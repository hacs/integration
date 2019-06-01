"""CommunityAPI View for HACS."""
import logging
import json
import functools
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.event import async_call_later

from custom_components.hacs.handler.download import (
    download_hacs,
    download_integration,
    download_plugin,
)
from custom_components.hacs.handler.log import get_log_file_content
from custom_components.hacs.handler.storage import write_to_data_store, load_storage_file

_LOGGER = logging.getLogger('custom_components.hacs')


class CommunityAPI(HomeAssistantView):
    """View to serve CommunityAPI."""

    requires_auth = False

    url = r"/community_api/{element}/{action}"
    name = "community_api"

    def __init__(self, hass, hacs):
        """Initialize CommunityAPI."""
        self.hass = hass
        self.hacs = hacs

    async def get(self, request, element, action):
        """Prosess GET API actions."""
        _LOGGER.debug("GET API call for %s with %s", element, action)

        # Show the content of hacs.data
        if element == "hacs" and action == "inspect":
            inspect = await load_storage_file(self.hass)
            return web.json_response(inspect, dumps=functools.partial(json.dumps, indent=4))

        # Reload data from the settings tab.
        elif action == "reload":
            async_call_later(self.hass, 1, self.hacs.data["commander"].full_element_scan())
            #await self.hacs.data["commander"].full_element_scan()

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
            element = self.hacs.data["elements"][element]

            if element.element_type == "integration":
                await download_integration(self.hass, element)
            elif element.element_type == "plugin":
                await download_plugin(self.hass, element)

            # Return to the element page.
            raise web.HTTPFound("/community_element/" + element.element_id)

        # Uninsall a custom element.
        elif action == "uninstall":

            # Get the Element.
            element = self.hacs.data["elements"][element]

            if element.element_type in ["integration", "plugin"]:
                await remove_element(self.hass, element)

            # Return to the store.
            raise web.HTTPFound("/community_store")

        # Custom repo handling.
        # Delete custom integration repo.
        elif element == "integration_url_delete":
            await remove_repo(self.hass, action)
            if action in self.hacs.data["commander"].blacklist:
                self.hacs.data["commander"].blacklist.remove(action)
            await write_to_data_store(
                self.hass.config.path(), self.hacs.data
            )

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        # Delete custom plugin repo.
        elif element == "plugin_url_delete":
            await remove_repo(self.hass, action)
            if action in self.hacs.data["commander"].blacklist:
                self.hacs.data["commander"].blacklist.remove(action)
            await write_to_data_store(
                self.hass.config.path(), self.hacs.data
            )

            # Return to settings tab.
            raise web.HTTPFound("/community_settings")

        # Reload custom plugin repo.
        elif element == "integration_url_reload":

            if action in self.hacs.data["commander"].blacklist:
                self.hacs.data["commander"].blacklist.remove(action)
            scan_result = await self.hacs.data["elements"][action].update_element()

            if scan_result is not None:+
                message = None
                await write_to_data_store(
                    self.hass.config.path(), self.hacs.data
                )
            else:
                message = "Could not reload repo '{}' at this time, if the repo meet all requirements try again later.".format(
                    action
                )

            # Return
            if "/" in action:
                if message is not None:
                    raise web.HTTPFound(
                        "/community_settings?message={}".format(message)
                    )
                else:
                    raise web.HTTPFound("/community_settings")
            else:
                if message is not None:
                    raise web.HTTPFound(
                        "/community_element/{}?message={}".format(action, message)
                    )
                else:
                    raise web.HTTPFound("/community_element/{}".format(action))

        # Reload custom plugin repo.
        elif element == "plugin_url_reload":

            if action in self.hacs.data["commander"].blacklist:
                self.hacs.data["commander"].blacklist.remove(action)
            scan_result = await self.hacs.data["elements"][action].update_element()

            if scan_result is not None:
                message = None
                await write_to_data_store(
                    self.hass.config.path(), self.hacs.data
                )
            else:
                message = "Could not reload repo '{}' at this time, if the repo meet all requirements try again later.".format(
                    action
                )

            # Return
            if "/" in action:
                if message is not None:
                    raise web.HTTPFound(
                        "/community_settings?message={}".format(message)
                    )
                else:
                    raise web.HTTPFound("/community_settings")
            else:
                if message is not None:
                    raise web.HTTPFound(
                        "/community_element/{}?message={}".format(action, message)
                    )
                else:
                    raise web.HTTPFound("/community_element/{}".format(action))

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
            message = None

            _LOGGER.debug("Trying to add %s", repo)

            # Stip first part if it's an URL.
            if "https://github" in repo:
                repo = repo.split("https://github.com/")[-1]

            if "https://www.github" in repo:
                repo = repo.split("https://www.github.com/")[-1]

            # If it still have content, continue.
            if repo != "":
                scan_result = await add_new_element(self.hacs, "integration", repo)
                if scan_result is not None:
                    await write_to_data_store(
                        self.hass.config.path(), self.hacs.data
                    )
                else:
                    message = "Could not add repo '{}' at this time, if the repo meet all requirements try again later.".format(
                        data["custom_url"]
                    )
            else:
                message = "Repo '{}' was not a valid format.".format(data["custom_url"])

            # Return to settings tab
            if message is not None:
                if repo in self.hacs.data["repos"]["plugin"]:
                    self.hacs.data["repos"]["plugin"].remove(repo)
                if repo in self.hacs.data["commander"].blacklist:
                    self.hacs.data["commander"].blacklist.remove(repo)
                raise web.HTTPFound("/community_settings?message={}".format(message))
            else:
                raise web.HTTPFound("/community_settings")

        # Add custom plugin repo.
        elif element == "plugin_url":

            # Get the repo.
            data = await request.post()
            repo = data["custom_url"]
            message = None

            _LOGGER.debug("Trying to add %s", repo)

            # Stip first part if it's an URL.
            if "https://github" in repo:
                repo = repo.split("https://github.com/")[-1]

            if "https://www.github" in repo:
                repo = repo.split("https://www.github.com/")[-1]

            # If it still have content, continue.
            if repo != "":
                scan_result = await add_new_element(self.hacs, "plugin", repo)
                if scan_result is not None:
                    await write_to_data_store(
                        self.hass.config.path(), self.hacs.data
                    )
                else:
                    message = "Could not add repo '{}' at this time, if the repo meet all requirements try again later.".format(
                        data["custom_url"]
                    )
            else:
                message = "Repo '{}' was not a valid format.".format(data["custom_url"])

            # Return to settings tab
            if message is not None:
                if repo in self.hacs.data["repos"]["plugin"]:
                    self.hacs.data["repos"]["plugin"].remove(repo)
                if repo in self.hacs.data["commander"].blacklist:
                    self.hacs.data["commander"].blacklist.remove(repo)
                raise web.HTTPFound("/community_settings?message={}".format(message))
            else:
                raise web.HTTPFound("/community_settings")

        else:
            # Serve the errorpage if action is not valid.
            raise web.HTTPFound(self.hacs.url_path["error"])
