"""Helpers: Information: get_integration_manifest."""
# pylint: disable=missing-docstring
import base64
import json

from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import aiohttp
import pytest

from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.utils.information import get_integration_manifest

from tests.common import TOKEN
from tests.sample_data import (
    integration_manifest,
    repository_data,
    response_rate_limit_header,
)


@pytest.mark.asyncio
async def test_get_integration_manifest(repository_integration, aresponses):
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

    (
        repository_integration.repository_object,
        _,
    ) = await repository_integration.async_get_legacy_repository_object(etag=None)
    repository_integration.content.path.remote = "custom_components/test"
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/manifest.json", "type": "blob"},
            "test/test",
            "main",
        )
    ]
    await get_integration_manifest(repository_integration)
    assert repository_integration.data.domain == integration_manifest["domain"]


@pytest.mark.asyncio
async def test_get_integration_manifest_no_file(repository_integration, aresponses, event_loop):
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

    (
        repository_integration.repository_object,
        _,
    ) = await repository_integration.async_get_legacy_repository_object()
    repository_integration.content.path.remote = "custom_components/test"
    with pytest.raises(HacsException):
        await get_integration_manifest(repository_integration)


@pytest.mark.asyncio
async def test_get_integration_manifest_format_issue(repository_integration, aresponses):
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

    (
        repository_integration.repository_object,
        _,
    ) = await repository_integration.async_get_legacy_repository_object()
    repository_integration.content.path.remote = "custom_components/test"
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/manifest.json", "type": "blob"},
            "test/test",
            "main",
        )
    ]
    with pytest.raises(HacsException):
        await get_integration_manifest(repository_integration)


@pytest.mark.asyncio
async def test_get_integration_manifest_missing_required_key(
    repository_integration, aresponses, event_loop
):
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

    (
        repository_integration.repository_object,
        _,
    ) = await repository_integration.async_get_legacy_repository_object()
    repository_integration.content.path.remote = "custom_components/test"
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "custom_components/test/manifest.json", "type": "blob"},
            "test/test",
            "main",
        )
    ]
    with pytest.raises(HacsException):
        await get_integration_manifest(repository_integration)
