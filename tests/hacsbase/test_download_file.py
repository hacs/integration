"""Exercise download response headers with aiohttp's real HTTP parser."""

from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer
import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.parametrize("redirect", [False, True])
@pytest.mark.parametrize(
    ("header_size", "expected"),
    [(100, b"release archive"), (10 * 1024, b"release archive"), (64 * 1024 + 1, None)],
)
async def test_download_response_header_size(header_size, expected, redirect):
    """Accept GitHub-sized CSP headers while retaining a bounded parser limit."""
    app = web.Application()

    async def download(request):
        headers = {"Content-Security-Policy": "x" * header_size}
        if redirect:
            headers["Location"] = "/asset.zip"
            return web.Response(status=302, headers=headers)
        return web.Response(body=b"release archive", headers=headers)

    async def asset(request):
        return web.Response(body=b"release archive")

    app.router.add_get("/download", download)
    app.router.add_get("/asset.zip", asset)

    async with TestServer(app) as server, ClientSession() as session:
        hacs = HacsBase()
        hacs.session = session

        assert await hacs.async_download_file(str(server.make_url("/download"))) == expected
