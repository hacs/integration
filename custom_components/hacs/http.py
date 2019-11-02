"""Blueprint for HacsWebResponse."""
import os
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

from integrationhelper import Logger

from .hacsbase import Hacs


class HacsFrontend(HomeAssistantView, Hacs):
    """Base View Class for HACS."""

    requires_auth = False
    name = "hacs_frontend"
    url = r"/hacs_frontend/{requested_file:.+}"

    def __init__(self):
        """Initialize."""
        self.logger = Logger("hacs.http")

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        servefile = f"{self.system.config_path}/custom_components/hacs/frontend/{requested_file}"

        # Serve .gz file if it exist
        if os.path.exists(f"{servefile}.gz"):
            servefile += ".gz"

        if os.path.exists(servefile):
            return web.FileResponse(servefile)
        else:
            return web.Response(status=404)


class HacsPluginView(HomeAssistantView, Hacs):
    """Serve plugins."""

    name = "hacs_plugin"

    def __init__(self):
        """Initialize."""
        self.url = r"/community_plugin/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Serve plugins for lovelace."""
        try:
            # Strip '?' from URL
            if "?" in requested_file:
                issue = f"?{requested_file.split('?')[0]}"
                requested_file = requested_file.split("?")[0]
                self.logger.warning(
                    f"You have a '{issue}' in your lovelace resource for {requested_file} this is not needed for HACS and should be removed."
                )

            file = f"{self.system.config_path}/www/community/{requested_file}"

            # Serve .gz if it exist
            if os.path.exists(file + ".gz"):
                file += ".gz"

            response = None
            if os.path.exists(file):
                self.logger.debug("Serving {} from {}".format(requested_file, file))
                response = web.FileResponse(file)
                response.headers["Cache-Control"] = "max-age=0, must-revalidate"
            else:
                self.logger.error(f"Tried to serve up '{file}' but it does not exist")
                response = web.Response(status=404)

        except Exception as error:  # pylint: disable=broad-except
            self.logger.debug(
                "there was an issue trying to serve {} - {}".format(
                    requested_file, error
                )
            )
            response = web.Response(status=404)

        return response
