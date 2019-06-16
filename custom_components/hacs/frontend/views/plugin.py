"""Serve plugins for lovelace."""
# pylint: disable=broad-except
import logging
import os
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound
from ...blueprints import HacsViewBase

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsPluginView(HacsViewBase):
    """Serve plugins."""

    url = r"/community_plugin/{requested_file:.+}"
    name = "community_plugin"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Serve plugins for lovelace."""
        try:
            # Strip '?' from URL
            if "?" in requested_file:
                requested_file = requested_file.split("?")[0]

            file = "{}/www/community/{}".format(self.config_dir, requested_file)

            # Serve .gz if it exist
            if os.path.exists(file + ".gz"):
                file += ".gz"

            response = None
            if os.path.exists(file):
                _LOGGER.debug("Serving %s from %s", requested_file, file)
                response = web.FileResponse(file)
                response.headers["Cache-Control"] = "max-age=0, must-revalidate"
            else:
                _LOGGER.debug("Tried to serve up '%s' but it does not exist", file)
                raise HTTPNotFound()

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(
                "there was an issue trying to serve %s - %s", requested_file, error
            )
            raise HTTPNotFound()

        return response
