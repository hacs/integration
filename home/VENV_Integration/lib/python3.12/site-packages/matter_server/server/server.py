"""Implementation of a Websocket-based server to proxy Matter support (using CHIP SDK)."""

from __future__ import annotations

import asyncio
from functools import cached_property, partial
import ipaddress
import logging
import os
from pathlib import Path
import traceback
from typing import TYPE_CHECKING, Any, cast
import weakref

from aiohttp import web

from matter_server.server.helpers.custom_web_runner import MultiHostTCPSite
from matter_server.server.helpers.paa_certificates import fetch_certificates

from ..common.const import SCHEMA_VERSION
from ..common.errors import VersionMismatch
from ..common.helpers.api import APICommandHandler, api_command
from ..common.helpers.json import json_dumps
from ..common.helpers.util import chip_clusters_version, chip_core_version
from ..common.models import (
    APICommand,
    EventCallBackType,
    EventType,
    ServerDiagnostics,
    ServerInfoMessage,
)
from ..server.client_handler import WebsocketClientHandler
from .const import (
    DEFAULT_OTA_PROVIDER_DIR,
    DEFAULT_PAA_ROOT_CERTS_DIR,
    MIN_SCHEMA_VERSION,
)
from .device_controller import MatterDeviceController
from .stack import MatterStack
from .storage import StorageController
from .vendor_info import VendorInfo

if TYPE_CHECKING:
    from collections.abc import Callable

DASHBOARD_DIR = Path(__file__).parent.joinpath("../dashboard/").resolve()
DASHBOARD_DIR_EXISTS = DASHBOARD_DIR.exists()


def _global_loop_exception_handler(_: Any, context: dict[str, Any]) -> None:
    """Handle all exception inside the core loop."""
    kwargs = {}
    if exception := context.get("exception"):
        kwargs["exc_info"] = (type(exception), exception, exception.__traceback__)

    logger = logging.getLogger(__package__)
    if source_traceback := context.get("source_traceback"):
        stack_summary = "".join(traceback.format_list(source_traceback))
        logger.error(
            "Error doing job: %s: %s",
            context["message"],
            stack_summary,
            **kwargs,  # type: ignore[arg-type]
        )
        return

    logger.error(
        "Error doing task: %s",
        context["message"],
        **kwargs,  # type: ignore[arg-type]
    )


def mount_websocket(server: MatterServer, path: str) -> None:
    """Mount the websocket endpoint."""
    clients: weakref.WeakSet[WebsocketClientHandler] = weakref.WeakSet()

    async def _handle_ws(request: web.Request) -> web.WebSocketResponse:
        connection = WebsocketClientHandler(server, request)
        try:
            clients.add(connection)
            return await connection.handle_client()
        finally:
            clients.remove(connection)

    async def _handle_shutdown(app: web.Application) -> None:
        # pylint: disable=unused-argument
        for client in set(clients):
            await client.disconnect()

    server.app.on_shutdown.append(_handle_shutdown)
    server.app.router.add_route("GET", path, _handle_ws)


