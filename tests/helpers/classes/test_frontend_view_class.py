import pytest
from homeassistant.core import HomeAssistant
from custom_components.hacs.helpers.classes.frontend_view import HacsFrontend
from custom_components.hacs.share import get_hacs
from custom_components.hacs.hacsbase.configuration import Configuration


@pytest.mark.asyncio
async def test_frontend_view_class():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.configuration = Configuration()
    frontend = HacsFrontend()
    await frontend.get({}, "test")
    await frontend.get({}, "class-map.js.map")
    await frontend.get({}, "frontend-test")
    await frontend.get({}, "iconset.js")
