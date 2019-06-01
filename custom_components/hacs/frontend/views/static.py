"""Serve static files used by HACS."""
# pylint: disable=broad-except
import logging
from aiohttp import web
import aiofiles
from custom_components.hacs.blueprints import HacsViewBase

_LOGGER = logging.getLogger('custom_components.hacs.frontend')


class HacsStaticView(HacsViewBase):
    """Serve static files."""

    name = "community_static"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["static"] + r"/{requested_file}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Serve static files."""
        servefile = "{}/custom_components/hacs/frontend/elements/{}".format(
            self.config_dir, requested_file)
        filecontent = ""

        if str(requested_file).endswith(".css"):
            filecontent_type = "text/css"

        elif str(requested_file).endswith(".js"):
            filecontent_type = "text/javascript"

        else:
            filecontent_type = "text/html"

        try:
            async with aiofiles.open(
                servefile, mode='r', encoding="utf-8", errors="ignore") as localfile:
                filecontent = await localfile.read()
                localfile.close()

        except Exception as exception:
            _LOGGER.debug("Could not serve %s - %s", requested_file, exception)

        return web.Response(body=filecontent, content_type=filecontent_type, charset="utf-8")
