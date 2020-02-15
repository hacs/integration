"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json
import aiohttp
import pytest
from custom_components.hacs.helpers.information import get_tree, get_repository
from tests.sample_data import (
    response_rate_limit_header,
    repository_data,
    tree_files_base_integration,
)

TOKEN = "xxxxxxxxxxxxxxxxxxxxxxx"


@pytest.mark.asyncio
async def test_base(aresponses, event_loop):
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
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/master",
        "get",
        aresponses.Response(
            body=json.dumps(tree_files_base_integration()),
            headers=response_rate_limit_header,
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = await get_repository(session, TOKEN, "test/test")
        tree = await get_tree(repository, repository.default_branch)
        filestocheck = [
            "custom_components/test/__init__.py",
            "custom_components/test/.translations/en.json",
            "custom_components/test/manifest.json",
        ]
        for check in filestocheck:
            assert check in [x.full_path for x in tree]
