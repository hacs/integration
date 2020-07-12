import pytest
from custom_components.hacs.operational.setup_actions.sensor import async_add_sensor
from custom_components.hacs.share import get_hacs
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries


@pytest.mark.asyncio
async def test_async_add_sensor():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.hass.config_entries = ConfigEntries(HomeAssistant(), {})
    hacs.configuration.config = {"key": "value"}
    await async_add_sensor()

    hacs.configuration.config_type = "yaml"
    await async_add_sensor()

    # Reset
    hacs.hass = HomeAssistant()
