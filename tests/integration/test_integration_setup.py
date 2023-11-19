from typing import Generator
import pytest
from homeassistant.core import HomeAssistant
from tests.common import create_config_entry
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.base import HacsBase


from tests.conftest import SnapshotFixture

@pytest.mark.asyncio
async def test_integration_setup(hass: HomeAssistant, proxy_session: Generator, snapshots: SnapshotFixture,):
    config_entry = create_config_entry(options={"experimental": True})
    hass.data.pop("custom_components", None)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hacs: HacsBase = hass.data.get(DOMAIN)
    assert not hacs.system.disabled

    await snapshots.assert_hacs_data(hacs, f"test_integration_setup.json")

