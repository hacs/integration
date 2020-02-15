"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json
import aiohttp
import pytest
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.helpers.information import get_releases, get_repository
from tests.sample_data import (
    response_rate_limit_header,
    repository_data,
    release_data,
    response_rate_limit_header_with_limit,
)

from tests.common import TOKEN


@pytest.mark.asyncio
async def test_get_releases(aresponses, event_loop):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(
            body=json.dumps(repository_data), headers=response_rate_limit_header
        ),
    )
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/releases",
        "get",
        aresponses.Response(
            body=json.dumps(release_data), headers=response_rate_limit_header
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = await get_repository(session, TOKEN, "test/test")
        tree = await get_releases(repository)
        assert "3" in [x.tag_name for x in tree]


@pytest.mark.asyncio
async def test_get_releases_exception(aresponses, event_loop):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(
            body=json.dumps(repository_data), headers=response_rate_limit_header
        ),
    )
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(
            body=b"{}", headers=response_rate_limit_header_with_limit, status=403
        ),
    )
    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = await get_repository(session, TOKEN, "test/test")
        with pytest.raises(HacsException):
            await get_releases(repository)
