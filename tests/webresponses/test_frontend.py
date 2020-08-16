import os
import pytest

from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.webresponses.frontend import async_serve_frontend


@pytest.mark.asyncio
async def test_frontend(hacs):
    await async_serve_frontend()


@pytest.mark.asyncio
async def test_frontend_debug(hacs):
    hacs.configuration.debug = True
    await async_serve_frontend()
    hacs.configuration = Configuration()


@pytest.mark.asyncio
async def test_frontend_repo(hacs, tmpdir):
    hacs.configuration.frontend_repo = tmpdir

    await async_serve_frontend()

    os.makedirs(f"{tmpdir}/hacs_frontend", exist_ok=True)
    with open(f"{tmpdir}/hacs_frontend/main.js", "w") as target:
        target.write("")

    await async_serve_frontend()

    hacs.configuration = Configuration()


@pytest.mark.asyncio
async def test_frontend_frontend_repo_url(hacs, aresponses):
    aresponses.add(
        "127.0.0.1", "/main.js", "get", "",
    )
    hacs.configuration.frontend_repo_url = "http://127.0.0.1"
    await async_serve_frontend()
