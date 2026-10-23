"""Test resource ownership when unloading HACS."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs import PLATFORMS, async_unload_entry
from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.enums import HacsDisabledReason, HacsStage
from custom_components.hacs.utils.queue_manager import QueueManager
from custom_components.hacs.utils.store import STORE_CACHE_KEY

from tests.common import create_config_entry


@pytest.mark.parametrize("pending", [False, True])
async def test_failed_unload_preserves_resources(hass: HomeAssistant, pending: bool):
    """Keep active resources if platforms refuse unload or work is pending."""
    hacs = HacsBase()
    hacs.hass = hass
    hacs.stage = HacsStage.RUNNING
    hacs.queue = QueueManager(hass)
    pending_work = Mock()
    if pending:
        hacs.queue.add(pending_work)
    cancel_task = Mock()
    hacs.recurring_tasks = [cancel_task]
    hacs.data = Mock(async_write=AsyncMock())
    hass.data[DOMAIN] = hacs
    cache = hass.data[STORE_CACHE_KEY] = {}
    panel = hass.data["frontend_panels"] = {"hacs": Mock()}
    entry = create_config_entry()

    with (
        patch.object(hass.config_entries, "async_unload_platforms", return_value=False) as unload,
        patch("custom_components.hacs.async_remove_panel") as remove_panel,
    ):
        assert not await async_unload_entry(hass, entry)

    if pending:
        unload.assert_not_called()
        assert hacs.queue.queue == [pending_work]
    else:
        unload.assert_awaited_once_with(entry, PLATFORMS)
    assert hass.data[DOMAIN] is hacs
    assert hass.data[STORE_CACHE_KEY] is cache
    assert hass.data["frontend_panels"] is panel
    assert hacs.stage is HacsStage.RUNNING
    assert not hacs.system.disabled
    cancel_task.assert_not_called()
    hacs.data.async_write.assert_not_awaited()
    remove_panel.assert_not_called()


async def test_successful_unload_cleans_up_resources(hass: HomeAssistant):
    """Dispose resources only after the platforms have unloaded successfully."""
    hacs = HacsBase()
    hacs.hass = hass
    hacs.stage = HacsStage.RUNNING
    hacs.queue = QueueManager(hass)
    cancel_task = Mock()
    hacs.recurring_tasks = [cancel_task]
    hacs.data = Mock(async_write=AsyncMock())
    hass.data[DOMAIN] = hacs
    hass.data[STORE_CACHE_KEY] = {}
    hass.data["frontend_panels"] = {"hacs": Mock()}
    entry = create_config_entry()

    async def unload_platforms(*_args):
        assert hass.data[DOMAIN] is hacs
        assert not hacs.system.disabled
        cancel_task.assert_not_called()
        hacs.data.async_write.assert_not_awaited()
        return True

    with (
        patch.object(hass.config_entries, "async_unload_platforms", side_effect=unload_platforms),
        patch("custom_components.hacs.async_remove_panel") as remove_panel,
    ):
        assert await async_unload_entry(hass, entry)

    cancel_task.assert_called_once_with()
    hacs.data.async_write.assert_awaited_once_with(force=True)
    remove_panel.assert_called_once_with(hass, "hacs")
    assert hacs.stage is None
    assert hacs.system.disabled_reason is HacsDisabledReason.REMOVED
    assert DOMAIN not in hass.data
    assert STORE_CACHE_KEY not in hass.data
