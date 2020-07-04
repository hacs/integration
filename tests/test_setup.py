"""HACS Setup Test Suite."""
# pylint: disable=missing-docstring
import json
import os

import aiohttp
import pytest

from custom_components.hacs.globals import get_hacs
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.setup import clear_storage, load_hacs_repository
from tests.sample_data import (
    release_data,
    repository_data,
    response_rate_limit_header,
    tree_files_base_integration,
)

TOKEN = "xxxxxxxxxxxxxxxxxxxxxxx"


def test_clear_storage(tmpdir):
    hacs = get_hacs()
    hacs.system.config_path = tmpdir.dirname
    os.makedirs(f"{hacs.system.config_path}/.storage")
    with open(f"{hacs.system.config_path}/.storage/hacs", "w") as h_f:
        h_f.write("")
    clear_storage()
    os.makedirs(f"{hacs.system.config_path}/.storage/hacs")
    clear_storage()


@pytest.mark.asyncio
async def _load_hacs_repository(aresponses, event_loop):
    hacs = get_hacs()
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
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        await load_hacs_repository()
