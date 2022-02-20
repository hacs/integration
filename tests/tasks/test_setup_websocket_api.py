# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_setup_websocket_api(hacs: HacsBase):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("setup_websocket_api")

    assert task

    with patch(
        "custom_components.hacs.tasks.setup_websocket_api.async_register_command"
    ) as mock_async_register_command:
        await task.execute_task()
        assert mock_async_register_command.call_count == 10
