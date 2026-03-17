"""Helpers for resolving repository icon URLs."""

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING, Any

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
REPOSITORY_ICONS_STORE_KEY = "repository_icons"
ICON_FILENAME = "icon.png"
DARK_ICON_FILENAME = "dark_icon.png"


def repository_uploaded_icon_path(image_id: str) -> str:
    """Return the image serve path for an uploaded icon."""
    return f"/api/image/serve/{image_id}/original"


def official_brand_icon_urls(domain: str, *, dark: bool = False) -> list[str]:
    """Return hosted Home Assistant brand icon URLs in priority order."""
    filenames = [DARK_ICON_FILENAME, ICON_FILENAME] if dark else [ICON_FILENAME]
    return [f"{BRANDS_BASE_URL}/{domain}/{filename}" for filename in filenames]


def hosted_brand_icon_url(domain: str, *, dark: bool = False) -> str:
    """Return the hosted placeholder URL for a brand icon."""
    filename = DARK_ICON_FILENAME if dark else ICON_FILENAME
    return f"{BRANDS_FALLBACK_BASE_URL}/{domain}/{filename}"


def local_brand_icon_paths(repository: HacsRepository, *, dark: bool = False) -> list[Path]:
    """Return candidate local brand icon paths for a repository."""
    filenames = [DARK_ICON_FILENAME, ICON_FILENAME] if dark else [ICON_FILENAME]
    candidate_directories: list[Path] = []

    if repository.content.path.local:
        candidate_directories.append(Path(repository.content.path.local) / "brand")

    if repository.data.domain and repository.hacs.core.config_path:
        candidate_directories.append(
            Path(repository.hacs.core.config_path)
            / "custom_components"
            / repository.data.domain
            / "brand"
        )

    paths: list[Path] = []
    seen_directories: set[str] = set()
    for directory in candidate_directories:
        directory_key = directory.as_posix()
        if directory_key in seen_directories:
            continue
        seen_directories.add(directory_key)
        for filename in filenames:
            paths.append(directory / filename)

    return paths


def _stored_local_source(path: Path) -> dict[str, Any] | None:
    """Return cache metadata for a local icon path."""
    try:
        stat = path.stat()
    except OSError:
        return None

    return {
        "source_path": path.as_posix(),
        "source_mtime_ns": stat.st_mtime_ns,
        "source_size": stat.st_size,
    }


async def async_initialize_repository_icon_cache(hacs: HacsBase) -> None:
    """Restore and prune cached local repository icons."""
    stored_icons = await async_load_from_store(hacs.hass, REPOSITORY_ICONS_STORE_KEY)
    if not isinstance(stored_icons, dict):
        stored_icons = {}

    image_collection = _get_image_upload_collection(hacs)
    retained: dict[str, dict[str, Any]] = {}
    valid_repository_ids = {str(repository.data.id) for repository in hacs.repositories.list_all}

    for key, entry in stored_icons.items():
        if not isinstance(entry, dict):
            continue

        repo_id = _repository_icon_store_repo_id(key)
        if repo_id not in valid_repository_ids:
            await _async_delete_uploaded_icon(image_collection, entry.get("image_id"))
            continue

        repository = hacs.repositories.get_by_id(repo_id)
        image_id = entry.get("image_id")
        source_path = entry.get("source_path")
        source_mtime_ns = entry.get("source_mtime_ns")
        source_size = entry.get("source_size")
        if (
            repository is None
            or not image_id
            or not isinstance(source_path, str)
            or not isinstance(source_mtime_ns, int)
            or not isinstance(source_size, int)
        ):
            await _async_delete_uploaded_icon(image_collection, image_id)
            continue

        if image_collection is None or image_id not in image_collection.data:
            continue

        current_source = await hacs.hass.async_add_executor_job(_stored_local_source, Path(source_path))
        if current_source is None:
            await _async_delete_uploaded_icon(image_collection, image_id)
            continue

        if (
            current_source["source_path"] != source_path
            or current_source["source_mtime_ns"] != source_mtime_ns
            or current_source["source_size"] != source_size
        ):
            await _async_delete_uploaded_icon(image_collection, image_id)
            continue

        retained[key] = {
            "image_id": image_id,
            "source_path": source_path,
            "source_mtime_ns": source_mtime_ns,
            "source_size": source_size,
        }

    hacs.common.repository_uploaded_icons = retained
    await async_save_to_store(hacs.hass, REPOSITORY_ICONS_STORE_KEY, retained)


