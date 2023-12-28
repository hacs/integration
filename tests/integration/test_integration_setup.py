from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_DOMAIN
from homeassistant.core import HomeAssistant
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
            "websocket_commands": [
                command for command in hass.data[WEBSOCKET_DOMAIN] if command.startswith("hacs/")
            ],
        },
    )
