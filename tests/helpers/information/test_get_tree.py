"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json

import aiohttp
import pytest

from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.helpers.functions.information import (
    get_repository,
    get_tree,
)

from tests.common import TOKEN
from tests.sample_data import (
    repository_data,
    response_rate_limit_header,
    response_rate_limit_header_with_limit,
    tree_files_base,
)


@pytest.mark.asyncio
async def test_get_tree(aresponses, event_loop):
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
        aresponses.Response(body=json.dumps(repository_data), headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/main",
        "get",
        aresponses.Response(body=json.dumps(tree_files_base), headers=response_rate_limit_header),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository, _ = await get_repository(session, TOKEN, "test/test")
        tree = await get_tree(repository, repository.default_branch)
        assert "hacs.json" in [x.full_path for x in tree]


@pytest.mark.asyncio
async def test_get_tree_exception(aresponses, event_loop):
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
        aresponses.Response(body=json.dumps(repository_data), headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header_with_limit, status=403),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/main",
        "get",
        aresponses.Response(
            body=json.dumps(tree_files_base),
            headers=response_rate_limit_header_with_limit,
            status=403,
        ),
    )
    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository, _ = await get_repository(session, TOKEN, "test/test")
        with pytest.raises(HacsException):
            await get_tree(repository, repository.default_branch)
