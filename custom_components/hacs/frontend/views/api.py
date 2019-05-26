"""Serve HacsAPIView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from custom_components.hacs.blueprints import HacsViewBase

_LOGGER = logging.getLogger('custom_components.hacs.frontend')


class HacsAPIView(HacsViewBase):
    """Serve HacsAPIView."""

    name = "community_api"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["api"] + r"/{element}/{action}"

    async def get(self, request, element, action=None):  # pylint: disable=unused-argument
        """Serve HacsAPIView."""
        _LOGGER.debug("GET API call for %s with %s", element, action)

        if element == "repository_register":
            repository = self.repositories[action]
            result = await repository.install()
            _LOGGER.debug(result)
            raise web.HTTPFound(f"{self.url_path['repository']}/{repository.repository_id}")



    async def post(self, request, element, action=None):  # pylint: disable=unused-argument
        """Prosess POST API actions."""
        _LOGGER.debug("GET POST call for %s with %s", element, action)

        postdata = await request.post()

        if element == "repository_register":
            repository_name = postdata["custom_url"]
            repository_type = action

            # Stip first part if it's an URL.
            if "https://github" in repository_name:
                repository_name = repository_name.split("https://github.com/")[-1]

            if "https://www.github" in repository_name:
                repository_name = repository_name.split("https://www.github.com/")[-1]

            # If it still have content, continue.
            if repository_name != "":
                await self.register_new_repository(repository_type, repository_name)

            raise web.HTTPFound(self.url_path['settings'])