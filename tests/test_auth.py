"""Tests for expiring GitHub credentials."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from aiogithubapi import (
    GitHub,
    GitHubAPI,
    GitHubAuthenticationException,
    GitHubException,
)
from aiohttp import ClientError
from homeassistant.const import (
    EVENT_HOMEASSISTANT_FINAL_WRITE,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
import pytest

from custom_components.hacs.auth import TOKEN_ENDPOINT, GitHubTokenManager, token_data
from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import CLIENT_ID
from custom_components.hacs.diagnostics import async_get_config_entry_diagnostics
from custom_components.hacs.enums import HacsDisabledReason

from tests.common import TOKEN, MockedResponse, create_config_entry


def expiring_data():
    return {
        "token": TOKEN,
        "refresh_token": "old-refresh",
        "expires_at": time.time() + 60,
        "refresh_token_expires_at": time.time() + 86400,
    }


def refreshed_data():
    return {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "expires_in": 28800,
        "refresh_token_expires_in": 15897600,
    }


@pytest.fixture
def oauth_response():
    response = AsyncMock()
    response.status = 200
    response.json.return_value = refreshed_data()
    return response


@pytest.fixture
def manager(hass, oauth_response):
    entry = create_config_entry(data=expiring_data())
    entry.add_to_hass(hass)
    session = MagicMock()
    session.post.return_value.__aenter__.return_value = oauth_response
    return GitHubTokenManager(hass, entry, session)


@pytest.mark.parametrize(
    "response",
    [
        {"access_token": ""},
        {"access_token": TOKEN, "refresh_token": "refresh"},
        {**refreshed_data(), "expires_in": -1},
        {**refreshed_data(), "refresh_token_expires_in": "86400"},
    ],
)
def test_invalid_token_response(response):
    with pytest.raises(GitHubException):
        token_data(response, time.time())


async def test_non_expiring_token_does_not_refresh(manager, hass):
    hass.config_entries.async_update_entry(manager.entry, data={"token": TOKEN})
    assert await manager.async_get_token() == TOKEN
    manager.session.post.assert_not_called()


async def test_valid_token_does_not_refresh(manager, hass):
    hass.config_entries.async_update_entry(
        manager.entry, data={**expiring_data(), "expires_at": time.time() + 3600}
    )
    assert await manager.async_get_token() == TOKEN
    manager.session.post.assert_not_called()


async def test_refresh_rotates_and_persists_once_for_concurrent_requests(manager):
    assert await asyncio.gather(*(manager.async_get_token() for _ in range(5))) == ["new-access"] * 5
    assert manager.entry.data == {
        "token": "new-access",
        "refresh_token": "new-refresh",
        "expires_at": time.time() + 28800,
        "refresh_token_expires_at": time.time() + 15897600,
    }
    manager.session.post.assert_called_once()
    args, kwargs = manager.session.post.call_args
    assert args == (TOKEN_ENDPOINT,)
    assert kwargs["data"] == {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": "old-refresh",
    }
    assert kwargs["headers"] == {"Accept": "application/json"}
    assert kwargs["allow_redirects"] is False
    assert await manager.async_get_token() == "new-access"
    manager.session.post.assert_called_once()


async def test_cancelled_caller_does_not_lose_rotated_tokens(manager, oauth_response):
    started = asyncio.Event()
    finish = asyncio.Event()

    async def delayed_response():
        started.set()
        await finish.wait()
        return refreshed_data()

    oauth_response.json.side_effect = delayed_response
    caller = asyncio.create_task(manager.async_get_token())
    await started.wait()
    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller
    finish.set()
    assert await manager.async_get_token() == "new-access"
    assert manager.entry.data["refresh_token"] == "new-refresh"
    manager.session.post.assert_called_once()


@pytest.mark.parametrize("error", ["bad_refresh_token", "invalid_grant"])
async def test_rejected_refresh_requires_reauth_without_retry(manager, oauth_response, error):
    oauth_response.json.return_value = {"error": error}
    for _ in range(2):
        with pytest.raises(GitHubAuthenticationException):
            await manager.async_get_token()
    manager.session.post.assert_called_once()
    assert manager.entry.data == expiring_data()


async def test_expired_refresh_token_does_not_call_github(manager, hass):
    hass.config_entries.async_update_entry(
        manager.entry, data={**expiring_data(), "refresh_token_expires_at": time.time() - 1}
    )
    with pytest.raises(GitHubAuthenticationException):
        await manager.async_get_token()
    manager.session.post.assert_not_called()


@pytest.mark.parametrize("failure", ["network", "server", "malformed"])
async def test_temporary_refresh_failure_preserves_credentials_and_can_retry(
    manager, oauth_response, time_freezer, failure
):
    original = dict(manager.entry.data)
    if failure == "network":
        oauth_response.json.side_effect = ClientError("offline")
    elif failure == "server":
        oauth_response.status = 503
        oauth_response.json.return_value = {"error": "temporarily_unavailable"}
    else:
        oauth_response.json.return_value = {"access_token": "incomplete"}
    for _ in range(2):
        with pytest.raises(GitHubException) as exception:
            await manager.async_get_token()
        assert not isinstance(exception.value, GitHubAuthenticationException)
    assert manager.entry.data == original
    manager.session.post.assert_called_once()

    time_freezer.tick(31)
    oauth_response.status = 200
    oauth_response.json.side_effect = None
    oauth_response.json.return_value = refreshed_data()
    assert await manager.async_get_token() == "new-access"


@pytest.mark.parametrize("response", [refreshed_data(), {"error": "invalid_grant"}])
async def test_refresh_does_not_overwrite_reauthentication(manager, oauth_response, hass, response):
    async def reauthenticate_during_refresh():
        hass.config_entries.async_update_entry(manager.entry, data={"token": "reauthorized"})
        return response

    oauth_response.json.side_effect = reauthenticate_during_refresh
    with pytest.raises(GitHubException, match="changed during"):
        await manager.async_get_token()
    assert manager.entry.data == {"token": "reauthorized"}


async def test_unload_waits_for_rotation(manager, oauth_response):
    started = asyncio.Event()
    finish = asyncio.Event()

    async def delayed_response():
        started.set()
        await finish.wait()
        return refreshed_data()

    oauth_response.json.side_effect = delayed_response
    caller = asyncio.create_task(manager.async_get_token())
    await started.wait()
    closing = asyncio.create_task(manager.async_close())
    await asyncio.sleep(0)
    assert not closing.done()
    with pytest.raises(GitHubException, match="unloading"):
        await manager.async_get_token()
    finish.set()
    await closing
    assert await caller == "new-access"
    assert manager.entry.data["refresh_token"] == "new-refresh"


async def test_shutdown_finishes_rotation_before_final_write(manager, oauth_response, hass):
    started = asyncio.Event()
    finish = asyncio.Event()
    stopping = asyncio.Event()
    saved_tokens = []

    async def delayed_response():
        started.set()
        await finish.wait()
        return refreshed_data()

    @callback
    def on_stop(_event):
        stopping.set()

    @callback
    def on_final_write(_event):
        saved_tokens.append(manager.entry.data["refresh_token"])

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_stop)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_FINAL_WRITE, on_final_write)
    oauth_response.json.side_effect = delayed_response
    caller = asyncio.create_task(manager.async_get_token())
    await started.wait()
    shutdown = asyncio.create_task(hass.async_stop())
    await stopping.wait()
    await asyncio.sleep(0)
    finish.set()
    await shutdown
    result = await asyncio.gather(caller, return_exceptions=True)
    assert saved_tokens == ["new-refresh"]
    assert result == ["new-access"]
    assert manager._closed


async def test_close_does_not_repeat_completed_refresh_failure(manager, oauth_response, caplog):
    oauth_response.json.return_value = {"error": "invalid_grant"}
    with pytest.raises(GitHubAuthenticationException):
        await manager.async_get_token()
    caplog.clear()
    await manager.async_close()
    assert "refresh failed while unloading" not in caplog.text


@pytest.mark.parametrize("refreshable", [False, True])
async def test_contents_request_preserves_media_type(manager, hass, refreshable):
    if not refreshable:
        hass.config_entries.async_update_entry(manager.entry, data={"token": TOKEN})
    session = MagicMock()
    session.request = AsyncMock(return_value=MockedResponse(
        content={"type": "file", "name": "hacs.json", "content": "e30=", "encoding": "base64"},
        headers={"Content-Type": "application/json"},
    ))
    hacs = HacsBase()
    hacs.auth = manager
    hacs.github = GitHub(TOKEN, session)
    hacs.githubapi = GitHubAPI(token=TOKEN, session=session)
    method = hacs.githubapi.repos.contents.get
    await hacs.async_github_api_method(method, repository="example/repo", path="hacs.json")
    headers = session.request.call_args.kwargs["headers"]
    assert headers["Accept"] == "application/vnd.github.v3+json"
    expected_token = "new-access" if refreshable else TOKEN
    assert headers["Authorization"] == f"token {expected_token}"


async def test_refreshed_credentials_reach_both_clients_without_reload(
    hacs, oauth_response, response_mocker
):
    entry = hacs.configuration.config_entry
    hacs.hass.config_entries.async_update_entry(entry, data=expiring_data())
    with (
        patch.object(hacs.auth.session, "post") as post,
        patch("custom_components.hacs.async_reload_entry") as reload_entry,
    ):
        post.return_value.__aenter__.return_value = oauth_response
        api_method = AsyncMock()
        await hacs.async_github_api_method(api_method, headers={"Accept": "custom"})
        api_method.assert_awaited_once_with(headers={"Accept": "custom"})
        assert hacs.github.client.headers["Authorization"] == "token new-access"
        assert hacs.configuration.token == "new-access"
        await hacs.hass.async_block_till_done()
        reload_entry.assert_not_called()

        diagnostics = await async_get_config_entry_diagnostics(hacs.hass, entry)
        assert "new-access" not in str(diagnostics)
        assert "new-refresh" not in str(diagnostics)
        repository = hacs.repositories.get_by_full_name("hacs/integration")
        await repository.async_get_legacy_repository_object()
        for url in (
            "https://api.github.com/rate_limit",
            "https://api.github.com/repos/hacs/integration",
        ):
            request = next(call for call in reversed(response_mocker.calls) if call["url"] == url)
            assert request["args"][1]["headers"]["Authorization"] == "token new-access"


async def test_terminal_failure_starts_existing_reauth_flow(hacs, oauth_response):
    hacs.hass.config_entries.async_update_entry(
        hacs.configuration.config_entry, data=expiring_data()
    )
    oauth_response.json.return_value = {"error": "bad_refresh_token"}
    with (
        patch.object(hacs.auth.session, "post") as post,
        patch.object(hacs.configuration.config_entry, "async_start_reauth") as reauth,
    ):
        post.return_value.__aenter__.return_value = oauth_response
        api_method = AsyncMock()
        await hacs.async_github_api_method(api_method, raise_exception=False)
        await hacs.hass.async_block_till_done()
        api_method.assert_not_called()
        assert hacs.system.disabled_reason == HacsDisabledReason.INVALID_TOKEN
        reauth.assert_called_once_with(hacs.hass)
