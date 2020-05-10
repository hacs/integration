"""HACS http endpoints."""
import os
from integrationhelper import Logger
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from hacs_frontend import locate_gz, locate_debug_gz

from custom_components.hacs.globals import get_hacs


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
    hacs = get_hacs()

    if requested_file.startswith("frontend-"):
        if hacs.configuration.debug:
            servefile = await hacs.hass.async_add_executor_job(locate_debug_gz)
            hacs.logger.debug("Serving DEBUG frontend")
        else:
            servefile = await hacs.hass.async_add_executor_job(locate_gz)

        if os.path.exists(servefile):
            return web.FileResponse(servefile)
    elif requested_file == "iconset.js":
        return web.FileResponse(
            f"{hacs.system.config_path}/custom_components/hacs/iconset.js"
        )

    try:
        if requested_file.startswith("themes"):
            file = f"{hacs.system.config_path}/{requested_file}"
        else:
            file = f"{hacs.system.config_path}/www/community/{requested_file}"

        # Serve .gz if it exist
        if os.path.exists(file + ".gz"):
            file += ".gz"

        if os.path.exists(file):
            hacs.logger.debug("Serving {} from {}".format(requested_file, file))
            response = web.FileResponse(file)
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-store"
            return response
        else:
            hacs.logger.error(f"Tried to serve up '{file}' but it does not exist")

    except Exception as error:  # pylint: disable=broad-except
        hacs.logger.debug(
            "there was an issue trying to serve {} - {}".format(requested_file, error)
        )

    return web.Response(status=404)
