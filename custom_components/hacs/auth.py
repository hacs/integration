"""Refresh GitHub device-flow credentials."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import time
from typing import Any

from aiogithubapi import (
    GitHubAuthenticationException,
    GitHubConnectionException,
    GitHubException,
)
from aiohttp import ClientError, ClientSession, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import CLIENT_ID
from .utils.logger import LOGGER

TOKEN_ENDPOINT = "https://github.com/login/oauth/access_token"
TOKEN_KEYS = frozenset({"token", "refresh_token", "expires_at", "refresh_token_expires_at"})
REFRESH_BUFFER = 300


def token_data(response: Mapping[str, Any], requested_at: float) -> dict[str, Any]:
    """Convert OAuth lifetimes to absolute expirations without retaining response extras."""
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise GitHubException("GitHub returned an invalid access token response")

    data: dict[str, Any] = {"token": token}
    refresh_token = response.get("refresh_token")
    if refresh_token is not None:
        if not isinstance(refresh_token, str) or not refresh_token:
            raise GitHubException("GitHub returned an invalid refresh token response")
        data["refresh_token"] = refresh_token

    for lifetime_key, expiry_key in (
        ("expires_in", "expires_at"),
        ("refresh_token_expires_in", "refresh_token_expires_at"),
    ):
        lifetime = response.get(lifetime_key)
        if lifetime is None and refresh_token is None:
            continue
        if type(lifetime) is not int or lifetime <= 0:
            raise GitHubException("GitHub returned an invalid token lifetime")
        data[expiry_key] = requested_at + lifetime
    return data


class GitHubTokenManager:
    """Share token rotation across HACS requests and persist renewed credentials."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, session: ClientSession) -> None:
        """Initialize the credential manager for one config entry."""
        self.hass = hass
        self.entry = entry
        self.session = session
        self._refresh_task: asyncio.Task[str] | None = None
        self._retry_at = 0.0
        self._invalid_refresh_token: str | None = None
        self._closed = False
        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._async_stop)
        )

    async def async_get_token(self) -> str:
        """Return a usable token, refreshing near expiry when supported."""
        if self._closed:
            raise GitHubConnectionException("HACS is unloading")
        if self._refresh_task is not None and self._refresh_task.done():
            self._refresh_task = None
        if self._refresh_task is not None:
            return await asyncio.shield(self._refresh_task)

        data = self.entry.data
        now = time.time()
        expires_at = data.get("expires_at")
        if expires_at is None or expires_at > now + REFRESH_BUFFER:
            return data["token"]
        refresh_token = data.get("refresh_token")
        if (
            not refresh_token
            or refresh_token == self._invalid_refresh_token
            or data.get("refresh_token_expires_at", 0) <= now
        ):
            raise GitHubAuthenticationException(
                "GitHub credentials expired; reauthentication required"
            )
        if now < self._retry_at:
            raise GitHubConnectionException("GitHub token refresh is temporarily unavailable")

        # A caller being cancelled must not interrupt saving a single-use token's replacement.
        self._refresh_task = self.hass.async_create_task(
            self._async_refresh(refresh_token), "HACS OAuth token refresh"
        )
        return await asyncio.shield(self._refresh_task)

    async def async_close(self) -> None:
        """Finish rotation before another HACS instance can start using the credential."""
        self._closed = True
        if self._refresh_task is not None and not self._refresh_task.done():
            try:
                await asyncio.shield(self._refresh_task)
            except GitHubException as exception:
                LOGGER.warning("GitHub token refresh failed while unloading HACS: %s", exception)

    async def _async_stop(self, _event: Event) -> None:
        await self.async_close()

    async def _async_refresh(self, refresh_token: str) -> str:
        requested_at = time.time()
        try:
            try:
                async with self.session.post(
                    TOKEN_ENDPOINT,
                    data={
                        "client_id": CLIENT_ID,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    headers={"Accept": "application/json"},
                    timeout=ClientTimeout(total=30),
                    allow_redirects=False,
                ) as response:
                    payload = await response.json()
                    if not isinstance(payload, dict):
                        raise GitHubException("GitHub returned an invalid refresh response")
                    if self.entry.data.get("refresh_token") != refresh_token:
                        raise GitHubException("GitHub credentials changed during token refresh")
                    if response.status < 500 and payload.get("error") in (
                        "bad_refresh_token",
                        "invalid_grant",
                    ):
                        self._invalid_refresh_token = refresh_token
                        raise GitHubAuthenticationException(
                            "GitHub rejected the refresh token; reauthentication required"
                        )
                    if response.status != 200 or payload.get("error"):
                        raise GitHubException("GitHub token refresh failed; try again later")
            except (ClientError, TimeoutError, ValueError) as exception:
                raise GitHubConnectionException(
                    "Unable to refresh GitHub credentials"
                ) from exception

            renewed = token_data(payload, requested_at)
            if "refresh_token" not in renewed:
                raise GitHubException("GitHub returned an incomplete refresh response")
            # Reauthentication or removal may have happened while the exchange was in flight.
            if (
                self.hass.config_entries.async_get_entry(self.entry.entry_id) is not self.entry
                or self.entry.data.get("refresh_token") != refresh_token
            ):
                raise GitHubException("GitHub credentials changed during token refresh")
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={
                    **{
                        key: value
                        for key, value in self.entry.data.items()
                        if key not in TOKEN_KEYS
                    },
                    **renewed,
                },
            )
            self._retry_at = 0
            return renewed["token"]
        except GitHubException:
            self._retry_at = time.time() + 30
            raise
