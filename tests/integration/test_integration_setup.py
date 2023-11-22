from typing import Generator

from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_DOMAIN
from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.base import HacsBase

from tests.common import create_config_entry, get_hacs
from tests.conftest import SnapshotFixture


@pytest.mark.asyncio
async def test_integration_setup(
    hass: HomeAssistant,
    proxy_session: Generator,
    snapshots: SnapshotFixture,
):
    config_entry = create_config_entry(options={"experimental": True})
    hass.data.pop("custom_components", None)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hacs: HacsBase = get_hacs(hass)
    assert not hacs.system.disabled
    assert hacs.stage == "running"

    assert await hass.config_entries.async_reload(config_entry.entry_id)
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
                        "entity_id": entity.entity_id,
                        "state": entity.state,
                        "attributes": entity.attributes,
                    }
                    for entity in hass.states.async_all()
                ),
                key=lambda x: x["entity_id"],
            ),
            "websocket_commands": [
                command for command in hass.data[WEBSOCKET_DOMAIN] if command.startswith("hacs/")
            ],
        },
    )
