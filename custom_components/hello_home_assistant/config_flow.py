"""Config_Flow file of the Hello Home Assistant Integration 1."""

import logging

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Input data schema:
DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name", default="Hello"): vol.In(
            ["Hello 1", "Hello 2", "Hello 3"]
        ),
        vol.Required("string", default="String"): str,
        vol.Required("integer", default=0): int,
    }
)


class HelloHomeAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow for the Hello Home Assistant integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
            )
        errors = {}

        if not user_input.get("string"):
            errors["string"] = "String is required."
        if user_input.get("integer") <= 0:
            errors["integer"] = "Integer must be greater than 0."

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors=errors,
            )

        return self.async_create_entry(title=user_input["string"], data=user_input)
