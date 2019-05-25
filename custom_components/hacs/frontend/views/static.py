"""Serve static files used by HACS."""
# pylint: disable=broad-except
from aiohttp import web
import logging
import aiofiles
from custom_components.hacs.blueprints import HacsViewBase

_LOGGER = logging.getLogger('custom_components.hacs')


class HacsStaticView(HacsViewBase):
    """Serve static files."""

    requires_auth = False

    url = r"/community_static/{requested_file}"
    name = "community_static"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Serve static files."""
        servefile = "{}/custom_components/hacs/frontend/static/{}".format(
            self.config_dir, requested_file)
        filecontent = ""
        if str(requested_file).endswith(".css"):
            filecontent_type = "text/css"
        else:
            filecontent_type = "text/html"

        try:
            async with aiofiles.open(
                servefile, mode='r', encoding="utf-8", errors="ignore") as localfile:
                filecontent = await localfile.read()
                localfile.close()

        except Exception as exception:
            _LOGGER.debug(f"Could not serve {requested_file} - {exception}")

        return web.Response(body=filecontent, content_type=filecontent_type, charset="utf-8")
