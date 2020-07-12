import pytest

from homeassistant.core import HomeAssistant

from custom_components.hacs.share import get_hacs
from custom_components.hacs.repositories import HacsTheme


@pytest.mark.asyncio
async def test_async_post_installation():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsTheme("test/test")
    repository.hacs = hacs
    await repository.async_post_installation()


@pytest.mark.asyncio
async def test_async_post_registration():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsTheme("test/test")
    repository.hacs = hacs
    await repository.async_post_registration()
