"""Adds config flow for HACS."""
import voluptuous as vol
from aiogithubapi import GitHubException, GitHubDeviceAPI
from aiogithubapi.common.const import OAUTH_USER_LOGIN
from awesomeversion import AwesomeVersion
from homeassistant import config_entries
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.event import async_call_later

from custom_components.hacs.const import (
    CLIENT_ID,
    DOMAIN,
    INTEGRATION_VERSION,
    MINIMUM_HA_VERSION,
)
from custom_components.hacs.helpers.functions.configuration_schema import (
    RELEASE_LIMIT,
    hacs_config_option_schema,
)
from custom_components.hacs.mixin import HacsMixin


class HacsFlowHandler(HacsMixin, config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for HACS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self.device = None
        self.activation = None
        self._progress_task = None
        self._login_device = None

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

            return await self.async_step_device(user_input)

        ## Initial form
        return await self._show_config_form(user_input)

    async def async_step_device(self, _user_input):
        """Handle device steps"""

        async def _wait_for_activation(_=None):
            if self._login_device is None or self._login_device.expires_in is None:
                async_call_later(self.hass, 1, _wait_for_activation)
                return

            response = await self.device.activation(
                device_code=self._login_device.device_code
            )
            self.activation = response.data
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
            )

        if not self.activation:
            if not self.device:
                self.device = GitHubDeviceAPI(
                    client_id=CLIENT_ID,
                    session=aiohttp_client.async_get_clientsession(self.hass),
                    **{"client_name": f"HACS/{INTEGRATION_VERSION}"},
                )
            async_call_later(self.hass, 1, _wait_for_activation)
            try:
                response = await self.device.register()
                self._login_device = response.data
                return self.async_show_progress(
                    step_id="device",
                    progress_action="wait_for_device",
                    description_placeholders={
                        "url": OAUTH_USER_LOGIN,
                        "code": self._login_device.user_code,
                    },
                )
            except GitHubException as exception:
                self.hacs.log.error(exception)
                return self.async_abort(reason="github")

        return self.async_show_progress_done(next_step_id="device_done")

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""
        if not user_input:
            user_input = {}
        if AwesomeVersion(HAVERSION) < MINIMUM_HA_VERSION:
            return self.async_abort(
                reason="min_ha_version",
                description_placeholders={"version": MINIMUM_HA_VERSION},
            )
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

    async def async_step_device_done(self, _user_input):
        """Handle device steps"""
        return self.async_create_entry(
            title="", data={"token": self.activation.access_token}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HacsOptionsFlowHandler(config_entry)


class HacsOptionsFlowHandler(HacsMixin, config_entries.OptionsFlow):
    """HACS config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, _user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            limit = int(user_input.get(RELEASE_LIMIT, 5))
            if limit <= 0 or limit > 100:
                return self.async_abort(reason="release_limit_value")
            return self.async_create_entry(title="", data=user_input)

        if self.hacs.configuration is None:
            return self.async_abort(reason="not_setup")

        if self.hacs.configuration.config_type == "yaml":
            schema = {vol.Optional("not_in_use", default=""): str}
        else:
            schema = hacs_config_option_schema(self.config_entry.options)
            del schema["frontend_repo"]
            del schema["frontend_repo_url"]

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))
