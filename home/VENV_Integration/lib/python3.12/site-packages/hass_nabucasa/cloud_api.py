"""Cloud APIs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    ParamSpec,
    TypedDict,
    TypeVar,
    cast,
)

from aiohttp import ClientResponse
from aiohttp.hdrs import AUTHORIZATION, USER_AGENT

_LOGGER = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

if TYPE_CHECKING:
    from . import Cloud, _ClientT


class _FilesHandlerUrlResponse(TypedDict):
    """URL Response from files handler."""

    url: str


class FilesHandlerDownloadDetails(_FilesHandlerUrlResponse):
    """Download details from files handler."""


class FilesHandlerUploadDetails(_FilesHandlerUrlResponse):
    """Upload details from files handler."""

    fields: dict[str, str]


class FilesHandlerListEntry(TypedDict):
    """List entry for files handlers."""

    key: str
    size: int
    last_modified: str
    tags: dict[str, Any]


def _do_log_response(resp: ClientResponse, content: str = "") -> None:
    """Log the response."""
    meth = _LOGGER.debug if resp.status < 400 else _LOGGER.warning
    meth("Fetched %s (%s) %s", resp.url, resp.status, content)


def _check_token(
    func: Callable[Concatenate[Cloud[_ClientT], P], Awaitable[T]],
) -> Callable[Concatenate[Cloud[_ClientT], P], Coroutine[Any, Any, T]]:
    """Decorate a function to verify valid token."""

    @wraps(func)
    async def check_token(
        cloud: Cloud[_ClientT],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Validate token, then call func."""
        await cloud.auth.async_check_token()
        return await func(cloud, *args, **kwargs)

    return check_token


