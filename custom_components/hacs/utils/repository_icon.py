"""Helpers for resolving repository icon URLs."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp.client import ClientSession

    from ..repositories.base import HacsRepository

BRANDS_BASE_URL = "https://brands.home-assistant.io/_"
RAW_CONTENT_BASE_URL = "https://raw.githubusercontent.com"
ICON_FILENAME = "icon.png"
DARK_ICON_FILENAME = "dark_icon.png"


def repository_icon_api_path(repository_id: str, *, dark: bool = False) -> str:
    """Return the local API path used to resolve repository icons."""
    suffix = "?dark=1" if dark else ""
    return f"/api/hacs/icon/{repository_id}{suffix}"


def hosted_brand_icon_url(domain: str, *, dark: bool = False) -> str:
    """Return the hosted Home Assistant brand icon URL for a domain."""
    filename = DARK_ICON_FILENAME if dark else ICON_FILENAME
    return f"{BRANDS_BASE_URL}/{domain}/{filename}"


def local_brand_icon_urls(repository: HacsRepository, *, dark: bool = False) -> list[str]:
    """Return candidate raw GitHub brand icon URLs for a repository."""
    if not repository.data.full_name:
        return []

    ref = repository.ref or repository.data.selected_tag or repository.data.last_version
    ref = ref or repository.data.default_branch or "main"
    if ref.startswith("tags/"):
        ref = ref.replace("tags/", "", 1)

    base_path = PurePosixPath(repository.content.path.remote or "")
    brand_path = base_path / "brand"

    filenames = [DARK_ICON_FILENAME, ICON_FILENAME] if dark else [ICON_FILENAME]
    urls: list[str] = []

    for filename in filenames:
        asset_path = (brand_path / filename).as_posix().lstrip("/")
        urls.append(f"{RAW_CONTENT_BASE_URL}/{repository.data.full_name}/{ref}/{asset_path}")

    return urls


async def async_resolve_repository_icon_url(
    repository: HacsRepository,
    session: ClientSession,
    *,
    dark: bool = False,
    cache: dict[tuple[str, bool], str | None] | None = None,
) -> str | None:
    """Resolve the best icon URL for a repository."""
    cache_key = (str(repository.data.id), dark)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    candidates: list[str] = []
    if repository.data.domain:
        candidates.append(hosted_brand_icon_url(repository.data.domain, dark=dark))
    candidates.extend(local_brand_icon_urls(repository, dark=dark))
    if dark and repository.data.domain:
        candidates.append(hosted_brand_icon_url(repository.data.domain))

    resolved = None
    for candidate in candidates:
        if await _async_url_exists(session, candidate):
            resolved = candidate
            break

    if cache is not None:
        cache[cache_key] = resolved

    return resolved


async def _async_url_exists(session: ClientSession, url: str) -> bool:
    """Check whether a URL can be fetched successfully."""
    try:
        response = await session.get(url, allow_redirects=True)
    except Exception:  # pylint: disable=broad-except
        return False

    return getattr(response, "status", 0) == 200
