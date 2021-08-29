# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_hello_world(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("hello_world")

    assert task

    await task.execute_task()
    assert "Hello World!" in caplog.text
