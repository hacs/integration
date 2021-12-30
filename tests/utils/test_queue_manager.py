"""Queue tests."""
from unittest.mock import AsyncMock

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.exceptions import HacsExecutionStillInProgress
from custom_components.hacs.utils.queue_manager import QueueManager

dummy_task = AsyncMock()


@pytest.mark.asyncio
async def test_queue_manager(hacs: HacsBase, caplog: pytest.LogCaptureFixture) -> None:
    """Test the queue manager."""

    queue_manager = QueueManager(hass=hacs.hass)
    assert not queue_manager.running
    assert not queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 0
    assert queue_manager.queue == []

    queue_manager.add(dummy_task())
    assert queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 1

    for _ in range(1, 5):
        queue_manager.add(dummy_task())
    assert queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 5

    await queue_manager.execute(1)
    assert queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 4

    queue_manager.running = True

    with pytest.raises(HacsExecutionStillInProgress):
        await queue_manager.execute()

    queue_manager.running = False

    await queue_manager.execute()
    await queue_manager.execute()
    assert not queue_manager.running
    assert not queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 0
    assert queue_manager.queue == []
    assert "The queue is empty" in caplog.text
