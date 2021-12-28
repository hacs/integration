# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock, MagicMock

from aiogithubapi import (
    GitHubAuthenticationException,
    GitHubRatelimitException,
    GitHubRateLimitModel,
    GitHubResponseModel,
)
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsDisabledReason


@pytest.mark.asyncio
async def test_verify_api_everything_is_good(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.githubapi = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("verify_api")

    assert task

    response = GitHubResponseModel(MagicMock(headers={}))
    response.data = GitHubRateLimitModel({"resources": {"core": {"remaining": 5000}}})
    hacs.githubapi.rate_limit.return_value = response
    await task.execute_task()
    assert "Can update" in caplog.text
    assert "Can update 0 repositories" not in caplog.text


@pytest.mark.asyncio
async def test_verify_api_ratelimited_value(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.githubapi = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("verify_api")

    assert task
    assert not hacs.system.disabled

    response = GitHubResponseModel(MagicMock(headers={}))
    response.data = GitHubRateLimitModel({"resources": {"core": {"remaining": 0}}})
    hacs.githubapi.rate_limit.return_value = response
    await task.execute_task()
    assert "Can update 0 repositories" in caplog.text
    assert "GitHub API ratelimited - 0 remaining" in caplog.text
    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.RATE_LIMIT


@pytest.mark.asyncio
async def test_verify_api_ratelimited_exception(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.githubapi = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("verify_api")

    assert task
    assert not hacs.system.disabled

    hacs.githubapi.rate_limit.side_effect = GitHubRatelimitException

    await task.execute_task()
    assert "Can update 0 repositories" in caplog.text
    assert "GitHub API ratelimited -" in caplog.text
    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.RATE_LIMIT


@pytest.mark.asyncio
async def test_verify_api_authentication_exception(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    hacs.githubapi = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("verify_api")

    assert task
    assert not hacs.system.disabled

    hacs.githubapi.rate_limit.side_effect = GitHubAuthenticationException
    await task.execute_task()
    assert "Can update 0 repositories" in caplog.text
    assert "GitHub authentication failed -" in caplog.text
    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.INVALID_TOKEN


@pytest.mark.asyncio
async def test_verify_api_base_exception(hacs: HacsBase, caplog: pytest.LogCaptureFixture):
    hacs.githubapi = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("verify_api")

    assert task
    assert not hacs.system.disabled

    hacs.githubapi.rate_limit.side_effect = BaseException
    await task.execute_task()
    assert "Can update 0 repositories" in caplog.text
    assert not hacs.system.disabled