class MatterServer:
    """Serve Matter stack over WebSockets."""

    # pylint: disable=too-many-instance-attributes

    _runner: web.AppRunner | None = None
    _http: MultiHostTCPSite | None = None

    def __init__(  # noqa: PLR0913, pylint: disable=too-many-positional-arguments, too-many-arguments
        self,
        storage_path: str,
        vendor_id: int,
        fabric_id: int,
        port: int,
        listen_addresses: list[str] | None = None,
        primary_interface: str | None = None,
        paa_root_cert_dir: Path | None = None,
        enable_test_net_dcl: bool = False,
        bluetooth_adapter_id: int | None = None,
        ota_provider_dir: Path | None = None,
        enable_server_interactions: bool = True,
    ) -> None:
        """Initialize the Matter Server."""
        self.storage_path = storage_path
        self.vendor_id = vendor_id
        self.fabric_id = fabric_id
        self.port = port
        self.listen_addresses = listen_addresses
        self.primary_interface = primary_interface
        if paa_root_cert_dir is None:
            self.paa_root_cert_dir = DEFAULT_PAA_ROOT_CERTS_DIR
        else:
            self.paa_root_cert_dir = Path(paa_root_cert_dir).absolute()
        self.enable_test_net_dcl = enable_test_net_dcl
        self.bluetooth_enabled = bluetooth_adapter_id is not None
        if ota_provider_dir is None:
            self.ota_provider_dir = DEFAULT_OTA_PROVIDER_DIR
        else:
            self.ota_provider_dir = Path(ota_provider_dir).absolute()
        self.logger = logging.getLogger(__name__)
        self.app = web.Application()
        self.loop: asyncio.AbstractEventLoop | None = None
        # Instantiate the Matter Stack using the SDK using the given storage path
        self.stack = MatterStack(self, bluetooth_adapter_id, enable_server_interactions)
        self.storage = StorageController(self)
        self.vendor_info = VendorInfo(self)
        # we dynamically register command handlers
        self.command_handlers: dict[str, APICommandHandler] = {}
        self._device_controller: MatterDeviceController | None = None
        self._subscribers: set[EventCallBackType] = set()
        if MIN_SCHEMA_VERSION > SCHEMA_VERSION:
            raise RuntimeError(
                "Minimum supported schema version can't be higher than current schema version."
            )

    @cached_property
    def device_controller(self) -> MatterDeviceController:
        """Return the main Matter device controller."""
        assert self._device_controller
        return self._device_controller

    async def start(self) -> None:
        """Start running the Matter server."""
        self.logger.info("Starting the Matter Server...")
        # safety shield: make sure we use same clusters and core packages!
        if chip_clusters_version() != chip_core_version():
            raise VersionMismatch(
                "CHIP Core version does not match CHIP Clusters version."
            )
        self.loop = asyncio.get_running_loop()
        self.loop.set_exception_handler(_global_loop_exception_handler)
        self.loop.set_debug(os.environ.get("PYTHONDEBUG", "") != "")

        # (re)fetch all PAA certificates once at startup
        # NOTE: this must be done before initializing the controller
        await fetch_certificates(
            self.paa_root_cert_dir,
            fetch_test_certificates=self.enable_test_net_dcl,
            fetch_production_certificates=True,
        )

        # Initialize our (intermediate) device controller which keeps track
        # of Matter devices and their subscriptions.
        self._device_controller = MatterDeviceController(
            self, self.paa_root_cert_dir, self.ota_provider_dir
        )
        self._register_api_commands()

        await self._device_controller.initialize()
        await self.storage.start()
        await self.vendor_info.start()
        await self._device_controller.start()
        mount_websocket(self, "/ws")
        self.app.router.add_route("GET", "/info", self._handle_info)

        # Host dashboard if the prebuilt files are detected
        if DASHBOARD_DIR_EXISTS:
            dashboard_dir = str(DASHBOARD_DIR)
            self.logger.debug("Detected dashboard files on %s", dashboard_dir)
            for abs_dir, _, files in os.walk(dashboard_dir):
                rel_dir = abs_dir.replace(dashboard_dir, "")
                for filename in files:
                    filepath = os.path.join(abs_dir, filename)
                    handler = partial(self._serve_static, filepath)
                    if rel_dir == "" and filename == "index.html":
                        route_path = "/"
                    else:
                        route_path = f"{rel_dir}/{filename}"
                    self.app.router.add_route("GET", route_path, handler)

        self._runner = web.AppRunner(self.app, access_log=None)
        await self._runner.setup()
        self._http = MultiHostTCPSite(
            self._runner, host=self.listen_addresses, port=self.port
        )
        await self._http.start()
        self.logger.info("Matter Server successfully initialized.")

    async def stop(self) -> None:
        """Stop running the server."""
        self.logger.info("Stopping the Matter Server...")
        if self._http is None or self._runner is None:
            raise RuntimeError("Server not started.")

        self.signal_event(EventType.SERVER_SHUTDOWN)
        await self._http.stop()
        await self._runner.cleanup()
        await self.app.shutdown()
        await self.app.cleanup()
        await self.device_controller.stop()
        await self.storage.stop()
        self.stack.shutdown()
        self.logger.debug("Cleanup complete")

    def subscribe(
        self, callback: Callable[[EventType, Any], None]
    ) -> Callable[[], None]:
        """
        Subscribe to events.

        Returns handle to remove subscription.
        """

        def unsub() -> None:
            self._subscribers.remove(callback)

        self._subscribers.add(callback)
        return unsub

    @api_command(APICommand.SERVER_INFO)
    def get_info(self) -> ServerInfoMessage:
        """Return (version)info of the Matter Server."""
        assert self._device_controller
        assert self._device_controller.compressed_fabric_id is not None
        return ServerInfoMessage(
            fabric_id=self.fabric_id,
            compressed_fabric_id=self._device_controller.compressed_fabric_id,
            schema_version=SCHEMA_VERSION,
            min_supported_schema_version=MIN_SCHEMA_VERSION,
            sdk_version=chip_clusters_version(),
            wifi_credentials_set=self._device_controller.wifi_credentials_set,
            thread_credentials_set=self._device_controller.thread_credentials_set,
            bluetooth_enabled=self.bluetooth_enabled,
        )

    @api_command(APICommand.SERVER_DIAGNOSTICS)
    def get_diagnostics(self) -> ServerDiagnostics:
        """Return a full dump of the server (for diagnostics)."""
        return ServerDiagnostics(
            info=self.get_info(),
            nodes=self.device_controller.get_nodes(),
            events=list(self.device_controller.event_history),
        )

    def signal_event(self, evt: EventType, data: Any = None) -> None:
        """Signal event to listeners."""
        if TYPE_CHECKING:
            assert self.loop
        for callback in self._subscribers:
            if asyncio.iscoroutinefunction(callback):
                asyncio.create_task(callback(evt, data))
            else:
                self.loop.call_soon(callback, evt, data)

    def scope_ipv6_lla(self, ip_addr: str) -> str:
        """Scope IPv6 link-local addresses to primary interface.

        IPv6 link-local addresses received through the websocket might have no
        scope_id or a scope_id which isn't valid on this device. Just assume the
        device is connected on the primary interface.
        """
        ip_addr_parsed = ipaddress.ip_address(ip_addr)
        if not ip_addr_parsed.is_link_local or ip_addr_parsed.version != 6:
            return ip_addr

        ip_addr_parsed = cast(ipaddress.IPv6Address, ip_addr_parsed)

        if ip_addr_parsed.scope_id is not None:
            # This type of IPv6 manipulation is not supported by the ipaddress lib
            ip_addr = ip_addr.split("%")[0]

        # Rely on host OS routing table
        if self.primary_interface is None:
            return ip_addr

        self.logger.debug(
            "Setting scope of link-local IP address %s to %s",
            ip_addr,
            self.primary_interface,
        )
        return f"{ip_addr}%{self.primary_interface}"

    def register_api_command(
        self,
        command: str,
        handler: Callable,
    ) -> None:
        """Dynamically register a command on the API."""
        assert command not in self.command_handlers, "Command already registered"
        self.command_handlers[command] = APICommandHandler.parse(command, handler)

    def _register_api_commands(self) -> None:
        """Register all methods decorated as api_command."""
        for cls in (self, self._device_controller, self.vendor_info):
            for attr_name in dir(cls):
                if attr_name.startswith("_"):
                    continue
                val = getattr(cls, attr_name)
                if not hasattr(val, "api_cmd"):
                    continue
                if hasattr(val, "mock_calls"):
                    # filter out mocks
                    continue
                # method is decorated with our api decorator
                self.register_api_command(val.api_cmd, val)

    async def _handle_info(self, request: web.Request) -> web.Response:
        """Handle info endpoint to serve basic server (version) info."""
        # pylint: disable=unused-argument
        return web.json_response(self.get_info(), dumps=json_dumps)

    async def _serve_static(
        self, file_path: str, _request: web.Request
    ) -> web.FileResponse:
        """Serve file response."""
        headers = {"Cache-Control": "no-cache"}
        return web.FileResponse(file_path, headers=headers)
