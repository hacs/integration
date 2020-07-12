import os
import pytest
import aiohttp
from homeassistant.core import HomeAssistant

from custom_components.hacs.webresponses.frontend import async_serve_frontend
from custom_components.hacs.hacsbase.configuration import Configuration

from custom_components.hacs.share import get_hacs


@pytest.mark.asyncio
async def test_frontend():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    await async_serve_frontend()


@pytest.mark.asyncio
async def test_frontend_debug():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.configuration = Configuration()
    hacs.configuration.debug = True
    await async_serve_frontend()
    hacs.configuration = Configuration()


@pytest.mark.asyncio
async def test_frontend_repo(tmpdir):
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.configuration = Configuration()
    hacs.configuration.frontend_repo = tmpdir

    await async_serve_frontend()

    os.makedirs(f"{tmpdir}/hacs_frontend", exist_ok=True)
    with open(f"{tmpdir}/hacs_frontend/main.js", "w") as target:
        target.write("")

    await async_serve_frontend()

    hacs.configuration = Configuration()


@pytest.mark.asyncio
async def test_frontend_frontend_repo_url(aresponses, event_loop):
    aresponses.add(
        "127.0.0.1", "/main.js", "get", "",
    )

    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.configuration = Configuration()
    hacs.configuration.frontend_repo_url = "http://127.0.0.1"
    await async_serve_frontend()

    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs.session = session
        await async_serve_frontend()
        hacs.configuration = Configuration()
