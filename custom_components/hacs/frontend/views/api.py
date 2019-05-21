"""CommunityAPI View for HACS."""
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from custom_components.hacs.const import DOMAIN_DATA
from custom_components.hacs.frontend.views import error_view
from custom_components.hacs.handler.download import (
    download_hacs,
    download_integration,
    download_plugin,
)
from custom_components.hacs.handler.log import get_log_file_content
from custom_components.hacs.handler.remove import remove_element
from custom_components.hacs.handler.storage import write_to_data_store
from custom_components.hacs.handler.update import (
    load_integrations_from_git,
    load_plugins_from_git,
)

_LOGGER = logging.getLogger(__name__)


class CommunityAPI(HomeAssistantView):
    """View to serve CommunityAPI."""

    requires_auth = False

    url = r"/community_api/{element}/{action}"
    name = "community_api"

    def __init__(self, hass):
        """Initialize CommunityAPI."""
        self.hass = hass

    async def get(self, request, element, action):
        """Prosess GET API actions."""
        _LOGGER.debug("GET API call for %s with %s", element, action)

        # Reload data from the settings tab.
        if action == "reload":
            await self.hass.data[DOMAIN_DATA]["commander"].repetetive_tasks()

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        # Generate logfile.
        elif element == "log" and action == "get":
            log_file = await get_log_file_content(self.hass)

            # Show the logfile
            return web.Response(
                body=log_file, content_type="text/html", charset="utf-8"
            )

        # Upgrade HACS.
        elif element == "hacs" and action == "upgrade":
            await download_hacs(self.hass)

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        # Insall or Upgrade a custom element.
        elif action in ["install", "upgrade"]:

            # Get the Element.
            element = self.hass.data[DOMAIN_DATA]["elements"][element]

            if element.element_type == "integration":
                await download_integration(self.hass, element)
            elif element.element_type == "plugin":
                await download_plugin(self.hass, element)

            # Return to the element page.
            raise web.HTTPFound("/community_element/" + element.element_id)

        # Uninsall a custom element.
        elif action == "uninstall":

            # Get the Element.
            element = self.hass.data[DOMAIN_DATA]["elements"][element]

            if element.element_type in ["integration", "plugin"]:
                await remove_element(self.hass, element)

            # Return to the element page.
            raise web.HTTPFound("/community_element/" + element.element_id)

        # Custom repo handling.
        # Delete custom integration repo.
        elif element == "integration_url_delete":
            self.hass.data[DOMAIN_DATA]["repos"]["integration"].remove(action)
            await write_to_data_store(
                self.hass.config.path(), self.hass.data[DOMAIN_DATA]
            )

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        # Delete custom plugin repo.
        elif element == "plugin_url_delete":
            self.hass.data[DOMAIN_DATA]["repos"]["plugin"].remove(action)
            await write_to_data_store(
                self.hass.config.path(), self.hass.data[DOMAIN_DATA]
            )

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        else:
            # Serve the errorpage if action is not valid.
            html = await error_view()
            return web.Response(body=html, content_type="text/html", charset="utf-8")

    async def post(self, request, element, action):
        """Prosess GET API actions."""
        _LOGGER.debug("GET API call for %s with %s", element, action)

        # Custom repo handling.
        # Add custom integration repo.
        if element == "integration_url":

            # Get the repo.
            data = await request.post()
            repo = data["custom_url"]

            _LOGGER.debug("Trying to add %s", repo)

            # Stip first part if it's an URL.
            if "https://github" in repo:
                repo = repo.split("https://github.com/")[-1]

            if "https://www.github" in repo:
                repo = repo.split("https://www.github.com/")[-1]

            # If it still have content, continue.
            if repo != "":
                self.hass.data[DOMAIN_DATA]["repos"]["integration"].append(repo)
                await load_integrations_from_git(self.hass, repo)
                await write_to_data_store(
                    self.hass.config.path(), self.hass.data[DOMAIN_DATA]
                )

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        # Add custom plugin repo.
        elif element == "plugin_url":

            # Get the repo.
            data = await request.post()
            repo = data["custom_url"]

            _LOGGER.debug("Trying to add %s", repo)

            # Stip first part if it's an URL.
            if "https://github" in repo:
                repo = repo.split("https://github.com/")[-1]

            if "https://www.github" in repo:
                repo = repo.split("https://www.github.com/")[-1]

            # If it still have content, continue.
            if repo != "":
                self.hass.data[DOMAIN_DATA]["repos"]["plugin"].append(repo)
                await load_plugins_from_git(self.hass, repo)
                await write_to_data_store(
                    self.hass.config.path(), self.hass.data[DOMAIN_DATA]
                )

            # Return to settings tab
            raise web.HTTPFound("/community_settings")

        else:
            # Serve the errorpage if action is not valid.
            html = await error_view()
            return web.Response(body=html, content_type="text/html", charset="utf-8")
