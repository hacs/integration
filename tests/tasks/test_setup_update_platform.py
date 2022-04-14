# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

from awesomeversion import AwesomeVersion
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import ConfigurationType


@pytest.mark.asyncio
async def test_setup_update_platform(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    await hacs.tasks.async_load()
    hacs.core.ha_version = AwesomeVersion("2022.4.0")
    task = hacs.tasks.get("setup_update_platform")

    assert task

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_setup_platforms"
    ) as mock_async_setup_platforms:
        hacs.configuration.config_type = ConfigurationType.YAML
        await task.execute_task()
        assert "Update entities are only supported when using UI configuration" in caplog.text

        hacs.configuration.config_type = ConfigurationType.CONFIG_ENTRY
        hacs.configuration.experimental = True

        await task.execute_task()
        assert mock_async_setup_platforms.call_count == 1
        assert mock_async_setup_platforms.call_args[0][1] == ["update"]
