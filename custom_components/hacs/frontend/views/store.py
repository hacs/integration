"""Serve HacsStoreView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase
from ...const import ELEMENT_TYPES
from ...repositoryinformation import RepositoryInformation

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsStoreView(HacsViewBase):
    """Serve HacsOverviewView."""

    name = "community_store"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["store"]

    async def get(self, request):  # pylint: disable=unused-argument
        """Serve HacsStoreView."""
        try:
            self.store.frontend = []
            for repository in self.repositories_list_name:
                self.store.frontend.append(
                    RepositoryInformation(
                        self.store.repositories[repository.repository_id]))

            render = self.render('overviews', 'store')
            return web.Response(body=render, content_type="text/html", charset="utf-8")

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])
