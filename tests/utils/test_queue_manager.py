"""Queue tests."""
import asyncio
from unittest.mock import AsyncMock

import async_timeout
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.exceptions import HacsExecutionStillInProgress
from custom_components.hacs.utils.queue_manager import QueueManager

TIMEOUT = 60


@pytest.mark.asyncio
async def test_queue_manager_interface(hacs: HacsBase, caplog: pytest.LogCaptureFixture) -> None:
    """Test QueueManager interface."""
    dummy_task = AsyncMock()
    queue_manager = QueueManager(hass=hacs.hass)

    async def sleeper() -> None:
        await dummy_task.before_sleep()
        await asyncio.sleep(TIMEOUT)
        await dummy_task.after_sleep()

    assert queue_manager.running is False
    assert queue_manager.has_pending_tasks is False
    assert queue_manager.pending_tasks == 0

    queue_manager.add(sleeper())
    queue_manager.add(sleeper())

    assert queue_manager.running is False
    assert queue_manager.has_pending_tasks is True
    assert queue_manager.pending_tasks == 2

    hacs.hass.async_create_task(queue_manager.execute(1))

    with async_timeout.timeout(TIMEOUT - 10):
        while not dummy_task.before_sleep.called:
            await asyncio.sleep(0.1)

    assert queue_manager.running is True
    assert queue_manager.has_pending_tasks is True
    assert queue_manager.pending_tasks == 1

    with pytest.raises(HacsExecutionStillInProgress):
        await queue_manager.execute()

    queue_manager.clear()

    assert not queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 0

    assert "The queue is empty" not in caplog.text
    await queue_manager.execute()
    assert "The queue is empty" in caplog.text

    queue_manager._stopping = True
    queue_manager.add(sleeper())
    assert not queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 0


@pytest.mark.asyncio
async def test_queue_manager_clear(hacs: HacsBase) -> None:
    """Test clearing the queue."""
    range_count = 44
    mocker = AsyncMock()
    queue_manager = QueueManager(hass=hacs.hass)

    async def sleeper() -> None:
        await mocker.before_sleep()
        await asyncio.sleep(TIMEOUT)
        await mocker.after_sleep()

    for _ in range(0, range_count):
        queue_manager.add(sleeper())

    assert queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == range_count
    hacs.hass.async_create_task(queue_manager.execute())

    with async_timeout.timeout(TIMEOUT - 10):
        while not mocker.before_sleep.called:
            await asyncio.sleep(0.1)

    assert queue_manager.pending_tasks == 0
    assert not queue_manager.has_pending_tasks

    for _ in range(0, range_count):
        queue_manager.add(sleeper())

    assert queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == range_count

    queue_manager.clear()
    assert not queue_manager.running
    assert not queue_manager.has_pending_tasks
    assert mocker.before_sleep.call_count == range_count
    assert mocker.after_sleep.call_count == 0
