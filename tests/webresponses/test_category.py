import os
import pytest
from homeassistant.core import HomeAssistant

from custom_components.hacs.webresponses.category import async_serve_category_file
from custom_components.hacs.hacsbase.configuration import Configuration

from custom_components.hacs.share import get_hacs


@pytest.mark.asyncio
async def test_categpry(tmpdir):
    hacs = get_hacs()
    hacs.system.config_path = tmpdir
    hacs.hass = HomeAssistant()
    await async_serve_category_file("test")
    await async_serve_category_file("themes/test")
    await async_serve_category_file(None)

    os.makedirs(f"{tmpdir}", exist_ok=True)
    os.makedirs(f"{tmpdir}/www/community", exist_ok=True)
    with open(f"{tmpdir}/test.gz", "w") as test:
        test.write("")
    with open(f"{tmpdir}/www/community/test.gz", "w") as test:
        test.write("")
    await async_serve_category_file("test")
