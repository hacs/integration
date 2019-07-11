"""Serve HacsSettingsView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from homeassistant.const import __version__ as HAVERSION

from ...http import HacsViewBase
from ...const import ISSUE_URL, NAME_LONG, ELEMENT_TYPES, VERSION

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsSettingsView(HacsViewBase):
    """Serve HacsSettingsView."""

    name = "community_settings"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["settings"]

    async def get(self, request):
        """Serve HacsOverviewView."""
        try:
            render = self.render('settings')
            return web.Response(body=render, content_type="text/html", charset="utf-8")

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])
