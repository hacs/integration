"""Adds config flow for HACS."""
# pylint: disable=dangerous-default-value
import logging
import voluptuous as vol
from aiogithubapi import AIOGitHubAPIException, AIOGitHubAPIAuthenticationException
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN
from .configuration_schema import hacs_base_config_schema, hacs_config_option_schema

from custom_components.hacs.globals import get_hacs
from custom_components.hacs.helpers.information import get_repository

_LOGGER = logging.getLogger(__name__)


class HacsFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
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
            if await self._test_token(user_input["token"]):
                return self.async_create_entry(title="", data=user_input)

            self._errors["base"] = "auth"
            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(hacs_base_config_schema(user_input)),
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HacsOptionsFlowHandler(config_entry)

    async def _test_token(self, token):
        """Return true if token is valid."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            await get_repository(session, token, "hacs/org")
            return True
        except (
            AIOGitHubAPIException,
            AIOGitHubAPIAuthenticationException,
        ) as exception:
            _LOGGER.error(exception)
        return False


class HacsOptionsFlowHandler(config_entries.OptionsFlow):
    """HACS config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        hacs = get_hacs()
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        if hacs.configuration.config_type == "yaml":
            schema = {vol.Optional("not_in_use", default=""): str}
        else:
            schema = hacs_config_option_schema(self.config_entry.options)

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))
