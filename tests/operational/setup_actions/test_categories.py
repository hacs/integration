import pytest
from custom_components.hacs.operational.setup_actions.categories import (
    async_setup_extra_stores,
)
from custom_components.hacs.share import get_hacs
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_extra_stores_python_script():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    await async_setup_extra_stores()

    assert "python_script" not in hacs.common.categories
    hacs.hass.config.components.add("python_script")
    await async_setup_extra_stores()
    assert "python_script" in hacs.common.categories

    hacs.hass.services._services["frontend"] = {"reload_themes": "dummy"}

    # Reset
    hacs.hass = HomeAssistant()


@pytest.mark.asyncio
async def test_extra_stores_theme():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    await async_setup_extra_stores()

    assert "theme" not in hacs.common.categories
    hacs.hass.services._services["frontend"] = {"reload_themes": "dummy"}
    await async_setup_extra_stores()
    assert "theme" in hacs.common.categories

    # Reset
    hacs.hass = HomeAssistant()
