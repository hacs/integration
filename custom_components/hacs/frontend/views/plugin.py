"""CommunityPluging View for HACS."""
import logging
import os
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger('custom_components.hacs')


class CommunityPlugin(HomeAssistantView):
    """View to return a plugin file with limited cache."""

    requires_auth = False

    url = r"/community_plugin/{path:.+}"
    name = "community_plugin"

    def __init__(self, hass, hacs):
        """Initialize plugin view."""
        self.hass = hass
        self.hacs = hacs

    async def get(self, request, path):  # pylint: disable=unused-argument
        """Retrieve custom_card."""

        # Strip '?' from URL
        if "?" in path:
            path = path.split("?")[0]

        file = "{}/www/community/{}".format(self.hass.config.path(), path)

        try:
            response = None
            if os.path.exists(file):
                _LOGGER.debug(
                    "Serving /community_plugin%s from /www/community%s", file, file
                )
                response = web.FileResponse(file)
                response.headers["Cache-Control"] = "max-age=0, must-revalidate"
            else:
                _LOGGER.debug("Tried to serve up '%s' but it does not exist", file)

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug("there was an issue trying to serve %s - %s", file, error)

        return response
