"""HTTP view for resolving repository icons."""

from __future__ import annotations

import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .base import HacsBase
from .const import DOMAIN
from .enums import HacsCategory
from .utils.repository_icon import async_resolve_repository_icon_url

_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class HacsRepositoryIconView(HomeAssistantView):
    """Resolve repository icons to hosted or repository-local assets."""

    url = "/api/hacs/icon/{repository_id}"
    name = "api:hacs:repository_icon"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request, repository_id: str) -> web.Response:
        """Handle icon requests."""
        hacs: HacsBase | None = self.hass.data.get(DOMAIN)
        if hacs is None:
            raise web.HTTPServiceUnavailable()

        repository = hacs.repositories.get_by_id(repository_id)
        if repository is None or repository.data.category != HacsCategory.INTEGRATION:
            raise web.HTTPNotFound()

        dark = request.query.get("dark") == "1"
        icon_url = await async_resolve_repository_icon_url(
            repository,
            hacs.session,
            dark=dark,
            cache=hacs.common.repository_icon_urls,
        )
        if icon_url is None:
            raise web.HTTPNotFound()

        raise web.HTTPFound(location=icon_url)


class HacsRepositoryIconByDomainView(HomeAssistantView):
    """Resolve repository icons by integration domain name."""

    url = "/api/hacs/icon/domain/{domain}"
    name = "api:hacs:repository_icon_domain"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request, domain: str) -> web.Response:
        """Handle icon requests by domain."""
        if not _DOMAIN_RE.match(domain):
            raise web.HTTPBadRequest()

        hacs: HacsBase | None = self.hass.data.get(DOMAIN)
        if hacs is None:
            raise web.HTTPServiceUnavailable()

        repository = None
        for repo in hacs.repositories.list_all:
            if (
                repo.data.category == HacsCategory.INTEGRATION
                and repo.data.domain == domain
            ):
                repository = repo
                break

        if repository is None:
            raise web.HTTPNotFound()

        dark = request.query.get("dark") == "1"
        icon_url = await async_resolve_repository_icon_url(
            repository,
            hacs.session,
            dark=dark,
            cache=hacs.common.repository_icon_urls,
        )
        if icon_url is None:
            raise web.HTTPNotFound()

        raise web.HTTPFound(location=icon_url)
