"""Helpers for resolving repository icon URLs."""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from aiohttp.web_request import FileField
from homeassistant.components.image_upload.const import DOMAIN as IMAGE_UPLOAD_DOMAIN
from homeassistant.const import CONF_ID
from multidict import CIMultiDict, CIMultiDictProxy

from .store import async_load_from_store, async_save_to_store

if TYPE_CHECKING:
    from aiohttp.client import ClientSession
    from homeassistant.components.image_upload import ImageStorageCollection

    from ..base import HacsBase
    from ..repositories.base import HacsRepository

_LOGGER = logging.getLogger(__name__)

BRANDS_BASE_URL = "https://brands.home-assistant.io"
BRANDS_FALLBACK_BASE_URL = f"{BRANDS_BASE_URL}/_"
RAW_CONTENT_BASE_URL = "https://raw.githubusercontent.com"
REPOSITORY_ICONS_STORE_KEY = "repository_icons"
ICON_FILENAME = "icon.png"
DARK_ICON_FILENAME = "dark_icon.png"
ALLOWED_CONTENT_TYPES = {"image/gif", "image/jpeg", "image/png"}


def repository_icon_api_path(repository_id: str, *, dark: bool = False) -> str:
    """Return the local API path used to resolve repository icons."""
    suffix = "?dark=1" if dark else ""
    return f"/api/hacs/icon/{repository_id}{suffix}"


def repository_uploaded_icon_path(image_id: str) -> str:
    """Return the Home Assistant image serve path for an uploaded icon."""
    return f"/api/image/serve/{image_id}/original"


def official_brand_icon_url(domain: str, *, dark: bool = False) -> str:
    """Return the direct Home Assistant brand icon URL for a domain."""
    filename = DARK_ICON_FILENAME if dark else ICON_FILENAME
    return f"{BRANDS_BASE_URL}/{domain}/{filename}"


def hosted_brand_icon_url(domain: str, *, dark: bool = False) -> str:
    """Return the hosted Home Assistant brand icon URL with legacy placeholder fallback."""
    filename = DARK_ICON_FILENAME if dark else ICON_FILENAME
    return f"{BRANDS_FALLBACK_BASE_URL}/{domain}/{filename}"


def local_brand_icon_urls(repository: HacsRepository, *, dark: bool = False) -> list[str]:
    """Return candidate raw GitHub brand icon URLs for a repository."""
    if not repository.data.full_name:
        return []

    ref = repository.ref or repository.data.selected_tag or repository.data.last_version
    ref = ref or repository.data.default_branch or "main"
    if ref.startswith("tags/"):
        ref = ref.replace("tags/", "", 1)

    base = f"{RAW_CONTENT_BASE_URL}/{repository.data.full_name}/{ref}"
    filenames = [DARK_ICON_FILENAME, ICON_FILENAME] if dark else [ICON_FILENAME]

    remote = repository.content.path.remote or ""
    brand_path = PurePosixPath(remote) / "brand"

    alt_brand_path = None
    domain = repository.data.domain
    if domain and not remote.endswith(domain):
        alt_brand_path = PurePosixPath(f"custom_components/{domain}/brand")

    urls: list[str] = []
    for filename in filenames:
        asset = (brand_path / filename).as_posix().lstrip("/")
        urls.append(f"{base}/{asset}")
    if alt_brand_path:
        for filename in filenames:
            asset = (alt_brand_path / filename).as_posix().lstrip("/")
            urls.append(f"{base}/{asset}")

    return urls


async def async_initialize_repository_icon_cache(hacs: HacsBase) -> None:
    """Restore and prune cached repository icons."""
    stored_icons = await async_load_from_store(hacs.hass, REPOSITORY_ICONS_STORE_KEY)
    if not isinstance(stored_icons, dict):
        stored_icons = {}

    image_collection = _get_image_upload_collection(hacs)
    valid_repository_ids = {str(repository.data.id) for repository in hacs.repositories.list_all}
    changed = False
    retained: dict[str, dict[str, str]] = {}

    for key, entry in stored_icons.items():
        if not isinstance(entry, dict):
            changed = True
            continue

        repo_id = _repository_icon_store_repo_id(key)
        image_id = entry.get("image_id")
        source_url = entry.get("source_url")

        if repo_id not in valid_repository_ids or not image_id or not source_url:
            changed = True
            if image_collection is not None and image_id:
                await _async_delete_uploaded_icon(image_collection, image_id)
            continue

        if image_collection is not None and image_id not in image_collection.data:
            changed = True
            continue

        retained[key] = {"image_id": image_id, "source_url": source_url}

    hacs.common.repository_icon_urls.clear()
    hacs.common.repository_uploaded_icons = retained

    if changed or retained != stored_icons:
        await async_save_to_store(hacs.hass, REPOSITORY_ICONS_STORE_KEY, retained)


