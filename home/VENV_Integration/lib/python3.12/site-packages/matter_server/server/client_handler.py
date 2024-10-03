"""Logic to handle a client connected over WebSockets."""

from __future__ import annotations

import asyncio
from concurrent import futures
from contextlib import suppress
import logging
from typing import TYPE_CHECKING, Any, Final

from aiohttp import WSMsgType, web
import async_timeout
from chip.exceptions import ChipStackError

from matter_server.common.const import VERBOSE_LOG_LEVEL
from matter_server.common.helpers.json import json_dumps, json_loads

from ..common.errors import InvalidArguments, InvalidCommand, MatterError
from ..common.helpers.api import parse_arguments
from ..common.helpers.util import dataclass_from_dict
from ..common.models import (
    APICommand,
    CommandMessage,
    ErrorResultMessage,
    EventMessage,
    MessageType,
    SuccessResultMessage,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from matter_server.common.models import EventType

    from ..common.helpers.api import APICommandHandler
    from .server import MatterServer

MAX_PENDING_MSG = 512
CANCELLATION_ERRORS: Final = (asyncio.CancelledError, futures.CancelledError)

LOGGER = logging.getLogger(__name__)


class WebSocketLogAdapter(logging.LoggerAdapter):
    """Add connection id to websocket log messages."""

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        """Add connid to websocket log messages."""
        assert self.extra is not None
        return f"[{self.extra['connid']}] {msg}", kwargs


class WebsocketClientHandler:
    """Handle an active websocket client connection."""

    def __init__(self, server: MatterServer, request: web.Request) -> None:
        """Initialize an active connection."""
        self.server = server
        self.request = request
        self.wsock = web.WebSocketResponse(heartbeat=55)
        self._to_write: asyncio.Queue = asyncio.Queue(maxsize=MAX_PENDING_MSG)
        self._handle_task: asyncio.Task | None = None
        self._writer_task: asyncio.Task | None = None
        self._logger = WebSocketLogAdapter(LOGGER, {"connid": id(self)})
        self._unsub_callback: Callable | None = None

    async def disconnect(self) -> None:
        """Disconnect client."""
        self._cancel()
        if self._writer_task is not None:
            await self._writer_task

    async def handle_client(self) -> web.WebSocketResponse:
        """Handle a websocket response."""
        # pylint: disable=too-many-branches,too-many-statements
        request = self.request
        wsock = self.wsock
        try:
            async with async_timeout.timeout(10):
                await wsock.prepare(request)
        except asyncio.TimeoutError:
            self._logger.warning("Timeout preparing request from %s", request.remote)
            return wsock

        self._logger.debug("Connected from %s", request.remote)
        self._handle_task = asyncio.current_task()

        self._writer_task = asyncio.create_task(self._writer())

        # send server(version) info when client connects
        self._send_message(self.server.get_info())

        disconnect_warn = None

        try:
            while not wsock.closed:
                msg = await wsock.receive()

                if msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSE, WSMsgType.CLOSING):
                    break

                if msg.type == WSMsgType.ERROR:
                    disconnect_warn = f"Received error message: {msg.data}"
                    break

                if msg.type != WSMsgType.TEXT:
                    self._logger.warning("Received non-Text message: %s", msg.data)
                    continue

                self._logger.log(VERBOSE_LOG_LEVEL, "Received: %s", msg.data)

                try:
                    command_msg = dataclass_from_dict(
                        CommandMessage, json_loads(msg.data)
                    )
                except ValueError:
                    disconnect_warn = f"Received invalid JSON: {msg.data}"
                    break

                self._logger.log(VERBOSE_LOG_LEVEL, "Received %s", command_msg)
                self._handle_command(command_msg)

        except asyncio.CancelledError:
            self._logger.info("Connection closed by client")

        except Exception:  # pylint: disable=broad-except
            self._logger.exception("Unexpected error inside websocket API")

        finally:
            # Handle connection shutting down.
            if self._unsub_callback:
                self._logger.log(VERBOSE_LOG_LEVEL, "Unsubscribed from events")
                self._unsub_callback()

            try:
                self._to_write.put_nowait(None)
                # Make sure all error messages are written before closing
                await self._writer_task
                await wsock.close()
            except asyncio.QueueFull:  # can be raised by put_nowait
                self._writer_task.cancel()

            finally:
                if disconnect_warn is None:
                    self._logger.debug("Disconnected")
                else:
                    self._logger.warning("Disconnected: %s", disconnect_warn)

        return wsock

    def _handle_command(self, msg: CommandMessage) -> None:
        """Handle an incoming command from the client."""
        self._logger.log(VERBOSE_LOG_LEVEL, "Handling command %s", msg.command)

        # work out handler for the given path/command
        if msg.command == APICommand.START_LISTENING:
            self._handle_start_listening_command(msg)
            return

        handler = self.server.command_handlers.get(msg.command)

        if handler is None:
            self._send_message(
                ErrorResultMessage(
                    msg.message_id,
                    InvalidCommand.error_code,
                    f"Invalid command: {msg.command}",
                )
            )
            self._logger.warning("Invalid command: %s", msg.command)
            return

        # schedule task to handle the command
        asyncio.create_task(self._run_handler(handler, msg))

    def _handle_start_listening_command(self, msg: CommandMessage) -> None:
        """Send a full dump of all nodes once and start receiving events."""
        assert self._unsub_callback is None, "Listen command already called!"
        all_nodes = self.server.device_controller.get_nodes()
        self._send_message(SuccessResultMessage(msg.message_id, all_nodes))

        def handle_event(evt: EventType, data: Any) -> None:
            self._send_message(EventMessage(event=evt, data=data))

        self._unsub_callback = self.server.subscribe(handle_event)

    async def _run_handler(
        self, handler: APICommandHandler, msg: CommandMessage
    ) -> None:
        try:
            try:
                args = parse_arguments(handler.signature, handler.type_hints, msg.args)
            except (TypeError, KeyError, ValueError) as err:
                raise InvalidArguments from err
            result = handler.target(**args)
            if asyncio.iscoroutine(result):
                result = await result
            self._send_message(SuccessResultMessage(msg.message_id, result))
        except (ChipStackError, MatterError) as err:
            error_code = getattr(err, "error_code", MatterError.error_code)
            message_str = msg.command
            if msg.args and (node_id := msg.args.get("node_id")):
                message_str += f" (node {node_id})"
            self._logger.error(
                "Error while handling: %s: %s",
                message_str,
                str(err) or err.__class__.__name__,
                # only print the full stacktrace if verbose logging is enabled
                exc_info=err if self._logger.isEnabledFor(VERBOSE_LOG_LEVEL) else None,
            )
            self._send_message(ErrorResultMessage(msg.message_id, error_code, str(err)))
        except Exception as err:
            self._send_message(ErrorResultMessage(msg.message_id, 0, str(err)))
            raise err

    async def _writer(self) -> None:
        """Write outgoing messages."""
        # Exceptions if Socket disconnected or cancelled by connection handler
        with suppress(RuntimeError, ConnectionResetError, *CANCELLATION_ERRORS):
            while not self.wsock.closed:
                if (process := await self._to_write.get()) is None:
                    break

                if not isinstance(process, str):
                    message: str = process()
                else:
                    message = process
                await self.wsock.send_str(message)

    def _send_message(self, message: MessageType) -> None:
        """
        Send a message to the client.

        Closes connection if the client is not reading the messages.

        Async friendly.
        """
        _message = json_dumps(message)

        try:
            self._to_write.put_nowait(_message)
        except asyncio.QueueFull:
            self._logger.error(
                "Client exceeded max pending messages: %s", MAX_PENDING_MSG
            )

            self._cancel()

    def _cancel(self) -> None:
        """Cancel the connection."""
        if self._handle_task is not None:
            self._handle_task.cancel()
        if self._writer_task is not None:
            self._writer_task.cancel()
