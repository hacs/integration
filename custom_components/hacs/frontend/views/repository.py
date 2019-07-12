"""Serve HacsRepositoryView."""
# pylint: disable=broad-except
import logging
from aiohttp import web

from ...http import HacsViewBase
from ...repositories.repositoryinformationview import RepositoryInformationView

_LOGGER = logging.getLogger("custom_components.hacs.frontend")

class HacsRepositoryView(HacsViewBase):
    """Serve HacsRepositoryView."""

    name = "community_repository"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["repository"] + r"/{repository_id}"

    async def get(self, request, repository_id):
        """Serve HacsRepositoryView."""
        try:
            message = request.rel_url.query.get("message")
            repository = self.store.repositories[str(repository_id)]
            if not repository.updated_info:
                await repository.set_repository()
                await repository.update()
                repository.updated_info = True
                self.store.write()

            if repository.new:
                repository.new = False
                self.store.write()

            repository = RepositoryInformationView(repository)
            render = self.render('repository', repository=repository, message=message)
            return web.Response(body=render, content_type="text/html", charset="utf-8")

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])
