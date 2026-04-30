"""Brand icon endpoint for HACS update entities."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .base import HacsBase
from .const import BRAND_ICON_CDN_URL, BRAND_ICON_URL
from .enums import HacsCategory

DOMAIN_RE = re.compile(r"^[a-z0-9_]+$")


def _read_brand_icon(path: Path) -> bytes | None:
    """Read a brand icon from disk."""
    if not path.is_file():
        return None
    return path.read_bytes()


class HacsBrandIconView(HomeAssistantView):
    """Serve installed integration brand icons with a CDN fallback."""

    name = "api:hacs:brand_icon"
    url = BRAND_ICON_URL
    requires_auth = False

    def __init__(self, hass: HomeAssistant, hacs: HacsBase) -> None:
        """Initialize the view."""
        self.hass = hass
        self.hacs = hacs

    async def get(self, request: web.Request, domain: str) -> web.Response:
        """Return the local brand icon for an installed HACS integration."""
        if not DOMAIN_RE.fullmatch(domain):
            return web.Response(status=HTTPStatus.NOT_FOUND)

        if (icon_path := self._brand_icon_path(domain)) is not None:
            data = await self.hass.async_add_executor_job(_read_brand_icon, icon_path)
            if data is not None:
                return web.Response(body=data, content_type="image/png")

        raise web.HTTPFound(BRAND_ICON_CDN_URL.format(domain=domain))

    def _brand_icon_path(self, domain: str) -> Path | None:
        """Return the local brand icon path for an installed integration."""
        for repository in self.hacs.repositories.list_downloaded:
            if repository.data.category != HacsCategory.INTEGRATION:
                continue
            if repository.data.domain != domain or repository.content.path.local is None:
                continue
            return Path(repository.content.path.local) / "brand" / "icon.png"
        return None
