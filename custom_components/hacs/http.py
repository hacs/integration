"""HACS http endpoints."""
import os
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from hacs_frontend import locate_gz, locate_debug_gz

from .hacsbase import Hacs


class HacsFrontend(HomeAssistantView, Hacs):
    """Base View Class for HACS."""

    requires_auth = False
    name = "hacs_files"
    url = r"/hacsfiles/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""

        if requested_file.startswith("frontend-"):
            if self.configuration.debug:
                servefile = await self.hass.async_add_executor_job(locate_debug_gz)
                self.logger.debug("Serving DEBUG frontend")
            else:
                servefile = await self.hass.async_add_executor_job(locate_gz)

            if os.path.exists(servefile):
                return web.FileResponse(servefile)
        elif requested_file == "iconset.js":
            return web.FileResponse(
                f"{self.system.config_path}/custom_components/hacs/iconset.js"
            )

        try:
            if requested_file.startswith("themes"):
                file = f"{self.system.config_path}/{requested_file}"
            else:
                file = f"{self.system.config_path}/www/community/{requested_file}"

            # Serve .gz if it exist
            if os.path.exists(file + ".gz"):
                file += ".gz"

            if os.path.exists(file):
                self.logger.debug("Serving {} from {}".format(requested_file, file))
                response = web.FileResponse(file)
                response.headers["Cache-Control"] = "max-age=0, must-revalidate"
                return response
            else:
                self.logger.error(f"Tried to serve up '{file}' but it does not exist")

        except Exception as error:  # pylint: disable=broad-except
            self.logger.debug(
                "there was an issue trying to serve {} - {}".format(
                    requested_file, error
                )
            )

        return web.Response(status=404)


class HacsPluginViewLegacy(HacsFrontend):
    """Alias for legacy, remove with 2.0"""

    url = r"/community_plugin/{requested_file:.+}"
