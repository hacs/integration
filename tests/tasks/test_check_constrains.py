# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import MINIMUM_HA_VERSION
from custom_components.hacs.enums import HacsDisabledReason


@pytest.mark.asyncio
async def test_check_constrains_custom_updater(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("check_constrains")

    assert task
    assert not hacs.system.disabled

    with patch("os.path.exists", return_value=False):
        await task.execute_task()
        assert not hacs.system.disabled

    with patch("os.path.exists", return_value=True):
        await task.execute_task()
        assert hacs.system.disabled
        assert hacs.system.disabled_reason == HacsDisabledReason.CONSTRAINS
        assert "This cannot be used with custom_updater" in caplog.text


@pytest.mark.asyncio
async def test_check_constrains_version(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("check_constrains")

    assert task
    assert not hacs.system.disabled

    with patch("os.path.exists", return_value=False):
        await task.execute_task()
        assert not hacs.system.disabled

    hacs.core.ha_version = "0"
    with patch("os.path.exists", return_value=False):
        await task.execute_task()
        assert hacs.system.disabled
        assert hacs.system.disabled_reason == HacsDisabledReason.CONSTRAINS
        assert (
            f"You need HA version {MINIMUM_HA_VERSION} or newer to use this integration"
            in caplog.text
        )
