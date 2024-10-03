"""Module to handle messages from Home Assistant cloud."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
import pprint
import random
from typing import TYPE_CHECKING, Any
import uuid

from . import iot_base
from .utils import Registry

if TYPE_CHECKING:
    from . import Cloud, _ClientT

HANDLERS = Registry()
_LOGGER = logging.getLogger(__name__)


class UnknownHandler(Exception):
    """Exception raised when trying to handle unknown handler."""


class ErrorMessage(Exception):
    """Exception raised when there was error handling message in the cloud."""

    def __init__(self, error: Any) -> None:
        """Initialize Error Message."""
        super().__init__("Error in Cloud")
        self.error = error


class HandlerError(Exception):
    """Exception raised when the handler failed."""

    def __init__(self, error: str) -> None:
        """Initialize Error Message."""
        super().__init__("Error in handler")
        self.error = error


class CloudIoT(iot_base.BaseIoT):
    """Class to manage the IoT connection."""

    mark_connected_after_first_message: bool = True

    def __init__(self, cloud: Cloud[_ClientT]) -> None:
        """Initialize the CloudIoT class."""
        super().__init__(cloud)

        # Local code waiting for a response
        self._response_handler: dict[str, asyncio.Future[Any]] = {}

        # Register start/stop
        cloud.register_on_start(self.start)
        cloud.register_on_stop(self.disconnect)

    @property
    def package_name(self) -> str:
        """Return the package name for logging."""
        return __name__

    @property
    def ws_heartbeat(self) -> float | None:
        """Server to connect to."""
        return 300

    @property
    def ws_server_url(self) -> str:
        """Server to connect to."""
        return f"wss://{self.cloud.relayer_server}/websocket"

    async def start(self) -> None:
        """Start the CloudIoT server."""
        if self.cloud.subscription_expired:
            return
        asyncio.create_task(self.connect())

    async def async_send_message(
        self,
        handler: str,
        payload: Any,
        expect_answer: bool = True,
    ) -> Any | None:
        """Send a message."""
        msgid = uuid.uuid4().hex
        fut: asyncio.Future[Any] | None = None

        if expect_answer:
            fut = self._response_handler[msgid] = asyncio.Future()

        try:
            await self.async_send_json_message(
                {"msgid": msgid, "handler": handler, "payload": payload},
            )

            if expect_answer and fut is not None:
                return await fut
            return None
        finally:
            self._response_handler.pop(msgid, None)

    def async_handle_message(self, msg: dict[str, Any]) -> None:
        """Handle a message."""
        response_handler = self._response_handler.get(msg["msgid"])

        if response_handler is not None:
            if "payload" in msg:
                response_handler.set_result(msg["payload"])
            else:
                response_handler.set_exception(ErrorMessage(msg["error"]))
            return

        asyncio.create_task(self._async_handle_handler_message(msg))

    async def _async_handle_handler_message(self, message: dict[str, Any]) -> None:
        """Handle incoming IoT message."""
        response = {"msgid": message["msgid"]}

        try:
            handler = HANDLERS.get(message["handler"])

            if handler is None:
                raise UnknownHandler

            result = await handler(self.cloud, message.get("payload"))

            # No response from handler
            if result is None:
                return

            response["payload"] = result

        except UnknownHandler:
            response["error"] = "unknown-handler"

        except HandlerError as err:
            self._logger.warning("Error handling message: %s", err.error)
            response["error"] = err.error

        except Exception:  # pylint: disable=broad-except
            self._logger.exception("Error handling message")
            response["error"] = "exception"

        # Client is unset in case the connection has been lost.
        if self.client is None:
            return

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug("Publishing message:\n%s\n", pprint.pformat(response))

        # Suppress when client is closing.
        with suppress(ConnectionResetError):
            await self.client.send_json(response)

    async def _connected(self) -> None:
        """Handle connected."""
        await super()._connected()
        await self.cloud.client.cloud_connected()

    async def _disconnected(self) -> None:
        """Handle connected."""
        await super()._disconnected()
        await self.cloud.client.cloud_disconnected()


@HANDLERS.register("system")
async def async_handle_system(cloud: Cloud[_ClientT], payload: dict[str, Any]) -> None:
    """Handle an incoming IoT message for System."""
    return await cloud.client.async_system_message(payload)


@HANDLERS.register("alexa")
async def async_handle_alexa(
    cloud: Cloud[_ClientT],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Handle an incoming IoT message for Alexa."""
    return await cloud.client.async_alexa_message(payload)


@HANDLERS.register("google_actions")
async def async_handle_google_actions(
    cloud: Cloud[_ClientT],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Handle an incoming IoT message for Google Actions."""
    return await cloud.client.async_google_message(payload)


@HANDLERS.register("cloud")
async def async_handle_cloud(cloud: Cloud[_ClientT], payload: dict[str, Any]) -> None:
    """Handle an incoming IoT message for cloud component."""
    action = payload["action"]

    if action == "logout":
        # Log out of Home Assistant Cloud
        await cloud.logout()
        _LOGGER.error(
            "You have been logged out from Home Assistant cloud: %s",
            payload["reason"],
        )
    elif action == "disconnect_remote":
        # Disconnect Remote connection
        await cloud.remote.disconnect(clear_snitun_token=True)
    elif action == "evaluate_remote_security":

        async def _reconnect() -> None:
            """Reconnect after a random timeout."""
            await asyncio.sleep(random.randint(60, 7200))
            await cloud.remote.disconnect(clear_snitun_token=True)
            await cloud.remote.connect()

        # Reconnect to remote frontends
        cloud.client.loop.create_task(_reconnect())
    elif action in ("user_notification", "critical_user_notification"):
        # Send user Notification
        cloud.client.user_message(
            "homeassistant_cloud_notification",
            payload["title"],
            payload["message"],
        )
    else:
        _LOGGER.warning("Received unknown cloud action: %s", action)


@HANDLERS.register("remote_sni")
async def async_handle_remote_sni(
    cloud: Cloud[_ClientT],
    payload: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any]:
    """Handle remote UI requests for cloud."""
    await cloud.client.async_cloud_connect_update(True)
    return {"server": cloud.remote.snitun_server}


@HANDLERS.register("connection_info")
async def async_handle_connection_info(
    cloud: Cloud[_ClientT],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Handle connection info requests for cloud."""
    return await cloud.client.async_cloud_connection_info(payload)


@HANDLERS.register("webhook")
async def async_handle_webhook(
    cloud: Cloud[_ClientT],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Handle an incoming IoT message for cloud webhooks."""
    return await cloud.client.async_webhook_message(payload)