async def async_resolve_repository_icon_url(
    repository: HacsRepository,
    session: ClientSession,
    *,
    dark: bool = False,
    cache: dict[tuple[str, bool], str | None] | None = None,
) -> str | None:
    """Resolve the best icon URL for a repository."""
    resolved = None
    domain = repository.data.domain

    if domain and await _async_url_exists(session, official_brand_icon_url(domain, dark=dark)):
        await _async_clear_uploaded_repository_icon(repository, dark=dark)
        resolved = official_brand_icon_url(domain, dark=dark)
    else:
        for candidate in local_brand_icon_urls(repository, dark=dark):
            if cached_icon := await _async_cache_local_repository_icon(
                repository,
                session,
                candidate,
                dark=dark,
            ):
                resolved = cached_icon
                break

        if resolved is None and dark and domain:
            light_brand_url = official_brand_icon_url(domain)
            if await _async_url_exists(session, light_brand_url):
                await _async_clear_uploaded_repository_icon(repository, dark=dark)
                resolved = light_brand_url

    if resolved is None:
        await _async_clear_uploaded_repository_icon(repository, dark=dark)
        if domain:
            resolved = hosted_brand_icon_url(domain, dark=dark)

    if cache is not None:
        cache[(str(repository.data.id), dark)] = resolved

    return resolved


def _repository_icon_store_key(repository_id: str, dark: bool) -> str:
    """Return the store key used for repository icon uploads."""
    return f"{repository_id}:{str(dark).lower()}"


def _repository_icon_store_repo_id(store_key: str) -> str:
    """Return the repository id for a cached icon entry."""
    return store_key.split(":", 1)[0]


def _get_image_upload_collection(hacs: HacsBase) -> ImageStorageCollection | None:
    """Return the Home Assistant image storage collection."""
    return hacs.hass.data.get(IMAGE_UPLOAD_DOMAIN)


async def _async_cache_local_repository_icon(
    repository: HacsRepository,
    session: ClientSession,
    source_url: str,
    *,
    dark: bool,
) -> str | None:
    """Cache a repository-local brand icon via Home Assistant image storage."""
    image_collection = _get_image_upload_collection(repository.hacs)
    if image_collection is None:
        return None

    store_key = _repository_icon_store_key(str(repository.data.id), dark)
    current = repository.hacs.common.repository_uploaded_icons.get(store_key)
    if (
        current is not None
        and current.get("source_url") == source_url
        and (image_id := current.get("image_id")) in image_collection.data
    ):
        return repository_uploaded_icon_path(image_id)

    downloaded = await _async_download_image(session, source_url)
    if downloaded is None:
        return None

    content, content_type = downloaded
    created = await _async_create_uploaded_icon(
        image_collection,
        source_url,
        content,
        content_type,
    )

    image_id = created[CONF_ID]
    previous_image_id = current.get("image_id") if current is not None else None

    repository.hacs.common.repository_uploaded_icons[store_key] = {
        "image_id": image_id,
        "source_url": source_url,
    }
    await async_save_to_store(
        repository.hacs.hass,
        REPOSITORY_ICONS_STORE_KEY,
        repository.hacs.common.repository_uploaded_icons,
    )

    if previous_image_id and previous_image_id != image_id:
        await _async_delete_uploaded_icon(image_collection, previous_image_id)

    return repository_uploaded_icon_path(image_id)


async def _async_clear_uploaded_repository_icon(
    repository: HacsRepository,
    *,
    dark: bool,
) -> None:
    """Remove a cached uploaded icon for a repository icon variant."""
    store_key = _repository_icon_store_key(str(repository.data.id), dark)
    current = repository.hacs.common.repository_uploaded_icons.pop(store_key, None)
    if current is None:
        return

    await async_save_to_store(
        repository.hacs.hass,
        REPOSITORY_ICONS_STORE_KEY,
        repository.hacs.common.repository_uploaded_icons,
    )

    image_collection = _get_image_upload_collection(repository.hacs)
    if image_collection is not None and (image_id := current.get("image_id")):
        await _async_delete_uploaded_icon(image_collection, image_id)


async def _async_download_image(
    session: ClientSession,
    url: str,
) -> tuple[bytes, str] | None:
    """Fetch image bytes and a supported content type."""
    try:
        response = await session.get(url, allow_redirects=True)
    except Exception:  # pylint: disable=broad-except
        return None

    if getattr(response, "status", 0) != 200:
        return None

    content = await response.read()
    if not content:
        return None

    return content, _response_content_type(response, url)


async def _async_create_uploaded_icon(
    image_collection: ImageStorageCollection,
    source_url: str,
    content: bytes,
    content_type: str,
) -> dict[str, str]:
    """Store a fetched icon in Home Assistant image storage."""
    filename = PurePosixPath(urlparse(source_url).path).name or ICON_FILENAME

    with SpooledTemporaryFile(mode="w+b") as file_handle:
        file_handle.write(content)
        file_handle.seek(0)

        file_field = FileField(
            name="file",
            filename=filename,
            file=file_handle,
            content_type=content_type,
            headers=CIMultiDictProxy(CIMultiDict()),
        )
        return await image_collection.async_create_item({"file": file_field})


async def _async_delete_uploaded_icon(
    image_collection: ImageStorageCollection,
    image_id: str,
) -> None:
    """Best-effort delete an uploaded icon."""
    try:
        await image_collection.async_delete_item(image_id)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.debug("Could not delete cached uploaded icon %s", image_id, exc_info=True)


async def _async_url_exists(session: ClientSession, url: str) -> bool:
    """Check whether a URL can be fetched successfully."""
    try:
        response = await session.get(url, allow_redirects=True)
    except Exception:  # pylint: disable=broad-except
        return False

    return getattr(response, "status", 0) == 200


def _response_content_type(response, url: str) -> str:
    """Return a supported image content type for a response."""
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    if content_type in ALLOWED_CONTENT_TYPES:
        return content_type

    path = urlparse(url).path.lower()
    if path.endswith(".gif"):
        return "image/gif"
    if path.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "image/png"
