import pytest

from homeassistant.core import HomeAssistant

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.share import get_hacs
from custom_components.hacs.repositories import HacsIntegration


@pytest.mark.asyncio
async def test_async_post_installation():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsIntegration("test/test")
    repository.hacs = hacs
    await repository.async_post_installation()

    repository.data.config_flow = True
    repository.data.first_install = True
    hacs.hass.data["custom_components"] = []
    await repository.async_post_installation()


@pytest.mark.asyncio
async def test_async_post_registration():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsIntegration("test/test")
    repository.hacs = hacs
    await repository.async_post_registration()


@pytest.mark.asyncio
async def test_reload_custom_components():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.hass.data["custom_components"] = []
    repository = HacsIntegration("test/test")
    repository.hacs = hacs
    await repository.reload_custom_components()


@pytest.mark.asyncio
async def test_validate_repository():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsIntegration("test/test")
    repository.hacs = hacs
    with pytest.raises(HacsException):
        await repository.validate_repository()


@pytest.mark.asyncio
async def test_update_repository():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsIntegration("test/test")
    repository.hacs = hacs
    with pytest.raises(HacsException):
        await repository.update_repository(True)
