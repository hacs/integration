import pytest

from homeassistant.core import HomeAssistant

from custom_components.hacs.share import get_hacs
from custom_components.hacs.repositories import HacsAppdaemon


@pytest.mark.asyncio
async def test_base():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsAppdaemon("test/test")
    repository.hacs = hacs
    assert repository.data.category == "appdaemon"
