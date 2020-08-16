import os

import pytest

from custom_components.hacs.webresponses.category import async_serve_category_file


@pytest.mark.asyncio
async def test_categpry(hacs, tmpdir):
    hacs.system.config_path = tmpdir
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
