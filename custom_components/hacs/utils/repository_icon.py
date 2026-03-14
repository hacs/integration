"""Helpers for resolving repository icon URLs."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp.client import ClientSession

    from ..repositories.base import HacsRepository

BRANDS_BASE_URL = "https://brands.home-assistant.io"
BRANDS_FALLBACK_BASE_URL = f"{BRANDS_BASE_URL}/_"
RAW_CONTENT_BASE_URL = "https://raw.githubusercontent.com"
ICON_FILENAME = "icon.png"
DARK_ICON_FILENAME = "dark_icon.png"


def repository_icon_api_path(repository_id: str, *, dark: bool = False) -> str:
    """Return the local API path used to resolve repository icons."""
    suffix = "?dark=1" if dark else ""
    return f"/api/hacs/icon/{repository_id}{suffix}"


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

    # Build candidate paths from content.path.remote if available.
    remote = repository.content.path.remote or ""
    brand_path = PurePosixPath(remote) / "brand"

    # If the remote path might not include the domain yet (e.g. just
    # "custom_components" before validation), also try with the domain appended.
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
        candidates.append(official_brand_icon_url(repository.data.domain, dark=dark))
    candidates.extend(local_brand_icon_urls(repository, dark=dark))
    if dark and repository.data.domain:
        candidates.append(official_brand_icon_url(repository.data.domain))

    resolved = None
    for candidate in candidates:
        if await _async_url_exists(session, candidate):
            resolved = candidate
            break

    if resolved is None and repository.data.domain:
        # Preserve the legacy placeholder image when neither the brands repo
        # nor the repository brand/ folder has an icon.
        resolved = hosted_brand_icon_url(repository.data.domain, dark=dark)

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
