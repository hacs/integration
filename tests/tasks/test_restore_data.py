# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsDisabledReason


@pytest.mark.asyncio
async def test_restore_data(hacs: HacsBase):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("restore_data")

    assert task
    assert not hacs.system.disabled

    hacs.data = AsyncMock()

    hacs.data.restore.return_value = True
    await task.execute_task()
    assert not hacs.system.disabled

    hacs.data.restore.return_value = False
    await task.execute_task()
    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.RESTORE
