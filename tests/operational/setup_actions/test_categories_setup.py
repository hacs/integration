import pytest

from custom_components.hacs.operational.setup_actions.categories import (
    async_setup_extra_stores,
)


@pytest.mark.asyncio
async def test_extra_stores_python_script(hacs):

    await async_setup_extra_stores()

    assert "python_script" not in hacs.common.categories
    hacs.hass.config.components.add("python_script")
    await async_setup_extra_stores()
    assert "python_script" in hacs.common.categories

    hacs.hass.services._services["frontend"] = {"reload_themes": "dummy"}


@pytest.mark.asyncio
async def test_extra_stores_theme(hacs):
    await async_setup_extra_stores()

    assert "theme" not in hacs.common.categories
    hacs.hass.services._services["frontend"] = {"reload_themes": "dummy"}
    await async_setup_extra_stores()
    assert "theme" in hacs.common.categories
