"""HACS Setup Test Suite."""
# pylint: disable=missing-docstring
import json
import aiohttp
import pytest
from custom_components.hacs.hacsbase import Hacs
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.setup import load_hacs_repository
from tests.sample_data import (
    response_rate_limit_header,
    repository_data,
    tree_files_base_integration,
    release_data,
)

TOKEN = "xxxxxxxxxxxxxxxxxxxxxxx"


@pytest.mark.asyncio
async def _load_hacs_repository(aresponses, event_loop):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/hacs/integration",
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
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/releases",
        "get",
        aresponses.Response(
            body=json.dumps(release_data), headers=response_rate_limit_header
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
        "/repos/test/test/contents/hacs.json",
        "get",
        aresponses.Response(
            body=json.dumps({"name": "test"}), headers=response_rate_limit_header
        ),
    )
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    async with aiohttp.ClientSession(loop=event_loop) as session:
        Hacs.session = session
        Hacs.configuration = Configuration()
        Hacs.configuration.token = TOKEN
        await load_hacs_repository(Hacs)
