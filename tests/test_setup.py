"""HACS Setup Test Suite."""
# pylint: disable=missing-docstring
import json
import os

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.operational.setup_actions.clear_storage import (
    async_clear_storage,
)
from custom_components.hacs.operational.setup_actions.load_hacs_repository import (
    async_load_hacs_repository,
)
from custom_components.hacs.share import get_hacs
from tests.sample_data import (
    release_data,
    repository_data,
    response_rate_limit_header,
    tree_files_base_integration,
)

TOKEN = "xxxxxxxxxxxxxxxxxxxxxxx"


@pytest.mark.asyncio
async def test_clear_storage(tmpdir):
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    hacs.system.config_path = tmpdir.dirname
    os.makedirs(f"{hacs.system.config_path}/.storage")
    with open(f"{hacs.system.config_path}/.storage/hacs", "w") as h_f:
        h_f.write("")
    await async_clear_storage()
    os.makedirs(f"{hacs.system.config_path}/.storage/hacs")
    await async_clear_storage()


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
        await async_load_hacs_repository()
