# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import ConfigurationType


@pytest.mark.asyncio
async def test_setup_sensor_platform(hacs: HacsBase):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("setup_sensor_platform")

    assert task

    hacs.configuration.config_type = ConfigurationType.YAML
    with patch(
        "custom_components.hacs.tasks.setup_sensor_platform.async_load_platform"
    ) as mock_async_load_platform:
        await task.execute_task()
        assert mock_async_load_platform.call_count == 1

    hacs.configuration.config_type = ConfigurationType.CONFIG_ENTRY
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_setup_platforms"
    ) as mock_async_setup_platforms:
        await task.execute_task()
        assert mock_async_setup_platforms.call_count == 1
        assert mock_async_setup_platforms.call_args[0][1] == ["sensor"]
