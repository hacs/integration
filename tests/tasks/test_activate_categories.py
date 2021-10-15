# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.asyncio
async def test_activate_categories(hacs: HacsBase):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("activate_categories")

    assert task
    assert len(hacs.common.categories) == 0

    await task.execute_task()
    assert hacs.common.categories == {"integration", "plugin"}

    hacs.hass.config.components.add("python_script")
    await task.execute_task()
    assert "python_script" in hacs.common.categories
    hacs.hass.config.components.remove("python_script")

    hacs.hass.services._services = {"frontend": {"reload_themes": None}}
    await task.execute_task()
    assert "theme" in hacs.common.categories
    hacs.hass.services._services = {}

    hacs.configuration.appdaemon = True
    await task.execute_task()
    assert "appdaemon" in hacs.common.categories
    hacs.configuration.appdaemon = False

    hacs.configuration.netdaemon = True
    await task.execute_task()
    assert "netdaemon" in hacs.common.categories
    hacs.configuration.netdaemon = False

    await task.execute_task()
    assert hacs.common.categories == {"integration", "plugin"}
