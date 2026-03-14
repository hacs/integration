"""Helpers for resolving repository icon URLs."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp.client import ClientSession

    from ..repositories.base import HacsRepository

BRANDS_BASE_URL = "https://brands.home-assistant.io/_"
BRANDS_DOMAINS_URL = "https://brands.home-assistant.io/domains.json"
RAW_CONTENT_BASE_URL = "https://raw.githubusercontent.com"
ICON_FILENAME = "icon.png"
DARK_ICON_FILENAME = "dark_icon.png"

# Module-level cache for known brand domains (populated once per session).
_known_brand_domains: set[str] | None = None


async def _async_get_known_brand_domains(session: ClientSession) -> set[str]:
    """Fetch and cache the set of domains that have real brand assets."""
    global _known_brand_domains  # noqa: PLW0603
    if _known_brand_domains is not None:
        return _known_brand_domains

    try:
        response = await session.get(BRANDS_DOMAINS_URL, allow_redirects=True)
        if response.status == 200:
            data = await response.json(content_type=None)
            domains: set[str] = set()
            # domains.json has keys like "core", "custom" with lists of domains
            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        domains.update(str(d) for d in value)
            _known_brand_domains = domains
            return domains
    except Exception:  # pylint: disable=broad-except
        pass

    # On failure, return empty set so we skip brands and try repo fallback.
    return set()


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

    known_domains = await _async_get_known_brand_domains(session)

    candidates: list[str] = []
    # Only use brands CDN if the domain is actually registered there.
    if repository.data.domain and repository.data.domain in known_domains:
        candidates.append(hosted_brand_icon_url(repository.data.domain, dark=dark))
    # Always try repo-local brand/ directory as fallback.
    candidates.extend(local_brand_icon_urls(repository, dark=dark))
    # For dark mode, also fall back to the non-dark brand icon.
    if dark and repository.data.domain and repository.data.domain in known_domains:
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