async def async_resolve_repository_icon_url(
    repository: HacsRepository,
    session: ClientSession,
    *,
    dark: bool = False,
) -> str | None:
    """Resolve the best icon URL for a repository."""
    domain = repository.data.domain
    if not domain:
        return None

    hosted_url = await _async_first_existing_url(session, official_brand_icon_urls(domain, dark=dark))
    if hosted_url is not None:
        await _async_clear_uploaded_repository_icon(repository, dark=dark)
        return hosted_url

    local_icon_path = await _async_get_local_brand_icon_path(repository, dark=dark)
    if local_icon_path is not None:
        cached_path = await _async_cache_local_repository_icon(repository, local_icon_path, dark=dark)
        if cached_path is not None:
            return cached_path

    await _async_clear_uploaded_repository_icon(repository, dark=dark)
    return hosted_brand_icon_url(domain, dark=dark)


async def _async_cache_local_repository_icon(
    repository: HacsRepository,
    source_path: Path,
    *,
    dark: bool,
) -> str | None:
    """Cache a local repository icon via Home Assistant image storage."""
    image_collection = _get_image_upload_collection(repository.hacs)
    if image_collection is None:
        return None

    source = await repository.hacs.hass.async_add_executor_job(_stored_local_source, source_path)
    if source is None:
        return None

    store_key = _repository_icon_store_key(str(repository.data.id), dark)
    current = repository.hacs.common.repository_uploaded_icons.get(store_key)
    image_id = current.get("image_id") if current is not None else None
    if (
        current is not None
        and current.get("source_path") == source["source_path"]
        and current.get("source_mtime_ns") == source["source_mtime_ns"]
        and current.get("source_size") == source["source_size"]
        and image_id in image_collection.data
    ):
        return repository_uploaded_icon_path(image_id)

    content = await repository.hacs.hass.async_add_executor_job(source_path.read_bytes)
    if not content:
        return None

    created = await _async_create_uploaded_icon(
        image_collection,
        source_path.name,
        content,
        _path_content_type(source_path),
    )

    previous_image_id = image_id
    repository.hacs.common.repository_uploaded_icons[store_key] = {
        "image_id": created[CONF_ID],
        **source,
    }
    await async_save_to_store(
        repository.hacs.hass,
        REPOSITORY_ICONS_STORE_KEY,
        repository.hacs.common.repository_uploaded_icons,
    )

    if previous_image_id and previous_image_id != created[CONF_ID]:
        await _async_delete_uploaded_icon(image_collection, previous_image_id)

    return repository_uploaded_icon_path(created[CONF_ID])


def _repository_icon_store_key(repository_id: str, dark: bool) -> str:
    """Return the store key used for repository icon uploads."""
    return f"{repository_id}:{str(dark).lower()}"


def _repository_icon_store_repo_id(store_key: str) -> str:
    """Return the repository id for a cached icon entry."""
    return store_key.split(":", 1)[0]


def _get_image_upload_collection(hacs: HacsBase) -> ImageStorageCollection | None:
    """Return the Home Assistant image storage collection."""
    return hacs.hass.data.get(IMAGE_UPLOAD_DOMAIN)


async def _async_get_local_brand_icon_path(
    repository: HacsRepository,
    *,
    dark: bool,
) -> Path | None:
    """Return the first local repository icon path on disk."""
    for candidate in local_brand_icon_paths(repository, dark=dark):
        exists = await repository.hacs.hass.async_add_executor_job(candidate.is_file)
        if exists:
            return candidate
    return None


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
    await _async_delete_uploaded_icon(
        _get_image_upload_collection(repository.hacs),
        current.get("image_id"),
    )


async def _async_create_uploaded_icon(
    image_collection: ImageStorageCollection,
    filename: str,
    content: bytes,
    content_type: str,
) -> dict[str, str]:
    """Store a fetched icon in Home Assistant image storage."""
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
    image_collection: ImageStorageCollection | None,
    image_id: str | None,
) -> None:
    """Best-effort delete an uploaded icon."""
    if image_collection is None or not image_id:
        return
    try:
        await image_collection.async_delete_item(image_id)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.debug("Could not delete cached uploaded icon %s", image_id, exc_info=True)


async def _async_first_existing_url(
    session: ClientSession,
    urls: list[str],
) -> str | None:
    """Return the first URL that can be fetched successfully."""
    for url in urls:
        try:
            response = await session.get(url, allow_redirects=True)
        except Exception:  # pylint: disable=broad-except
            continue
        if getattr(response, "status", 0) == 200:
            return url
    return None


def _path_content_type(path: Path) -> str:
    """Return a supported image content type for a local file path."""
    suffix = path.suffix.lower()
    if suffix == ".gif":
        return "image/gif"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"
