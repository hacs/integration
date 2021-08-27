"""
HACS gives you a powerful UI to handle downloads of all your custom needs.

For more details about this integration, please refer to the documentation at
https://hacs.xyz/
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .const import DOMAIN, PLATFORMS
from .enums import HacsDisabledReason
from .helpers.functions.configuration_schema import hacs_config_combined
from .operational.setup import (
    async_setup as hacs_yaml_setup,
    async_setup_entry as hacs_ui_setup,
)

if TYPE_CHECKING:
    from .base import HacsBase

CONFIG_SCHEMA = vol.Schema({DOMAIN: hacs_config_combined()}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up this integration using yaml."""

    return await hacs_yaml_setup(hass, config)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.add_update_listener(async_reload_entry)

    return await hacs_ui_setup(hass, config_entry)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    hacs: HacsBase = hass.data[DOMAIN]

    for task in hacs.recuring_tasks:
        # Cancel all pending tasks
        task()

    try:
        if hass.data.get("frontend_panels", {}).get("hacs"):
            hacs.log.info("Removing sidepanel")
            hass.components.frontend.async_remove_panel("hacs")
    except AttributeError:
        pass

    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    hacs.disable_hacs(HacsDisabledReason.REMOVED)
    hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the HACS config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
