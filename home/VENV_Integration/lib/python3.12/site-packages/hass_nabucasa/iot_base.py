"""Base class to keep a websocket connection open to a server."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import dataclasses
import logging
import pprint
import random
from socket import gaierror
from typing import TYPE_CHECKING, Any

from aiohttp import (
    ClientError,
    ClientWebSocketResponse,
    WSMessage,
    WSMsgType,
    WSServerHandshakeError,
    client_exceptions,
    hdrs,
)

from .auth import CloudError
from .const import (
    MESSAGE_EXPIRATION,
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
)
from .utils import gather_callbacks

if TYPE_CHECKING:
    from . import Cloud, _ClientT


@dataclasses.dataclass
class DisconnectReason:
    """Disconnect reason."""

    clean: bool
    reason: str


class NotConnected(Exception):
    """Exception raised when trying to handle unknown handler."""


class BaseIoT:
    """Class to manage the IoT connection."""

    mark_connected_after_first_message = False

    def __init__(self, cloud: Cloud[_ClientT]) -> None:
        """Initialize the CloudIoT class."""
        self.cloud = cloud
        # The WebSocket client
        self.client: ClientWebSocketResponse | None = None
        # Scheduled sleep task till next connection retry
        self.retry_task: asyncio.Task | None = None
        # Boolean to indicate if we wanted the connection to close
        self.close_requested: bool = False
        # The current number of attempts to connect, impacts wait time
        self.tries: int = 0
        # Current state of the connection
        self.state: str = STATE_DISCONNECTED
        self._on_connect: list[Callable[[], Awaitable[None]]] = []
        self._on_disconnect: list[Callable[[], Awaitable[None]]] = []
        self._logger = logging.getLogger(self.package_name)
        self._disconnect_event: asyncio.Event | None = None
        self.last_disconnect_reason: DisconnectReason | None = None

    @property
    def package_name(self) -> str:
        """Return package name for logging."""
        raise NotImplementedError

    @property
    def ws_heartbeat(self) -> float | None:
        """Server to connect to."""
        return None

    @property
    def ws_server_url(self) -> str:
        """Server to connect to."""
        raise NotImplementedError

    @property
    def require_subscription(self) -> bool:
        """If the server requires a valid subscription."""
        return True

    def async_handle_message(self, msg: dict[str, Any]) -> None:
        """Handle incoming message.

        Run all async tasks in a wrapper to log appropriately.
        """
        raise NotImplementedError

    # --- Do not override after this line ---

    def register_on_connect(self, on_connect_cb: Callable[[], Awaitable[None]]) -> None:
        """Register an async on_connect callback."""
        self._on_connect.append(on_connect_cb)

    def register_on_disconnect(
        self,
        on_disconnect_cb: Callable[[], Awaitable[None]],
    ) -> None:
        """Register an async on_disconnect callback."""
        self._on_disconnect.append(on_disconnect_cb)

    @property
    def connected(self) -> bool:
        """Return if we're currently connected."""
        return self.state == STATE_CONNECTED

    async def async_send_json_message(self, message: dict[str, Any]) -> None:
        """Send a message.

        Raises NotConnected if client not connected.
        """
        if self.state != STATE_CONNECTED or self.client is None:
            raise NotConnected

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug("Publishing message:\n%s\n", pprint.pformat(message))

        await self.client.send_json(message)

    async def connect(self) -> None:
        """Connect to the IoT broker."""
        if self.state != STATE_DISCONNECTED:
            raise RuntimeError("Connect called while not disconnected")

        self.close_requested = False
        self.state = STATE_CONNECTING
        self.tries = 0
        self._disconnect_event = asyncio.Event()

        while True:
            try:
                self._logger.debug("Trying to connect")
                await self._handle_connection()
            except Exception:  # pylint: disable=broad-except
                # Safety net. This should never hit.
                # Still adding it here to make sure we can always reconnect
                self._logger.exception("Unexpected error")

            if self.state == STATE_CONNECTED:
                await self._disconnected()

            if self.close_requested:
                break

            if self.require_subscription and self.cloud.subscription_expired:
                break

            self.state = STATE_CONNECTING
            self.tries += 1

            try:
                await self._wait_retry()
            except asyncio.CancelledError:
                # Happens if disconnect called
                break

        self.state = STATE_DISCONNECTED
        self._disconnect_event.set()
        self._disconnect_event = None

    async def _wait_retry(self) -> None:
        """Wait until it's time till the next retry."""
        # Sleep 2^tries + 0…tries*3 seconds between retries
        self.retry_task = asyncio.create_task(
            asyncio.sleep(2 ** min(9, self.tries) + random.randint(0, self.tries * 3)),
        )
        await self.retry_task
        self.retry_task = None

    async def _handle_connection(self) -> None:
        """Connect to the IoT broker."""
        try:
            await self.cloud.auth.async_check_token()
        except CloudError as err:
            self._logger.warning(
                "Cannot connect because unable to refresh token: %s",
                err,
            )
            return

        if self.require_subscription and self.cloud.subscription_expired:
            self._logger.debug("Cloud subscription expired. Cancelling connecting.")
            self.cloud.client.user_message(
                "cloud_subscription_expired",
                "Home Assistant Cloud",
                MESSAGE_EXPIRATION,
            )
            self.close_requested = True
            return

        disconnect_clean: bool = False
        disconnect_reason: (
            str
            | WSServerHandshakeError
            | ClientError
            | ConnectionResetError
            | gaierror
            | None
        ) = None
        try:
            self.client = await self.cloud.websession.ws_connect(
                self.ws_server_url,
                heartbeat=self.ws_heartbeat,
                headers={
                    hdrs.AUTHORIZATION: f"Bearer {self.cloud.id_token}",
                    hdrs.USER_AGENT: self.cloud.client.client_name,
                },
            )

            if not self.mark_connected_after_first_message:
                await self._connected()

            while not self.client.closed:
                msg: WSMessage | None | str = None
                try:
                    msg = await self.client.receive(55)
                except TimeoutError:
                    # This is logged as info instead of warning because when
                    # this hits there is not really much that can be done about it.
                    # But the context is still valuable to have while
                    # troubleshooting.
                    self._logger.info("Timeout while waiting to receive message")
                    await self.client.ping()
                    continue

                if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
                    disconnect_clean = self.state == STATE_CONNECTED
                    disconnect_reason = f"Closed by server. {msg.extra} ({msg.data})"
                    break

                # Do this inside the loop because if 2 clients are connected,
                # it can happen that we get connected with valid auth,
                # but then server decides to drop our connection.
                if self.state != STATE_CONNECTED:
                    await self._connected()

                if msg.type == WSMsgType.ERROR:
                    disconnect_reason = "Connection error"
                    break

                if msg.type != WSMsgType.TEXT:
                    disconnect_reason = f"Received non-Text message: {msg.type}"
                    break

                try:
                    msg_content: dict[str, Any] = msg.json()
                except ValueError:
                    disconnect_reason = "Received invalid JSON."
                    break

                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.debug(
                        "Received message:\n%s\n",
                        pprint.pformat(msg_content),
                    )

                try:
                    self.async_handle_message(msg_content)
                except Exception:  # pylint: disable=broad-except
                    self._logger.exception("Unexpected error handling %s", msg_content)

            if self.client.closed:
                if self.close_requested:
                    disconnect_clean = True
                    disconnect_reason = "Close requested"
                elif disconnect_reason is None:
                    disconnect_reason = "Closed by server. Unknown reason"

        except client_exceptions.WSServerHandshakeError as err:
            if err.status == 401:
                disconnect_reason = "Invalid auth."
                self.close_requested = True
                # Should we notify user?
            else:
                disconnect_reason = err

        except (client_exceptions.ClientError, ConnectionResetError, gaierror) as err:
            disconnect_reason = err

        except asyncio.CancelledError:
            disconnect_clean = True
            disconnect_reason = "Connection Cancelled"

        finally:
            if self.client:
                base_msg = "Connection closed"
                await self.client.close()
                self.client = None
            else:
                base_msg = "Unable to connect"
            msg = f"{base_msg}: {disconnect_reason}"
            self.last_disconnect_reason = DisconnectReason(disconnect_clean, msg)

            if self.close_requested or disconnect_clean:
                self._logger.info(msg)
            else:
                self._logger.warning(msg)

    async def disconnect(self) -> None:
        """Disconnect the client."""
        self.close_requested = True

        if self.client is not None:
            await self.client.close()
        elif self.retry_task is not None:
            self.retry_task.cancel()

        if self._disconnect_event is not None:
            await self._disconnect_event.wait()

    async def _connected(self) -> None:
        """Handle connected."""
        self.last_disconnect_reason = None
        self.tries = 0
        self.state = STATE_CONNECTED
        self._logger.info("Connected")

        if self._on_connect:
            await gather_callbacks(self._logger, "on_connect", self._on_connect)

    async def _disconnected(self) -> None:
        """Handle connected."""
        if self._on_disconnect:
            await gather_callbacks(self._logger, "on_disconnect", self._on_disconnect)
