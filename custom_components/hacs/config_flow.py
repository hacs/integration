"""Adds config flow for HACS."""
import logging
from collections import OrderedDict

import voluptuous as vol
from aiogithubapi import AIOGitHub, AIOGitHubException, AIOGitHubAuthentication
from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class HacsFlowHandler(config_entries.ConfigFlow):
    """Config flow for HACS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input={}):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_token(user_input["token"])
            if valid:
                return self.async_create_entry(title="", data=user_input)
            else:
                self._errors["base"] = "auth"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""

        # Defaults
        token = "xxxxxxxxxxxxxxxxxxxx"
        sidepanel_title = "Community"
        sidepanel_icon = "mdi:alpha-c-box"
        appdaemon = False
        python_script = False
        theme = False

        if user_input is not None:
            if "token" in user_input:
                token = user_input["token"]
            if "sidepanel_title" in user_input:
                sidepanel_title = user_input["sidepanel_title"]
            if "sidepanel_icon" in user_input:
                sidepanel_icon = user_input["sidepanel_icon"]
            if "appdaemon" in user_input:
                appdaemon = user_input["appdaemon"]
            if "python_script" in user_input:
                python_script = user_input["python_script"]
            if "theme" in user_input:
                theme = user_input["theme"]

        data_schema = OrderedDict()
        data_schema[vol.Required("token", default=token)] = str
        data_schema[vol.Optional("sidepanel_title", default=sidepanel_title)] = str
        data_schema[vol.Optional("sidepanel_icon", default=sidepanel_icon)] = str
        data_schema[vol.Optional("appdaemon", default=appdaemon)] = bool
        data_schema[vol.Optional("python_script", default=python_script)] = bool
        data_schema[vol.Optional("theme", default=theme)] = bool
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def async_step_import(self, user_input):
        """Import a config entry.
        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    async def _test_token(self, token):
        """Return true if token is valid."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            client = AIOGitHub(token, session)
            await client.get_repo("custom-components/hacs")
            return True
        except (AIOGitHubException, AIOGitHubAuthentication):
            pass
        return False
