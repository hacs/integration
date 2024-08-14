"""Test the sensor cleanup."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.hacs.const import DOMAIN, HACS_SYSTEM_ID

from tests.common import create_config_entry, setup_integration


async def test_sensor_cleanup(hass: HomeAssistant) -> None:
    """Test the sensor cleanup."""
    entity_registry = er.async_get(hass)
    assert len(entity_registry.entities) == 0
    entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=HACS_SYSTEM_ID,
    )

    assert entity_registry.async_get(entry.entity_id) is not None

    await setup_integration(
        hass,
        create_config_entry(
            options={
                "appdaemon": True,
            },
        ),
    )

    assert entity_registry.async_get(entry.entity_id) is None
