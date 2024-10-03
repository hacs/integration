"""Logic to manage the WebSocket connection to the Matter server."""

from __future__ import annotations

import logging
import os
import pprint
from typing import Final, cast

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType, client_exceptions

from matter_server.common.helpers.util import dataclass_from_dict

from ..common.const import SCHEMA_VERSION
from ..common.helpers.json import json_dumps, json_loads
from ..common.models import (
    CommandMessage,
    ErrorResultMessage,
    EventMessage,
    MessageType,
    ServerInfoMessage,
    SuccessResultMessage,
)
from .exceptions import (
    CannotConnect,
    ConnectionClosed,
    ConnectionFailed,
    InvalidMessage,
    InvalidState,
    NotConnected,
    ServerVersionTooNew,
    ServerVersionTooOld,
)

LOGGER = logging.getLogger(f"{__package__}.connection")
VERBOSE_LOGGER = os.environ.get("MATTER_VERBOSE_LOGGING")
SUB_WILDCARD: Final = "*"


class MatterClientConnection:
    """Manage a Matter server over WebSockets."""

    def __init__(
        self,
        ws_server_url: str,
        aiohttp_session: ClientSession,
    ):
        """Initialize the Client class."""
        self.ws_server_url = ws_server_url
        # server info is retrieved on connect
        self.server_info: ServerInfoMessage | None = None
        self._aiohttp_session = aiohttp_session
        self._ws_client: ClientWebSocketResponse | None = None

    @property
    def connected(self) -> bool:
        """Return if we're currently connected."""
        return self._ws_client is not None and not self._ws_client.closed

    async def connect(self) -> None:
        """Connect to the websocket server."""
        if self._ws_client is not None:
            raise InvalidState("Already connected")

        LOGGER.debug("Trying to connect")
        try:
            self._ws_client = await self._aiohttp_session.ws_connect(
                self.ws_server_url,
                heartbeat=55,
                compress=15,
                max_msg_size=0,
            )
        except (
            client_exceptions.WSServerHandshakeError,
            client_exceptions.ClientError,
        ) as err:
            raise CannotConnect(err) from err

        # at connect, the server sends a single message with the server info
        info = cast(ServerInfoMessage, await self.receive_message_or_raise())
        self.server_info = info

        if info.schema_version < SCHEMA_VERSION:
            # The client schema is too new, the server can't handle it yet
            await self._ws_client.close()
            raise ServerVersionTooOld(
                f"Matter schema version is incompatible: {SCHEMA_VERSION}, "
                f"the server supports at most {info.schema_version} "
                "- update the Matter server to a more recent version or downgrade the client."
            )

        if info.min_supported_schema_version > SCHEMA_VERSION:
            # The client schema version is too low and can't be handled by the server anymore
            await self._ws_client.close()
            raise ServerVersionTooNew(
                f"Matter schema version is incompatible: {SCHEMA_VERSION}, "
                f"the server requires at least {info.min_supported_schema_version} "
                "- update the Matter client to a more recent version or downgrade the server."
            )

        LOGGER.info(
            "Connected to Matter Fabric %s (%s), Schema version %s, CHIP SDK Version %s",
            info.fabric_id,
            info.compressed_fabric_id,
            info.schema_version,
            info.sdk_version,
        )

    async def disconnect(self) -> None:
        """Disconnect the client."""
        LOGGER.debug("Closing client connection")
        if self._ws_client is not None and not self._ws_client.closed:
            await self._ws_client.close()
        self._ws_client = None

    async def receive_message_or_raise(self) -> MessageType:
        """Receive (raw) message or raise."""
        assert self._ws_client
        ws_msg = await self._ws_client.receive()

        if ws_msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
            raise ConnectionClosed("Connection was closed.")

        if ws_msg.type == WSMsgType.ERROR:
            raise ConnectionFailed

        if ws_msg.type != WSMsgType.TEXT:
            raise InvalidMessage(
                f"Received non-Text message: {ws_msg.type}: {ws_msg.data}"
            )

        try:
            msg = parse_message(json_loads(ws_msg.data))
        except TypeError as err:
            raise InvalidMessage(f"Received unsupported JSON: {err}") from err
        except ValueError as err:
            raise InvalidMessage("Received invalid JSON.") from err

        if VERBOSE_LOGGER and LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Received message:\n%s\n", pprint.pformat(ws_msg))

        return msg

    async def send_message(self, message: CommandMessage) -> None:
        """
        Send a CommandMessage to the server.

        Raises NotConnected if client not connected.
        """
        if not self.connected:
            raise NotConnected

        if VERBOSE_LOGGER and LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Publishing message:\n%s\n", pprint.pformat(message))

        assert self._ws_client
        assert isinstance(message, CommandMessage)

        await self._ws_client.send_json(message, dumps=json_dumps)

    def __repr__(self) -> str:
        """Return the representation."""
        prefix = "" if self.connected else "not "
        return f"{type(self).__name__}(ws_server_url={self.ws_server_url!r}, {prefix}connected)"


def parse_message(raw: dict) -> MessageType:
    """Parse Message from raw dict object."""
    if "event" in raw:
        return dataclass_from_dict(EventMessage, raw)
    if "error_code" in raw:
        return dataclass_from_dict(ErrorResultMessage, raw)
    if "result" in raw:
        return dataclass_from_dict(SuccessResultMessage, raw)
    if "sdk_version" in raw:
        return dataclass_from_dict(ServerInfoMessage, raw)
    return dataclass_from_dict(CommandMessage, raw)
