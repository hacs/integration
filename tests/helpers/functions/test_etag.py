"""Tests for etag."""
import asyncio
import os
import time

import pytest
from custom_components.hacs.helpers.functions.file_etag import async_get_etag
from custom_components.hacs.webresponses.category import async_serve_category_file


class MockRequest:
    headers = {}
    remote = ""


@pytest.mark.asyncio
async def test_etag(tmpdir, hacs):
    testfile = f"{tmpdir}/test"
    with open(testfile, "w") as test_file:
        test_file.write("")
    assert await async_get_etag(testfile) == "0x811c9dc5"


@pytest.mark.asyncio
async def test_etag_no_file(tmpdir, hacs):
    testfile = f"{tmpdir}/test"
    assert not await async_get_etag(testfile)


@pytest.mark.asyncio
async def test_etag_with_web_response(tmpdir, hacs):
    request = MockRequest()
    os.makedirs(f"{tmpdir}/www/community", exist_ok=True)
    testfile = f"{tmpdir}/www/community/test.gz"
    with open(testfile, "w") as test_file:
        test_file.write("")

    req1 = await async_serve_category_file(request, "test.gz")
    request.headers["if-none-match"] = req1.headers.get("Etag")

    req2 = await async_serve_category_file(request, "test.gz")

    with open(testfile, "w") as test_file:
        test_file.write("change")

    req3 = await async_serve_category_file(request, "test.gz")
    request.headers["if-none-match"] = req3.headers.get("Etag")

    assert req1.status == 200
    assert req2.status == 304
    assert req3.status == 200

    start_time = time.time()

    async def test_304():
        assert (await async_serve_category_file(request, "test.gz")).status == 304

    await asyncio.gather(*[test_304() for _ in range(0, 1000)])
    print("--- %s seconds ---" % (time.time() - start_time))
    assert (time.time() - start_time) < 1
