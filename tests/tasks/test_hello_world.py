# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_hello_world(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("hello_world")

    assert task

    await task.execute_task()
    assert "Hello World!" in caplog.text


@pytest.mark.asyncio
async def test_hello_world_exception(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("hello_world")

    assert task

    with patch(
        "custom_components.hacs.tasks.hello_world.Task.execute", side_effect=Exception("lore_ipsum")
    ):
        await task.execute_task()
        assert "Task hello_world failed: lore_ipsum" in caplog.text


@pytest.mark.asyncio
async def test_hello_world_disabled(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("hello_world")

    assert task

    hacs.system.disabled_reason = "lorem_ipsum"

    await task.execute_task()
    assert "Skipping task hello_world, HACS is disabled - lorem_ipsum" in caplog.text
