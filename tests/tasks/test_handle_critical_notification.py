# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import VERSION_STORAGE


@pytest.mark.asyncio
async def test_handle_critical_notification_nothing_to_notify(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("handle_critical_notification")

    assert task

    with patch("custom_components.hacs.utils.store.json_util.load_json", return_value={}):
        await task.execute_task()

    with patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={"version": VERSION_STORAGE, "data": []},
    ):
        await task.execute_task()

    with patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={"version": VERSION_STORAGE, "data": [{"acknowledged": True}]},
    ):
        await task.execute_task()

    assert "URGENT!: Check the HACS panel!" not in caplog.text


@pytest.mark.asyncio
async def test_handle_critical_notification(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("handle_critical_notification")

    assert task

    with patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={"version": VERSION_STORAGE, "data": [{"acknowledged": False}]},
    ):
        await task.execute_task()

    assert "URGENT!: Check the HACS panel!" in caplog.text
