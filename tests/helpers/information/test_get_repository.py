"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json
import aiohttp
import pytest
from custom_components.hacs.helpers.information import get_repository
from tests.sample_data import response_rate_limit_header, repository_data

TOKEN = "xxxxxxxxxxxxxxxxxxxxxxx"


@pytest.mark.asyncio
async def test_get_repository(aresponses, event_loop):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(
            body=json.dumps(repository_data), headers=response_rate_limit_header
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = await get_repository(session, TOKEN, "test/test")
        assert repository.attributes["full_name"] == "test/test"