def _log_response(
    func: Callable[Concatenate[P], Awaitable[ClientResponse]],
) -> Callable[Concatenate[P], Coroutine[Any, Any, ClientResponse]]:
    """Decorate a function to log bad responses."""

    @wraps(func)
    async def log_response(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ClientResponse:
        """Log response if it's bad."""
        resp = await func(*args, **kwargs)
        _do_log_response(resp)
        return resp

    return log_response


@_check_token
@_log_response
async def async_create_cloudhook(cloud: Cloud[_ClientT]) -> ClientResponse:
    """Create a cloudhook."""
    return await cloud.websession.post(
        f"https://{cloud.cloudhook_server}/generate",
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
    )


@_check_token
@_log_response
async def async_remote_register(cloud: Cloud[_ClientT]) -> ClientResponse:
    """Create/Get a remote URL."""
    url = f"https://{cloud.servicehandlers_server}/instance/register"
    return await cloud.websession.post(
        url,
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
    )


@_check_token
@_log_response
async def async_remote_token(
    cloud: Cloud[_ClientT],
    aes_key: bytes,
    aes_iv: bytes,
) -> ClientResponse:
    """Create a remote snitun token."""
    url = f"https://{cloud.servicehandlers_server}/instance/snitun_token"
    return await cloud.websession.post(
        url,
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={"aes_key": aes_key.hex(), "aes_iv": aes_iv.hex()},
    )


@_check_token
@_log_response
async def async_remote_challenge_txt(
    cloud: Cloud[_ClientT],
    txt: str,
) -> ClientResponse:
    """Set DNS challenge."""
    url = f"https://{cloud.servicehandlers_server}/instance/dns_challenge_txt"
    return await cloud.websession.post(
        url,
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={"txt": txt},
    )


@_check_token
@_log_response
async def async_remote_challenge_cleanup(
    cloud: Cloud[_ClientT],
    txt: str,
) -> ClientResponse:
    """Remove DNS challenge."""
    url = f"https://{cloud.servicehandlers_server}/instance/dns_challenge_cleanup"
    return await cloud.websession.post(
        url,
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={"txt": txt},
    )


@_check_token
@_log_response
async def async_alexa_access_token(cloud: Cloud[_ClientT]) -> ClientResponse:
    """Request Alexa access token."""
    return await cloud.websession.post(
        f"https://{cloud.alexa_server}/access_token",
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
    )


@_check_token
@_log_response
async def async_voice_connection_details(cloud: Cloud[_ClientT]) -> ClientResponse:
    """Return connection details for voice service."""
    url = f"https://{cloud.servicehandlers_server}/voice/connection_details"
    return await cloud.websession.get(
        url,
        headers={AUTHORIZATION: cloud.id_token, USER_AGENT: cloud.client.client_name},
    )


@_check_token
async def async_files_download_details(
    cloud: Cloud[_ClientT],
    *,
    storage_type: str,
    filename: str,
) -> FilesHandlerDownloadDetails:
    """Get files download details."""
    resp = await cloud.websession.get(
        f"https://{cloud.servicehandlers_server}/files/download_details",
        headers={"authorization": cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={
            "storage_type": storage_type,
            "filename": filename,
        },
    )

    data: dict[str, Any] = await resp.json()
    _do_log_response(
        resp,
        data["message"] if resp.status == 400 and "message" in data else "",
    )
    resp.raise_for_status()
    return cast(FilesHandlerDownloadDetails, data)


@_check_token
async def async_files_list(
    cloud: Cloud[_ClientT],
    *,
    storage_type: str,
) -> list[FilesHandlerListEntry]:
    """List files for storage type."""
    resp = await cloud.websession.get(
        f"https://{cloud.servicehandlers_server}/files/list",
        headers={"authorization": cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={
            "storage_type": storage_type,
        },
    )

    data: dict[str, Any] | list[dict[str, Any]] = await resp.json()
    _do_log_response(
        resp,
        data["message"]
        if resp.status == 400 and isinstance(data, dict) and "message" in data
        else "",
    )
    resp.raise_for_status()
    return cast(list[FilesHandlerListEntry], data)


@_check_token
async def async_files_upload_details(
    cloud: Cloud[_ClientT],
    *,
    storage_type: str,
    filename: str,
    base64md5hash: str,
    size: int,
    homeassistant_version: str | None = None,
) -> FilesHandlerUploadDetails:
    """Get files upload details."""
    resp = await cloud.websession.get(
        f"https://{cloud.servicehandlers_server}/files/upload_details",
        headers={"authorization": cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={
            "storage_type": storage_type,
            "filename": filename,
            "homeassistant_version": homeassistant_version,
            "md5": base64md5hash,
            "size": size,
        },
    )

    data: dict[str, Any] = await resp.json()
    _do_log_response(
        resp,
        data["message"] if "message" in data and resp.status == 400 else "",
    )
    resp.raise_for_status()
    return cast(FilesHandlerUploadDetails, data)


@_check_token
@_log_response
async def async_google_actions_request_sync(cloud: Cloud[_ClientT]) -> ClientResponse:
    """Request a Google Actions sync request."""
    return await cloud.websession.post(
        f"https://{cloud.remotestate_server}/request_sync",
        headers={
            AUTHORIZATION: f"Bearer {cloud.id_token}",
            USER_AGENT: cloud.client.client_name,
        },
    )


@_check_token
async def async_subscription_info(cloud: Cloud[_ClientT]) -> dict[str, Any]:
    """Fetch subscription info."""
    resp = await cloud.websession.get(
        f"https://{cloud.accounts_server}/payments/subscription_info",
        headers={"authorization": cloud.id_token, USER_AGENT: cloud.client.client_name},
    )
    _do_log_response(resp)
    resp.raise_for_status()
    data: dict[str, Any] = await resp.json()

    # If subscription info indicates we are subscribed, force a refresh of the token
    if data.get("provider") and not cloud.started:
        _LOGGER.debug("Found disconnected account with valid subscription, connecting")
        await cloud.auth.async_renew_access_token()

    return data


@_check_token
async def async_migrate_paypal_agreement(cloud: Cloud[_ClientT]) -> dict[str, Any]:
    """Migrate a paypal agreement from legacy."""
    resp = await cloud.websession.post(
        f"https://{cloud.accounts_server}/payments/migrate_paypal_agreement",
        headers={"authorization": cloud.id_token, USER_AGENT: cloud.client.client_name},
    )
    _do_log_response(resp)
    resp.raise_for_status()
    data: dict[str, Any] = await resp.json()
    return data


@_check_token
async def async_resolve_cname(cloud: Cloud[_ClientT], hostname: str) -> list[str]:
    """Resolve DNS CNAME."""
    resp = await cloud.websession.post(
        f"https://{cloud.accounts_server}/instance/resolve_dns_cname",
        headers={"authorization": cloud.id_token, USER_AGENT: cloud.client.client_name},
        json={"hostname": hostname},
    )
    _do_log_response(resp)
    resp.raise_for_status()
    data: list[str] = await resp.json()
    return data
