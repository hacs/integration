"""Adds config flow for HACS."""
import voluptuous as vol
from aiogithubapi import (
    AIOGitHubAPIAuthenticationException,
    AIOGitHubAPIException,
    GitHubDevice,
)
from aiogithubapi.common.const import OAUTH_USER_LOGIN
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from custom_components.hacs.const import DOMAIN
from custom_components.hacs.helpers.functions.configuration_schema import (
    hacs_config_option_schema,
)
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.share import get_hacs

from .base import HacsBase

_LOGGER = getLogger()


class HacsFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for HACS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self.device = None

    async def async_step_device(self, user_input):
        """Handle device steps"""
        ## Vaiting for token
        try:
            activation = await self.device.async_device_activation()
            return self.async_create_entry(
                title="", data={"token": activation.access_token}
            )
        except (
            AIOGitHubAPIException,
            AIOGitHubAPIAuthenticationException,
        ) as exception:
            _LOGGER.error(exception)
            self._errors["base"] = "auth"
            return await self._show_config_form(user_input)

    async def async_step_user(self, user_input):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if user_input:
            if [x for x in user_input if not user_input[x]]:
                self._errors["base"] = "acc"
                return await self._show_config_form(user_input)

            ## Get device key
            if not self.device:
                return await self._show_device_form()

        ## Initial form
        return await self._show_config_form(user_input)

    async def _show_device_form(self):
        """Device flow"""
        self.device = GitHubDevice(
            "395a8e669c5de9f7c6e8",
            session=aiohttp_client.async_get_clientsession(self.hass),
        )
        device_data = await self.device.async_register_device()

        return self.async_show_form(
            step_id="device",
            errors=self._errors,
            description_placeholders={
                "url": OAUTH_USER_LOGIN,
                "code": device_data.user_code,
            },
        )

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""
        if not user_input:
            user_input = {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "acc_logs", default=user_input.get("acc_logs", False)
                    ): bool,
                    vol.Required(
                        "acc_addons", default=user_input.get("acc_addons", False)
                    ): bool,
                    vol.Required(
                        "acc_untested", default=user_input.get("acc_untested", False)
                    ): bool,
                    vol.Required(
                        "acc_disable", default=user_input.get("acc_disable", False)
                    ): bool,
                }
            ),
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HacsOptionsFlowHandler(config_entry)


class HacsOptionsFlowHandler(config_entries.OptionsFlow):
    """HACS config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, _user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        hacs: HacsBase = get_hacs()
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        if hacs.configuration.config_type == "yaml":
            schema = {vol.Optional("not_in_use", default=""): str}
        else:
            schema = hacs_config_option_schema(self.config_entry.options)
            del schema["frontend_repo"]
            del schema["frontend_repo_url"]

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))
