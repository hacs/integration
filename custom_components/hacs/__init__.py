"""
HACS gives you a powerful UI to handle downloads of all your custom needs.

For more details about this integration, please refer to the documentation at
https://hacs.xyz/
"""
import voluptuous as vol

from .const import DOMAIN
from .helpers.functions.configuration_schema import hacs_config_combined
from .operational.setup import async_setup as hacs_yaml_setup
from .operational.setup import async_setup_entry as hacs_ui_setup
from .operational.remove import async_remove_entry as hacs_remove_entry

CONFIG_SCHEMA = vol.Schema({DOMAIN: hacs_config_combined()}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up this integration using yaml."""

    return await hacs_yaml_setup(hass, config)


async def async_setup_entry(hass, config_entry):
    """Set up this integration using UI."""

    return await hacs_ui_setup(hass, config_entry)


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    return await hacs_remove_entry(hass, config_entry)
