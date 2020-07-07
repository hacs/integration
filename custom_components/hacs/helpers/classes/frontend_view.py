"""HACS http endpoints."""
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.webresponses.category import async_serve_category_file
from custom_components.hacs.webresponses.frontend import async_serve_frontend
from custom_components.hacs.webresponses.iconset import serve_iconset

IGNORE = ["class-map.js.map"]


class HacsFrontend(HomeAssistantView):
    """Base View Class for HACS."""

    requires_auth = False
    name = "hacs_files"
    url = r"/hacsfiles/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        return await get_file_response(requested_file)


async def get_file_response(requested_file):
    """Get file."""
    logger = getLogger("web")

    if requested_file in IGNORE:
        logger.debug(f"Ignoring request for {requested_file}")
        return web.Response(status=200)

    if requested_file.startswith("frontend-"):
        return await async_serve_frontend()

    elif requested_file == "iconset.js":
        return serve_iconset()

    return await async_serve_category_file(requested_file)
