# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsDisabledReason, HacsStage
from custom_components.hacs.exceptions import HacsExecutionStillInProgress

dummy_task = AsyncMock()


@pytest.mark.asyncio
async def test_prosess_queue_disabled(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    assert not hacs.queue.has_pending_tasks

    task = hacs.tasks.get("prosess_queue")

    assert task

    hacs.disable_hacs(HacsDisabledReason.RATE_LIMIT)

    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.RATE_LIMIT

    await task.execute_task()

    assert "<HacsTask prosess_queue> Skipping task, HACS is disabled rate_limit" in caplog.text


@pytest.mark.asyncio
async def test_prosess_queue_no_pending_tasks(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING

    assert not hacs.queue.has_pending_tasks

    task = hacs.tasks.get("prosess_queue")

    assert task

    await task.execute_task()
    assert "<HacsTask prosess_queue> Nothing in the queue" in caplog.text
    assert not hacs.queue.has_pending_tasks


@pytest.mark.asyncio
async def test_prosess_queue_running(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    hacs.queue.running = True

    assert not hacs.queue.has_pending_tasks

    hacs.queue.add(dummy_task())

    task = hacs.tasks.get("prosess_queue")

    assert task

    await task.execute_task()
    assert "<HacsTask prosess_queue> Queue is already running" in caplog.text

    assert hacs.queue.has_pending_tasks


@pytest.mark.asyncio
async def test_prosess_queue_ratelimted(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    hacs.queue.running = False

    assert not hacs.queue.has_pending_tasks

    hacs.queue.add(dummy_task())

    task = hacs.tasks.get("prosess_queue")

    assert task

    with patch("custom_components.hacs.base.HacsBase.async_can_update", return_value=0):
        await task.execute_task()

    assert hacs.queue.has_pending_tasks


@pytest.mark.asyncio
async def test_prosess_queue_not_ratelimted(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    hacs.queue.running = False

    assert not hacs.queue.has_pending_tasks

    hacs.queue.add(dummy_task())

    task = hacs.tasks.get("prosess_queue")

    assert task

    with patch("custom_components.hacs.base.HacsBase.async_can_update", return_value=100):
        await task.execute_task()

    assert "Can update 100 repositories, items in queue 1" in caplog.text
    assert "Queue execution finished" in caplog.text

    assert not hacs.queue.has_pending_tasks


@pytest.mark.asyncio
async def test_prosess_queue_exception(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    hacs.queue.running = False

    assert not hacs.queue.has_pending_tasks

    hacs.queue.add(dummy_task())

    task = hacs.tasks.get("prosess_queue")

    assert task

    with patch("custom_components.hacs.base.HacsBase.async_can_update", return_value=100), patch(
        "custom_components.hacs.utils.queue_manager.QueueManager.execute",
        side_effect=HacsExecutionStillInProgress,
    ):
        await task.execute_task()

    assert "Can update 100 repositories, items in queue 1" in caplog.text

    assert hacs.queue.has_pending_tasks
