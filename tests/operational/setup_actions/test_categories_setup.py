from custom_components.hacs.enums import HacsCategory
import pytest

from custom_components.hacs.operational.setup_actions.categories import (
    async_setup_extra_stores,
)


@pytest.mark.asyncio
async def test_extra_stores_python_script(hacs):
    await async_setup_extra_stores()
    assert HacsCategory.PYTHON_SCRIPT not in hacs.common.categories
    hacs.hass.config.components.add("python_script")
    await async_setup_extra_stores()
    assert HacsCategory.PYTHON_SCRIPT in hacs.common.categories


@pytest.mark.asyncio
async def test_extra_stores_theme(hacs):
    await async_setup_extra_stores()
    assert HacsCategory.THEME not in hacs.common.categories
    hacs.hass.services._services["frontend"] = {"reload_themes": "dummy"}
    await async_setup_extra_stores()
    assert HacsCategory.THEME in hacs.common.categories


@pytest.mark.asyncio
async def test_extra_stores_appdaemon(hacs):
    await async_setup_extra_stores()
    assert HacsCategory.APPDAEMON not in hacs.common.categories
    hacs.configuration.appdaemon = True
    await async_setup_extra_stores()
    assert HacsCategory.APPDAEMON in hacs.common.categories


@pytest.mark.asyncio
async def test_extra_stores_netdaemon(hacs):
    await async_setup_extra_stores()
    assert HacsCategory.NETDAEMON not in hacs.common.categories
    hacs.configuration.netdaemon = True
    await async_setup_extra_stores()
    assert HacsCategory.NETDAEMON in hacs.common.categories
