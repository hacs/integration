"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json
import aiohttp
import pytest
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.helpers.validate_repository import common_validate
from tests.sample_data import (
    response_rate_limit_header,
    response_rate_limit_header_with_limit,
    repository_data,
    tree_files_base,
    repository_data_archived,
    release_data,
)
from tests.dummy_repository import dummy_repository_base
from tests.common import TOKEN


@pytest.mark.asyncio
async def test_common_base(aresponses, event_loop):
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
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/3",
        "get",
        aresponses.Response(
            body=json.dumps(tree_files_base), headers=response_rate_limit_header
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
        "/repos/test/test/contents/hacs.json",
        "get",
        aresponses.Response(body=json.dumps({}), headers=response_rate_limit_header),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        repository = dummy_repository_base()
        repository.ref = None
        await common_validate(repository)


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
            body=json.dumps({"message": "X"}),
            headers=response_rate_limit_header_with_limit,
            status=403,
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
        "/repos/test/test/git/trees/3",
        "get",
        aresponses.Response(
            body=json.dumps(tree_files_base), headers=response_rate_limit_header
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
        "/repos/test/test/contents/hacs.json",
        "get",
        aresponses.Response(body=json.dumps({}), headers=response_rate_limit_header),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        repository = dummy_repository_base()
        repository.ref = None
        await common_validate(repository)
        assert not repository.releases.releases


@pytest.mark.asyncio
async def test_common_archived(aresponses, event_loop):
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
            body=json.dumps(repository_data_archived()),
            headers=response_rate_limit_header,
        ),
    )
    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        repository = dummy_repository_base()
        repository.data.archived = True
        with pytest.raises(HacsException):
            await common_validate(repository)


@pytest.mark.asyncio
async def test_common_blacklist(aresponses, event_loop):
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
    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        hacs.common.blacklist.append("test/test")
        repository = dummy_repository_base()
        with pytest.raises(HacsException):
            await common_validate(repository)
        hacs.common.blacklist = []


@pytest.mark.asyncio
async def test_common_base_exception_does_not_exsist(aresponses, event_loop):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(headers=response_rate_limit_header_with_limit, status=500),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(
            body=json.dumps({"message": "X"}),
            headers=response_rate_limit_header_with_limit,
            status=500,
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        hacs.system.status.startup = False
        repository = dummy_repository_base()
        with pytest.raises(HacsException):
            await common_validate(repository)


@pytest.mark.asyncio
async def test_common_base_exception_tree_issues(aresponses, event_loop):
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
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/3",
        "get",
        aresponses.Response(
            body=json.dumps({"message": "X"}), headers=response_rate_limit_header
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        repository = dummy_repository_base()
        hacs.common.blacklist = []
        hacs.system.status.startup = False
        with pytest.raises(HacsException):
            await common_validate(repository)
