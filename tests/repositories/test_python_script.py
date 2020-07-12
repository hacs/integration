import pytest

from homeassistant.core import HomeAssistant

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.share import get_hacs
from custom_components.hacs.repositories import HacsPythonScript


@pytest.mark.asyncio
async def test_async_post_registration():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsPythonScript("test/test")
    repository.hacs = hacs
    await repository.async_post_registration()


@pytest.mark.asyncio
async def test_validate_repository():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsPythonScript("test/test")
    repository.hacs = hacs
    with pytest.raises(HacsException):
        await repository.validate_repository()


@pytest.mark.asyncio
async def test_update_repository():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsPythonScript("test/test")
    repository.hacs = hacs
    with pytest.raises(HacsException):
        await repository.update_repository(True)
