"""Remove HACS."""
from typing import TYPE_CHECKING

from ..const import DOMAIN
from ..enums import HacsDisabledReason
from ..share import get_hacs

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_remove_entry(hass: "HomeAssistant", config_entry: "ConfigEntry"):
    """Handle removal of an entry."""
    hacs = get_hacs()
    hacs.log.info("Disabling HACS")
    hacs.log.info("Removing recurring tasks")
    for task in hacs.recuring_tasks:
        task()

    if str(config_entry.state) in ["ConfigEntryState.LOADED", "loaded"]:
        hacs.log.info("Removing sensor")
        try:
            await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        except ValueError:
            pass
    try:
        if "hacs" in hass.data.get("frontend_panels", {}):
            hacs.log.info("Removing sidepanel")
            hass.components.frontend.async_remove_panel("hacs")
    except AttributeError:
        pass
    if DOMAIN in hass.data:
        del hass.data[DOMAIN]
    hacs.disable(HacsDisabledReason.REMOVED)
