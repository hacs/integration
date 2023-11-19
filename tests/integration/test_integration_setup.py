from typing import Generator

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN

from tests.common import create_config_entry
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

    hacs: HacsBase = hass.data.get(DOMAIN)
    assert not hacs.system.disabled

    await snapshots.assert_hacs_data(hacs, f"test_integration_setup.json")
