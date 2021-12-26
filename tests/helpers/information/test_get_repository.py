"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json

import aiohttp
import pytest

from custom_components.hacs.exceptions import HacsException

from tests.common import TOKEN
from tests.sample_data import (
    repository_data,
    response_rate_limit_header,
    response_rate_limit_header_with_limit,
)


@pytest.mark.asyncio
async def test_get_repository(aresponses, repository_integration):
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
        aresponses.Response(body=json.dumps(repository_data), headers=response_rate_limit_header),
    )

    repository, _ = await repository_integration.async_get_legacy_repository_object()
    assert repository.attributes["full_name"] == "test/test"


@pytest.mark.asyncio
async def test_get_repository_exception(aresponses, repository_integration):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header_with_limit, status=403),
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
        await repository_integration.async_get_legacy_repository_object()
