"""Helpers: Download: download_content."""
# pylint: disable=missing-docstring
import os
import aiohttp
import pytest
from aiogithubapi.content import AIOGithubTreeContent

from custom_components.hacs.helpers.download import download_content

from custom_components.hacs.globals import get_hacs
from tests.dummy_repository import dummy_repository_base, dummy_repository_integration
from tests.sample_data import response_rate_limit_header


@pytest.mark.asyncio
async def test_download_content(aresponses, tmp_path, event_loop):
    aresponses.add(
        "raw.githubusercontent.com",
        "/test/test/master/test/path/file.file",
        "get",
        aresponses.Response(body="test", headers=response_rate_limit_header),
    )

    repository = dummy_repository_base()
    repository.content.path.remote = ""
    repository.content.path.local = tmp_path
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "test/path/file.file", "type": "blob"}, "test/test", "master"
        )
    ]
    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs = get_hacs()
        hacs.hass.loop = event_loop
        hacs.session = session
        await download_content(repository)
        assert os.path.exists(f"{repository.content.path.local}/test/path/file.file")


@pytest.mark.asyncio
async def test_download_content_integration(aresponses, tmp_path, event_loop):
    aresponses.add(
        "raw.githubusercontent.com",
        aresponses.ANY,
        "get",
        aresponses.Response(body="", headers=response_rate_limit_header),
    )
    aresponses.add(
        "raw.githubusercontent.com",
        aresponses.ANY,
        "get",
        aresponses.Response(body="", headers=response_rate_limit_header),
    )
    aresponses.add(
        "raw.githubusercontent.com",
        aresponses.ANY,
        "get",
        aresponses.Response(body="", headers=response_rate_limit_header),
    )
    aresponses.add(
        "raw.githubusercontent.com",
        aresponses.ANY,
        "get",
        aresponses.Response(body="", headers=response_rate_limit_header),
    )
    hacs = get_hacs()
    hacs.system.config_path = tmp_path
    repository = dummy_repository_integration()
    repository.domain = "test"
    repository.content.path.local = repository.localpath
    repository.content.path.remote = "custom_components/test"
    integration_files = [
        "__init__.py",
        "sensor.py",
        ".translations/en.json",
        "manifest.json",
    ]
    for integration_file in integration_files:
        repository.tree.append(
            AIOGithubTreeContent(
                {"path": f"custom_components/test/{integration_file}", "type": "blob"},
                "test/test",
                "master",
            )
        )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        hacs.hass.loop = event_loop
        hacs.session = session
        await download_content(repository)
        for path in repository.tree:
            assert os.path.exists(f"{hacs.system.config_path}/{path.full_path}")
