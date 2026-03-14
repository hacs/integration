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


async def async_initialize_repository_icon_cache(hacs: HacsBase) -> None:
    """Restore and prune cached repository icons."""
    stored_icons = await async_load_from_store(hacs.hass, REPOSITORY_ICONS_STORE_KEY)
    if not isinstance(stored_icons, dict):
        stored_icons = {}

    image_collection = _get_image_upload_collection(hacs)
    valid_repository_ids = {str(repository.data.id) for repository in hacs.repositories.list_all}
    changed = False
    retained: dict[str, dict[str, Any]] = {}

    for key, entry in stored_icons.items():
        if not isinstance(entry, dict):
            changed = True
            continue

        repo_id = _repository_icon_store_repo_id(key)
        image_id = entry.get("image_id")
        source = _stored_repository_icon_source(entry)

        if repo_id not in valid_repository_ids or not image_id or source is None:
            changed = True
            if image_collection is not None and image_id:
                await _async_delete_uploaded_icon(image_collection, image_id)
            continue

        if image_collection is not None and image_id not in image_collection.data:
            changed = True
            continue

        current_source = await hacs.hass.async_add_executor_job(
            _local_repository_icon_source,
            Path(source["source_path"]),
        )
        if current_source is None or not _repository_icon_source_matches(entry, current_source):
            changed = True
            if image_collection is not None:
                await _async_delete_uploaded_icon(image_collection, image_id)
            continue

        retained[key] = _repository_icon_store_entry(image_id, current_source)

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
        local_source = await _async_get_local_repository_icon_source(repository, dark=dark)
        if local_source is not None:
            resolved = await _async_cache_local_repository_icon(
                repository,
                local_source,
                dark=dark,
            )

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


async def _async_get_local_repository_icon_source(
    repository: HacsRepository,
    *,
    dark: bool,
) -> dict[str, Any] | None:
    """Return metadata for the first local repository icon on disk."""
    for candidate in local_brand_icon_paths(repository, dark=dark):
        source = await repository.hacs.hass.async_add_executor_job(
            _local_repository_icon_source,
            candidate,
        )
        if source is not None:
            return source
    return None


async def _async_cache_local_repository_icon(
    repository: HacsRepository,
    source: dict[str, Any],
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
        and _repository_icon_source_matches(current, source)
        and (image_id := current.get("image_id")) in image_collection.data
    ):
        return repository_uploaded_icon_path(image_id)

    content = await repository.hacs.hass.async_add_executor_job(
        _read_local_repository_icon_content,
        Path(source["source_path"]),
    )
    if not content:
        return None

    created = await _async_create_uploaded_icon(
        image_collection,
        source["filename"],
        content,
        source["content_type"],
    )

    image_id = created[CONF_ID]
    previous_image_id = current.get("image_id") if current is not None else None

    repository.hacs.common.repository_uploaded_icons[store_key] = _repository_icon_store_entry(
        image_id,
        source,
    )
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


def _local_repository_icon_source(path: Path) -> dict[str, Any] | None:
    """Return source metadata for a local repository icon."""
    try:
        if not path.is_file():
            return None
        stat = path.stat()
    except OSError:
        return None

    return {
        "source_path": path.as_posix(),
        "source_mtime_ns": stat.st_mtime_ns,
        "source_size": stat.st_size,
        "filename": path.name,
        "content_type": _path_content_type(path),
    }


def _stored_repository_icon_source(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Return normalized stored metadata for a cached repository icon."""
    source_path = entry.get("source_path")
    source_mtime_ns = entry.get("source_mtime_ns")
    source_size = entry.get("source_size")

    if not isinstance(source_path, str) or not isinstance(source_mtime_ns, int) or not isinstance(
        source_size,
        int,
    ):
        return None

    return {
        "source_path": source_path,
        "source_mtime_ns": source_mtime_ns,
        "source_size": source_size,
    }


def _repository_icon_store_entry(image_id: str, source: dict[str, Any]) -> dict[str, Any]:
    """Return stored metadata for a cached repository icon."""
    return {
        "image_id": image_id,
        "source_path": source["source_path"],
        "source_mtime_ns": source["source_mtime_ns"],
        "source_size": source["source_size"],
    }


def _repository_icon_source_matches(entry: dict[str, Any], source: dict[str, Any]) -> bool:
    """Return whether stored metadata matches the current local source."""
    return (
        entry.get("source_path") == source["source_path"]
        and entry.get("source_mtime_ns") == source["source_mtime_ns"]
        and entry.get("source_size") == source["source_size"]
    )


def _read_local_repository_icon_content(path: Path) -> bytes | None:
    """Read a local repository icon from disk."""
    try:
        content = path.read_bytes()
    except OSError:
        return None

    return content or None


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


def _path_content_type(path: Path) -> str:
    """Return a supported image content type for a local file path."""
    suffix = path.suffix.lower()
    if suffix == ".gif":
        return "image/gif"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"
