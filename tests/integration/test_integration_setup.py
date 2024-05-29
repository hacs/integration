import sys
from unittest.mock import MagicMock, patch

from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_DOMAIN
from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.base import HacsBase

from tests.common import create_config_entry, get_hacs
from tests.conftest import SnapshotFixture


async def test_integration_setup(
    hass: HomeAssistant,
    snapshots: SnapshotFixture,
):
    config_entry = create_config_entry()
    hass.data.pop("custom_components", None)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hacs: HacsBase = get_hacs(hass)
    assert not hacs.system.disabled
    assert hacs.stage == "running"

    await snapshots.assert_hacs_data(
        hacs,
        "test_integration_setup.json",
        {
            "websocket_commands": [
                command for command in hass.data[WEBSOCKET_DOMAIN] if command.startswith("hacs/")
            ],
        },
    )


async def test_integration_setup_with_custom_updater(
    hass: HomeAssistant,
    snapshots: SnapshotFixture,
    caplog: pytest.LogCaptureFixture,
):
    config_entry = create_config_entry()
    hass.data.pop("custom_components", None)
    config_entry.add_to_hass(hass)
    with patch.dict(
        sys.modules,
        {
            **sys.modules,
            # Pretend custom_updater is loaded
            "custom_components.custom_updater": MagicMock(),
        },
    ):
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    hacs: HacsBase = get_hacs(hass)
    assert hacs.system.disabled_reason == "constrains"

    assert (
        "HACS cannot be used with custom_updater. To use HACS you need to remove custom_updater from `custom_components`"
        in caplog.text
    )

    await snapshots.assert_hacs_data(
        hacs,
        "test_integration_setup_with_custom_updater.json",
        {},
    )
