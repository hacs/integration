"""Helpers to help with account linking."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from aiohttp.client_ws import ClientWebSocketResponse

if TYPE_CHECKING:
    from . import Cloud, _ClientT

_LOGGER = logging.getLogger(__name__)

# Each function can only be called once.
ERR_ALREADY_CONSUMED = "already_consumed"

# If the specified service is not supported
ERR_UNSUPORTED = "unsupported"

# If authorizing is currently unavailable
ERR_UNAVAILABLE = "unavailable"

# If we try to get tokens without being connected.
ERR_NOT_CONNECTED = "not_connected"

# Unknown error
ERR_UNKNOWN = "unknown"

# This error will be converted to asyncio.TimeoutError
ERR_TIMEOUT = "timeout"


class AccountLinkException(Exception):
    """Base exception for when account link errors happen."""

    def __init__(self, code: str) -> None:
        """Initialize the exception."""
        super().__init__(code)
        self.code = code


def _update_token_response(tokens: dict[str, str], service: str) -> None:
    """Update token response in place."""
    tokens["service"] = service


class AuthorizeAccountHelper:
    """Class to help the user authorize a third party account with Home Assistant."""

    def __init__(self, cloud: Cloud[_ClientT], service: str) -> None:
        """Initialize the authorize account helper."""
        self.cloud = cloud
        self.service = service
        self._client: ClientWebSocketResponse | None = None

    async def async_get_authorize_url(self) -> str:
        """Generate the url where the user can authorize Home Assistant."""
        if self._client is not None:
            raise AccountLinkException(ERR_ALREADY_CONSUMED)

        _LOGGER.debug("Opening connection for %s", self.service)

        self._client = await self.cloud.client.websession.ws_connect(
            f"https://{self.cloud.account_link_server}/v1",
        )
        await self._client.send_json({"service": self.service})

        try:
            response = await self._get_response()
        except asyncio.CancelledError:
            await self._client.close()
            self._client = None
            raise

        authorize_url: str = response["authorize_url"]
        return authorize_url

    async def async_get_tokens(self) -> dict[str, str]:
        """Return the tokens when the user finishes authorizing."""
        if self._client is None:
            raise AccountLinkException(ERR_NOT_CONNECTED)

        try:
            response = await self._get_response()
        finally:
            await self._client.close()
            self._client = None

        _LOGGER.debug("Received tokens for %s", self.service)
        tokens: dict[str, str] = response["tokens"]

        _update_token_response(tokens, self.service)
        return tokens

    async def _get_response(self) -> dict[str, Any]:
        """Read a response from the connection and handle errors."""
        assert self._client is not None
        response: dict[str, Any] = await self._client.receive_json()

        if "error" in response:
            if response["error"] == ERR_TIMEOUT:
                raise TimeoutError

            raise AccountLinkException(response["error"])

        return response


async def async_fetch_access_token(
    cloud: Cloud[_ClientT],
    service: str,
    refresh_token: str,
) -> dict[str, str]:
    """Fetch access tokens using a refresh token."""
    _LOGGER.debug("Fetching tokens for %s", service)
    resp = await cloud.client.websession.post(
        f"https://{cloud.account_link_server}/refresh_token/{service}",
        json={"refresh_token": refresh_token},
    )
    resp.raise_for_status()
    tokens: dict[str, str] = await resp.json()
    _update_token_response(tokens, service)
    return tokens


async def async_fetch_available_services(
    cloud: Cloud[_ClientT],
) -> list[dict[str, Any]]:
    """Fetch available services."""
    resp = await cloud.client.websession.get(
        f"https://{cloud.account_link_server}/services",
    )
    resp.raise_for_status()
    content: list[dict[str, Any]] = await resp.json()
    return content
