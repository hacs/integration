"""Serve HacsOverviewView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase
from ...repositoryinformation import RepositoryInformation

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsOverviewView(HacsViewBase):
    """Serve HacsOverviewView."""

    name = "community_overview"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["overview"]

    async def get(self, request):  # pylint: disable=unused-argument
        """Serve HacsOverviewView."""
        try:
            self.store.frontend = []
            for repository in self.repositories_list_name:
                self.store.frontend.append(
                    RepositoryInformation(
                        self.store.repositories[repository.repository_id]))

            render = self.render('overviews', 'overview')
            return web.Response(body=render, content_type="text/html", charset="utf-8")

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

