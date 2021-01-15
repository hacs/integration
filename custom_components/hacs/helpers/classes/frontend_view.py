"""HACS http endpoints."""
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.util import sanitize_path

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.webresponses.category import async_serve_category_file
from custom_components.hacs.webresponses.frontend import async_serve_frontend
from custom_components.hacs.webresponses.iconset import serve_iconset

IGNORE = []

_LOGGER = getLogger()


class HacsFrontend(HomeAssistantView):
    """Base View Class for HACS."""

    requires_auth = False
    name = "hacs_files"
    url = r"/hacsfiles/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        return await get_file_response(request, sanitize_path(requested_file))


async def get_file_response(request, requested_file):
    """Get file."""

    if requested_file in IGNORE:
        _LOGGER.debug("Ignoring request for %s", requested_file)
        return web.Response(status=200)

    elif requested_file.startswith("frontend/"):
        return await async_serve_frontend(requested_file)

    elif requested_file == "iconset.js":
        return serve_iconset()

    return await async_serve_category_file(request, requested_file)
