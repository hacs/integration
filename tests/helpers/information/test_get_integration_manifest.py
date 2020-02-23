"""Helpers: Information: get_integration_manifest."""
# pylint: disable=missing-docstring
import base64
import json
import aiohttp
import pytest
from aiogithubapi import AIOGithubTreeContent
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.helpers.information import (
    get_integration_manifest,
    get_repository,
)
from tests.common import TOKEN
from tests.dummy_repository import dummy_repository_integration
from tests.sample_data import (
    response_rate_limit_header,
    repository_data,
    integration_manifest,
)


@pytest.mark.asyncio
async def test_get_integration_manifest(aresponses, event_loop):
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
    content = base64.b64encode(json.dumps(integration_manifest).encode("utf-8"))
    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/custom_components/test/manifest.json",
        "get",
        aresponses.Response(
            body=json.dumps({"content": content.decode("utf-8")}),
            headers=response_rate_limit_header,
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = dummy_repository_integration()
        repository.repository_object = await get_repository(session, TOKEN, "test/test")
        repository.content.path.remote = "custom_components/test"
        repository.tree = [
            AIOGithubTreeContent(
                {"path": "custom_components/test/manifest.json", "type": "blob"},
                "test/test",
                "master",
            )
        ]
        await get_integration_manifest(repository)
        assert repository.data.domain == integration_manifest["domain"]


@pytest.mark.asyncio
async def test_get_integration_manifest_no_file(aresponses, event_loop):
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
        repository = dummy_repository_integration()
        repository.repository_object = await get_repository(session, TOKEN, "test/test")
        repository.content.path.remote = "custom_components/test"
        with pytest.raises(HacsException):
            await get_integration_manifest(repository)


@pytest.mark.asyncio
async def test_get_integration_manifest_format_issue(aresponses, event_loop):
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
        "/repos/test/test/contents/custom_components/test/manifest.json",
        "get",
        aresponses.Response(
            body=json.dumps({"content": {"wrong": "format"}}),
            headers=response_rate_limit_header,
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = dummy_repository_integration()
        repository.repository_object = await get_repository(session, TOKEN, "test/test")
        repository.content.path.remote = "custom_components/test"
        repository.tree = [
            AIOGithubTreeContent(
                {"path": "custom_components/test/manifest.json", "type": "blob"},
                "test/test",
                "master",
            )
        ]
        with pytest.raises(HacsException):
            await get_integration_manifest(repository)


@pytest.mark.asyncio
async def test_get_integration_manifest_missing_required_key(aresponses, event_loop):
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
    del integration_manifest["domain"]
    content = base64.b64encode(json.dumps(integration_manifest).encode("utf-8"))
    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/custom_components/test/manifest.json",
        "get",
        aresponses.Response(
            body=json.dumps({"content": content.decode("utf-8")}),
            headers=response_rate_limit_header,
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        repository = dummy_repository_integration()
        repository.repository_object = await get_repository(session, TOKEN, "test/test")
        repository.content.path.remote = "custom_components/test"
        repository.tree = [
            AIOGithubTreeContent(
                {"path": "custom_components/test/manifest.json", "type": "blob"},
                "test/test",
                "master",
            )
        ]
        with pytest.raises(HacsException):
            await get_integration_manifest(repository)
