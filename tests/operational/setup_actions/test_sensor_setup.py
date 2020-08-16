import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry

from custom_components.hacs.operational.setup_actions.sensor import async_add_sensor


@pytest.mark.asyncio
async def test_async_add_sensor_ui(hacs, hass):
    hacs.hass.config_entries = ConfigEntries(hass, {})
    hacs.configuration.config_entry = ConfigEntry(
        1, "hacs", "hacs", {}, "user", "local_push", {},
    )
    hacs.configuration.config = {"key": "value"}
    await async_add_sensor()


@pytest.mark.asyncio
async def test_async_add_sensor_yaml(hacs):
    hacs.configuration.config = {"key": "value"}

    hacs.configuration.config_type = "yaml"
    await async_add_sensor()
