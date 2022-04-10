# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsDisabledReason, HacsStage


@pytest.mark.asyncio
async def test_check_ratelimit_not_running(hacs: HacsBase):
    hacs.stage = HacsStage.WAITING
    await hacs.tasks.async_load()
    task = hacs.tasks.get("check_ratelimit")

    assert task

    await task.execute_task()


@pytest.mark.asyncio
async def test_check_ratelimit(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    await hacs.tasks.async_load()
    task = hacs.tasks.get("check_ratelimit")

    assert task

    hacs.disable_hacs(HacsDisabledReason.RATE_LIMIT)

    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.RATE_LIMIT

    with patch(
        "custom_components.hacs.base.HacsBase.async_can_update",
        return_value=1,
    ):
        await task.execute_task()

    assert "<HacsTask check_ratelimit> Ratelimit indicate we can update 1" in caplog.text
    assert not hacs.system.disabled
    assert hacs.system.disabled_reason is None


@pytest.mark.asyncio
async def test_check_ratelimit_exception(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.stage = HacsStage.RUNNING
    await hacs.tasks.async_load()
    task = hacs.tasks.get("check_ratelimit")

    assert task

    with patch(
        "custom_components.hacs.tasks.check_ratelimit.Task.async_execute",
        side_effect=Exception("lore_ipsum"),
    ):
        await task.execute_task()
        assert "<HacsTask check_ratelimit> failed: lore_ipsum" in caplog.text
