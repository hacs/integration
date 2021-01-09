import pytest

from custom_components.hacs.helpers.classes.frontend_view import HacsFrontend


@pytest.mark.asyncio
async def test_frontend_view_class(hacs):
    frontend = HacsFrontend()
    await frontend.get({}, "test")
    await frontend.get({}, "class-map.js.map")
    await frontend.get({}, "frontend-test")
    await frontend.get({}, "iconset.js")
