"""Component to integrate the Home Assistant cloud."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Generic, Literal, TypeVar

from aiohttp import ClientSession
from atomicwrites import atomic_write
import jwt

from .auth import CloudError, CognitoAuth
from .client import CloudClient
from .cloudhooks import Cloudhooks
from .const import (
    CONFIG_DIR,
    DEFAULT_SERVERS,
    DEFAULT_VALUES,
    MODE_DEV,
    STATE_CONNECTED,
)
from .google_report_state import GoogleReportState
from .iot import CloudIoT
from .remote import RemoteUI
from .utils import UTC, gather_callbacks, parse_date, utcnow
from .voice import Voice

_ClientT = TypeVar("_ClientT", bound=CloudClient)


_LOGGER = logging.getLogger(__name__)


class Cloud(Generic[_ClientT]):
    """Store the configuration of the cloud connection."""

    def __init__(
        self,
        client: _ClientT,
        mode: Literal["development", "production"],
        *,
        cognito_client_id: str | None = None,
        user_pool_id: str | None = None,
        region: str | None = None,
        account_link_server: str | None = None,
        accounts_server: str | None = None,
        acme_server: str | None = None,
        alexa_server: str | None = None,
        cloudhook_server: str | None = None,
        relayer_server: str | None = None,
        remotestate_server: str | None = None,
        thingtalk_server: str | None = None,
        servicehandlers_server: str | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Create an instance of Cloud."""
        self._on_initialized: list[Callable[[], Awaitable[None]]] = []
        self._on_start: list[Callable[[], Awaitable[None]]] = []
        self._on_stop: list[Callable[[], Awaitable[None]]] = []
        self.mode = mode
        self.client = client
        self.id_token: str | None = None
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.started: bool | None = None
        self.iot = CloudIoT(self)
        self.google_report_state = GoogleReportState(self)
        self.cloudhooks = Cloudhooks(self)
        self.remote = RemoteUI(self)
        self.auth = CognitoAuth(self)
        self.voice = Voice(self)

        self._init_task: asyncio.Task | None = None

        # Set reference
        self.client.cloud = self

        if mode == MODE_DEV:
            self.cognito_client_id = cognito_client_id
            self.user_pool_id = user_pool_id
            self.region = region

            self.account_link_server = account_link_server
            self.accounts_server = accounts_server
            self.acme_server = acme_server
            self.alexa_server = alexa_server
            self.cloudhook_server = cloudhook_server
            self.relayer_server = relayer_server
            self.remotestate_server = remotestate_server
            self.thingtalk_server = thingtalk_server
            self.servicehandlers_server = servicehandlers_server
            return

        _values = DEFAULT_VALUES[mode]

        self.cognito_client_id = _values["cognito_client_id"]
        self.user_pool_id = _values["user_pool_id"]
        self.region = _values["region"]

        _servers = DEFAULT_SERVERS[mode]

        self.account_link_server = _servers["account_link"]
        self.accounts_server = _servers["accounts"]
        self.acme_server = _servers["acme"]
        self.alexa_server = _servers["alexa"]
        self.cloudhook_server = _servers["cloudhook"]
        self.relayer_server = _servers["relayer"]
        self.remotestate_server = _servers["remotestate"]
        self.thingtalk_server = _servers["thingtalk"]
        self.servicehandlers_server = _servers["servicehandlers"]

    @property
    def is_logged_in(self) -> bool:
        """Get if cloud is logged in."""
        return self.id_token is not None

    @property
    def is_connected(self) -> bool:
        """Return True if we are connected."""
        return self.iot.state == STATE_CONNECTED

    @property
    def websession(self) -> ClientSession:
        """Return websession for connections."""
        return self.client.websession

    @property
    def subscription_expired(self) -> bool:
        """Return a boolean if the subscription has expired."""
        return utcnow() > self.expiration_date + timedelta(days=7)

    @property
    def expiration_date(self) -> datetime:
        """Return the subscription expiration as a UTC datetime object."""
        if (parsed_date := parse_date(self.claims["custom:sub-exp"])) is None:
            raise ValueError(
                f"Invalid expiration date ({self.claims['custom:sub-exp']})",
            )
        return datetime.combine(parsed_date, datetime.min.time()).replace(tzinfo=UTC)

    @property
    def username(self) -> str:
        """Return the subscription username."""
        return self.claims["cognito:username"]

    @property
    def claims(self) -> Mapping[str, str]:
        """Return the claims from the id token."""
        return self._decode_claims(str(self.id_token))

    @property
    def user_info_path(self) -> Path:
        """Get path to the stored auth."""
        return self.path(f"{self.mode}_auth.json")

    async def update_token(
        self,
        id_token: str,
        access_token: str,
        refresh_token: str | None = None,
    ) -> asyncio.Task | None:
        """Update the id and access token."""
        self.id_token = id_token
        self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token

        await self.run_executor(self._write_user_info)

        if self.started is None:
            return None

        if not self.started and not self.subscription_expired:
            self.started = True
            return asyncio.create_task(self._start())

        if self.started and self.subscription_expired:
            self.started = False
            await self.stop()

        return None

    def register_on_initialized(
        self,
        on_initialized_cb: Callable[[], Awaitable[None]],
    ) -> None:
        """Register an async on_initialized callback.

        on_initialized callbacks are called after all on_start callbacks.
        """
        self._on_initialized.append(on_initialized_cb)

    def register_on_start(self, on_start_cb: Callable[[], Awaitable[None]]) -> None:
        """Register an async on_start callback."""
        self._on_start.append(on_start_cb)

    def register_on_stop(self, on_stop_cb: Callable[[], Awaitable[None]]) -> None:
        """Register an async on_stop callback."""
        self._on_stop.append(on_stop_cb)

    def path(self, *parts: Any) -> Path:
        """Get config path inside cloud dir.

        Async friendly.
        """
        return Path(self.client.base_path, CONFIG_DIR, *parts)

    def run_executor(self, callback: Callable, *args: Any) -> asyncio.Future:
        """Run function inside executore.

        Return a awaitable object.
        """
        return self.client.loop.run_in_executor(None, callback, *args)

    async def login(self, email: str, password: str) -> None:
        """Log a user in."""
        await self.auth.async_login(email, password)

    async def logout(self) -> None:
        """Close connection and remove all credentials."""
        self.id_token = None
        self.access_token = None
        self.refresh_token = None

        self.started = False
        await self.stop()

        # Cleanup auth data
        if self.user_info_path.exists():
            await self.run_executor(self.user_info_path.unlink)

        await self.client.logout_cleanups()

    async def remove_data(self) -> None:
        """Remove all stored data."""
        if self.started:
            raise ValueError("Cloud not stopped")

        try:
            await self.remote.reset_acme()
        finally:
            await self.run_executor(self._remove_data)

    def _remove_data(self) -> None:
        """Remove all stored data."""
        base_path = self.path()

        # Recursively remove .cloud
        if base_path.is_dir():
            shutil.rmtree(base_path)

        # Guard against .cloud not being a directory
        if base_path.exists():
            base_path.unlink()

    def _write_user_info(self) -> None:
        """Write user info to a file."""
        base_path = self.path()
        if not base_path.exists():
            base_path.mkdir()

        with atomic_write(self.user_info_path, overwrite=True) as fp:
            fp.write(
                json.dumps(
                    {
                        "id_token": self.id_token,
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                    },
                    indent=4,
                ),
            )
        self.user_info_path.chmod(0o600)

    async def initialize(self) -> None:
        """Initialize the cloud component (load auth and maybe start)."""

        def load_config() -> None | dict[str, Any]:
            """Load config."""
            # Ensure config dir exists
            base_path = self.path()
            if not base_path.exists():
                base_path.mkdir()

            if not self.user_info_path.exists():
                return None

            try:
                content: dict[str, Any] = json.loads(
                    self.user_info_path.read_text(encoding="utf-8"),
                )
            except (ValueError, OSError) as err:
                path = self.user_info_path.relative_to(self.client.base_path)
                self.client.user_message(
                    "load_auth_data",
                    "Home Assistant Cloud error",
                    f"Unable to load authentication from {path}. "
                    "[Please login again](/config/cloud)",
                )
                _LOGGER.warning(
                    "Error loading cloud authentication info from %s: %s",
                    path,
                    err,
                )
                return None

            return content

        info = await self.run_executor(load_config)
        if info is None:
            # No previous token data
            self.started = False
            return

        self.id_token = info["id_token"]
        self.access_token = info["access_token"]
        self.refresh_token = info["refresh_token"]

        self._init_task = asyncio.create_task(self._finish_initialize())

    async def _finish_initialize(self) -> None:
        """Finish initializing the cloud component (load auth and maybe start)."""
        try:
            await self.auth.async_check_token()
        except CloudError:
            _LOGGER.debug("Failed to check cloud token", exc_info=True)

        if self.subscription_expired:
            self.started = False
            return

        self.started = True
        await self._start()
        await gather_callbacks(_LOGGER, "on_initialized", self._on_initialized)
        self._init_task = None

    async def _start(self) -> None:
        """Start the cloud component."""
        await self.client.cloud_started()
        await gather_callbacks(_LOGGER, "on_start", self._on_start)

    async def stop(self) -> None:
        """Stop the cloud component."""
        if self._init_task:
            self._init_task.cancel()
            self._init_task = None

        await self.client.cloud_stopped()
        await gather_callbacks(_LOGGER, "on_stop", self._on_stop)

    @staticmethod
    def _decode_claims(token: str) -> Mapping[str, Any]:
        """Decode the claims in a token."""
        decoded: Mapping[str, Any] = jwt.decode(
            token,
            options={"verify_signature": False},
        )
        return decoded
