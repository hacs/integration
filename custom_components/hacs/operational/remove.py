"""Remove HACS."""
from custom_components.hacs.share import get_hacs


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    hacs = get_hacs()
    hacs.logger.info("Disabling HACS")
    hacs.logger.info("Removing recurring tasks")
    for task in hacs.recuring_tasks:
        task()
    if config_entry.state == "loaded":
        hacs.logger.info("Removing sensor")
        try:
            await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        except ValueError:
            pass
    hacs.logger.info("Removing sidepanel")
    try:
        hass.components.frontend.async_remove_panel("hacs")
    except AttributeError:
        pass
    hacs.system.disabled = True
    hacs.logger.info("HACS is now disabled")
