"""Serve brand icons for repositories managed by HACS.

Custom integrations ship their brand images in a local brand folder
(custom_components/<domain>/brand/) since Home Assistant 2026.3, and
home-assistant/brands no longer accepts images for custom integrations.

This view serves those icons to the HACS frontend:
- Downloaded integrations are served straight from the local brand folder.
- Integrations that are not downloaded are fetched from the repository
  content on GitHub and cached on disk. The cache is keyed by the version
  the icon was fetched for, so a new release invalidates it automatically.
- Repositories without a brand icon are redirected to the brands CDN,
  which still hosts previously accepted images.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import quote

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .enums import HacsCategory

if TYPE_CHECKING:
    from .base import HacsBase
    from .repositories.base import HacsRepository

URL_BASE = "/api/hacs/repository"
BRANDS_CDN_URL = "https://brands.home-assistant.io/_"
CACHE_DIR = ".storage/hacs.icons"
CACHE_CONTROL = f"public, max-age={60 * 60 * 24}"
NEGATIVE_CACHE_TTL = 60 * 60 * 24 * 7
MAX_ICON_SIZE = 1024 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
VALID_FILENAMES = ("icon.png", "dark_icon.png")

_DOMAIN_RE = re.compile(r"[a-z0-9_]+")

_VIEW_REGISTERED = "hacs_repository_icon_view_registered"


def _read_file(path: Path) -> bytes | None:
    """Read a file, returning None if it can not be read."""
    try:
        return path.read_bytes()
    except OSError:
        return None


def _validate_icon(content: bytes | None) -> bytes | None:
    """Return the content if it is a PNG image within the size limit."""
    if content is None or len(content) > MAX_ICON_SIZE or not content.startswith(PNG_MAGIC):
        return None
    return content


def _cache_lookup(cache_file: Path, marker_file: Path) -> tuple[bytes | None, bool]:
    """Return cached icon content and whether a fresh negative marker exists."""
    if (content := _validate_icon(_read_file(cache_file))) is not None:
        return content, False
    try:
        fresh = (time.time() - marker_file.stat().st_mtime) < NEGATIVE_CACHE_TTL
    except OSError:
        fresh = False
    return None, fresh


def _cache_write(
    cache_dir: Path,
    prefix: str,
    filename: str,
    target: Path,
    content: bytes | None,
) -> None:
    """Write icon content (or a negative marker) and drop entries for old versions."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for stale in (
        *cache_dir.glob(f"{prefix}*-{filename}"),
        *cache_dir.glob(f"{prefix}*-{filename}.missing"),
    ):
        if stale != target:
            stale.unlink(missing_ok=True)
    if content is None:
        target.touch()
    else:
        target.write_bytes(content)


class HacsRepositoryIconView(HomeAssistantView):
    """Serve brand icons for HACS repositories."""

    url = f"{URL_BASE}/{{repository_id}}/{{filename}}"
    name = "api:hacs:repository:icon"
    requires_auth = False

    def __init__(self, hacs: HacsBase) -> None:
        """Initialize the view."""
        self.hacs = hacs
        self._cache_dir = Path(hacs.hass.config.path(CACHE_DIR))
        self._locks: dict[str, asyncio.Lock] = {}

    async def get(
        self,
        request: web.Request,
        repository_id: str,
        filename: str,
    ) -> web.StreamResponse:
        """Serve the brand icon for a repository."""
        repository = self.hacs.repositories.get_by_id(repository_id)
        if (
            filename not in VALID_FILENAMES
            or repository is None
            or repository.data.category != HacsCategory.INTEGRATION
            or not repository.data.domain
            or not _DOMAIN_RE.fullmatch(repository.data.domain)
        ):
            raise web.HTTPNotFound

        if repository.data.installed:
            return await self._async_serve_local(repository, filename)
        return await self._async_serve_remote(repository, filename)

    async def _async_serve_local(
        self, repository: HacsRepository, filename: str
    ) -> web.StreamResponse:
        """Serve the icon from the downloaded integration."""
        brand_path = Path(
            self.hacs.hass.config.path(
                "custom_components", repository.data.domain, "brand", filename
            )
        )
        content = _validate_icon(
            await self.hacs.hass.async_add_executor_job(_read_file, brand_path)
        )
        if content is not None:
            return self._icon_response(content)
        return self._fallback_response(repository, filename)

    async def _async_serve_remote(
        self, repository: HacsRepository, filename: str
    ) -> web.StreamResponse:
        """Serve the icon from the GitHub repository content, with caching."""
        if (ref := repository.data.last_version or repository.data.default_branch) is None:
            return self._fallback_response(repository, filename)

        prefix = f"{repository.data.id}-"
        cache_file = self._cache_dir / f"{prefix}{quote(ref, safe='')}-{filename}"
        marker_file = cache_file.parent / f"{cache_file.name}.missing"

        lock = self._locks.setdefault(str(repository.data.id), asyncio.Lock())
        async with lock:
            content, missing = await self.hacs.hass.async_add_executor_job(
                _cache_lookup, cache_file, marker_file
            )
            if content is None and not missing:
                content = await self._async_download_icon(repository, ref, filename)
                await self.hacs.hass.async_add_executor_job(
                    _cache_write,
                    self._cache_dir,
                    prefix,
                    filename,
                    cache_file if content is not None else marker_file,
                    content,
                )

        if content is not None:
            return self._icon_response(content)
        return self._fallback_response(repository, filename)

    async def _async_download_icon(
        self, repository: HacsRepository, ref: str, filename: str
    ) -> bytes | None:
        """Download the icon from the repository content."""
        url = (
            f"https://raw.githubusercontent.com/{repository.data.full_name}/{ref}"
            f"/custom_components/{repository.data.domain}/brand/{filename}"
        )
        return _validate_icon(await self.hacs.async_download_file(url, keep_url=True, nolog=True))

    def _icon_response(self, content: bytes) -> web.Response:
        """Return the icon content."""
        return web.Response(
            body=content,
            content_type="image/png",
            headers={"Cache-Control": CACHE_CONTROL},
        )

    def _fallback_response(self, repository: HacsRepository, filename: str) -> web.StreamResponse:
        """Redirect to the icon variant, or to the brands CDN."""
        if filename != "icon.png":
            location = f"{URL_BASE}/{repository.data.id}/icon.png"
        else:
            location = f"{BRANDS_CDN_URL}/{repository.data.domain}/{filename}"
        return web.HTTPFound(location, headers={"Cache-Control": CACHE_CONTROL})


@callback
def async_register_icon_view(hass: HomeAssistant, hacs: HacsBase) -> None:
    """Register the repository icon view."""
    if hass.data.get(_VIEW_REGISTERED):
        return
    hass.data[_VIEW_REGISTERED] = True
    hass.http.register_view(HacsRepositoryIconView(hacs))
