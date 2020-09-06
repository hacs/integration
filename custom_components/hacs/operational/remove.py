"""Remove HACS."""
from custom_components.hacs.share import get_hacs


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    hacs = get_hacs()
    hacs.log.info("Disabling HACS")
    hacs.log.info("Removing recurring tasks")
    for task in hacs.recuring_tasks:
        task()
    if config_entry.state == "loaded":
        hacs.log.info("Removing sensor")
        try:
            await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        except ValueError:
            pass
    hacs.log.info("Removing sidepanel")
    try:
        hass.components.frontend.async_remove_panel("hacs")
    except AttributeError:
        pass
    hacs.system.disabled = True
    hacs.log.info("HACS is now disabled")
