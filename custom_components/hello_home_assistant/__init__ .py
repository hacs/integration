"""Init of the Hello Home Assistant integration 1."""  # noqa: INP001

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Hello Home Assistant integration."""
    _LOGGER.info("Setting up Simple Integration")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello Home Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Store the config entry data in hass.data
    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.info("Setting up entry: %s", entry.title)

    # Extract the user input data
    name = entry.data.get("name", "Default Name")
    string_value = entry.data.get("string", "Default String")
    integer_value = entry.data.get("integer", 0)

    _LOGGER.debug(
        "Name: %s, String: %s, Integer: %d", name, string_value, integer_value
    )

    # Set the state of the sensor
    hass.states.async_set(f"sensor.{name.lower().replace(' ', '_')}", integer_value)
    _LOGGER.info(f"Sensor '{name}' with value '{integer_value}' is configured.")  # noqa: G004

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry from Hello Home Assistant."""
    _LOGGER.info("Unloading entry: %s with ID: %s", entry.title, entry.entry_id)

    # Check if the entry was loaded before attempting to unload
    if entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.info(
            "Config entry was never loaded! Current entries: %s", entry.entry_id
        )
        return False
    # Remove the state of the sensor
    name = entry.data.get("name", "default_name").lower().replace(" ", "_")
    sensor_entity_id = f"sensor.{name}"

    if hass.states.get(sensor_entity_id):
        hass.states.async_remove(sensor_entity_id)

    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Successfully unloaded entry: %s", entry.title)
    else:
        _LOGGER.error("Failed to unload entry: %s", entry.title)

    return unload_ok
