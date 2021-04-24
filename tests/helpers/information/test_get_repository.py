"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json

import aiohttp
import pytest

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.information import get_repository
from tests.common import TOKEN
from tests.sample_data import (
    repository_data,
    response_rate_limit_header,
    response_rate_limit_header_with_limit,
)


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

    repository, _ = await get_repository("test/test")
    assert repository.attributes["full_name"] == "test/test"


@pytest.mark.asyncio
async def test_get_repository_exception(aresponses, event_loop):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(
            body=b"{}", headers=response_rate_limit_header_with_limit, status=403
        ),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(
            body=json.dumps(repository_data),
            headers=response_rate_limit_header_with_limit,
            status=403,
        ),
    )
    with pytest.raises(HacsException):
        await get_repository("test/test")
