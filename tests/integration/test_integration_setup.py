from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.hacs.base import HacsBase

from tests.common import create_config_entry, get_hacs
from tests.conftest import SnapshotFixture


@pytest.mark.asyncio
async def test_integration_setup(
    hass: HomeAssistant,
    snapshots: SnapshotFixture,
):
    config_entry = create_config_entry(data={"experimental": True})
    hass.data.pop("custom_components", None)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hacs: HacsBase = get_hacs(hass)
    assert not hacs.system.disabled
    assert hacs.stage == "running"

    await snapshots.assert_hacs_data(
        hacs,
        f"test_integration_setup.json",
        {
            "entities": sorted(
                (
                    {
                        "entity_id": hass.states.get(entity.entity_id).entity_id,
                        "state": hass.states.get(entity.entity_id).state,
                        "attributes": hass.states.get(entity.entity_id).attributes,
                        **entity.as_partial_dict(),
                    }
                    for entity in er.async_entries_for_config_entry(
                        er.async_get(hass), config_entry.entry_id
                    )
                ),
                key=lambda x: x["unique_id"],
            ),
            "websocket_commands": [
                command for command in hass.data[WEBSOCKET_DOMAIN] if command.startswith("hacs/")
            ],
        },
    )
