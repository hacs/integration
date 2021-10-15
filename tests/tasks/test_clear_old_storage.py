# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_clear_old_storage(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("clear_old_storage")

    assert task

    with patch("os.path.isfile", return_value=True), patch("os.remove", MagicMock()) as os_remove:
        await task.execute_task()
        assert "Cleaning up old storage file" in caplog.text
        assert os_remove.call_count == 1
