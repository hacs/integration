# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock

import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_store_hacs_data(hacs: HacsBase):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("store_hacs_data")

    assert task

    hacs.data = AsyncMock()

    assert not hacs.system.disabled

    await task.execute_task()
    assert hacs.data.async_write.call_count == 1
