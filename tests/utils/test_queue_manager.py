"""Queue tests."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.exceptions import HacsExecutionStillInProgress
from custom_components.hacs.utils.queue_manager import QueueManager


async def test_queue_manager(hacs: HacsBase, caplog: pytest.LogCaptureFixture) -> None:
    """Test the queue manager."""
    dummy_task = AsyncMock()

    queue_manager = QueueManager(hass=hacs.hass)
    assert not queue_manager.running
    assert not queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 0
    assert queue_manager.queue == []

    queue_manager.add((dummy_task(),))
    assert queue_manager.has_pending_tasks
    assert queue_manager.pending_tasks == 1

    for _ in range(1, 5):
        queue_manager.add((dummy_task(),))
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


async def test_queue_manager_grouping(
    event_loop: asyncio.AbstractEventLoop, hacs: HacsBase, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the queue manager excutes queue items in order."""

    dummy_task = AsyncMock()
    slow_task_event_1 = asyncio.Event()
    slow_task_event_2 = asyncio.Event()

    async def fast_task() -> None:
        """A fast task."""

    async def slow_task() -> None:
        """A slow task."""
        await asyncio.sleep(0.1)
        slow_task_event_1.set()
        await slow_task_event_2.wait()

    coro_group_1 = (fast_task(), fast_task(), slow_task())
    coro_group_2 = (dummy_task(), dummy_task())

    queue_manager = QueueManager(hass=hacs.hass)
    queue_manager.add(coro_group_1)
    queue_manager.add(coro_group_2)
    assert queue_manager.pending_tasks == 5

    execute_task = event_loop.create_task(queue_manager.execute())
    await slow_task_event_1.wait()

    dummy_task.assert_not_awaited()

    slow_task_event_2.set()

    await execute_task

    assert dummy_task.await_count == 2
