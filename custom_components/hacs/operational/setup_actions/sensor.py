from homeassistant.helpers import discovery

from custom_components.hacs.const import DOMAIN
from custom_components.hacs.share import get_hacs


def _add_sensor():
    """Add sensor."""
    hacs = get_hacs()

    if hacs.configuration.config_type == "yaml":
        hacs.hass.async_create_task(
            discovery.async_load_platform(
                hacs.hass, "sensor", DOMAIN, {}, hacs.configuration.config
            )
        )
    else:
        hacs.hass.async_add_job(
            hacs.hass.config_entries.async_forward_entry_setup(
                hacs.configuration.config_entry, "sensor"
            )
        )


async def async_add_sensor():
    """Async wrapper for add sensor"""
    hacs = get_hacs()
    await hacs.hass.async_add_executor_job(_add_sensor)
