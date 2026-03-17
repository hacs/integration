"""HTTP view for resolving repository icons."""

from __future__ import annotations

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .enums import HacsCategory
from .utils.repository_icon import async_resolve_repository_icon_url


class HacsRepositoryIconView(HomeAssistantView):
    """Resolve repository icons for the dashboard."""

    url = "/api/hacs/icon/{repository_id}"
    name = "api:hacs:repository_icon"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request, repository_id: str) -> web.Response:
        """Handle icon requests."""
        hacs = self.hass.data.get(DOMAIN)
        if hacs is None:
            raise web.HTTPServiceUnavailable()

        repository = hacs.repositories.get_by_id(repository_id)
        if repository is None or repository.data.category != HacsCategory.INTEGRATION:
            raise web.HTTPNotFound()

        icon_url = await async_resolve_repository_icon_url(
            repository,
            hacs.session,
            dark=request.query.get("dark") == "1",
        )
        if icon_url is None:
            raise web.HTTPNotFound()

        raise web.HTTPFound(location=icon_url)
