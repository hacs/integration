"""Serve static files used by HACS."""
# pylint: disable=broad-except
import logging
import os
from aiohttp import web
from aiohttp.web import HTTPNotFound
from ...blueprints import HacsViewBase

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsStaticView(HacsViewBase):
    """Serve static files."""

    name = "community_static"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["static"] + r"/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Serve static files."""
        servefile = "{}/custom_components/hacs/frontend/elements/{}".format(
            self.config_dir, requested_file
        )

        if os.path.exists(servefile + ".gz"):
            return web.FileResponse(servefile + ".gz")
        else:
            if os.path.exists(servefile):
                return web.FileResponse(servefile)
            else:
                raise HTTPNotFound
