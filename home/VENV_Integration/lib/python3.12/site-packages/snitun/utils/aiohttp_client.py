"""Helper for handle aiohttp internal server."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from contextlib import suppress
import logging
import socket
import ssl
from typing import Any

from aiohttp.web import AppRunner, SockSite
import async_timeout

from ..client.client_peer import ClientPeer
from ..client.connector import Connector

_LOGGER = logging.getLogger(__name__)


class SniTunClientAioHttp:
    """Help to handle a internal aiohttp app runner."""

    def __init__(
        self,
        runner: AppRunner,
        context: ssl.SSLContext,
        snitun_server: str,
        snitun_port: int | None=None,
    )->None:
        """Initialize SniTunClient with aiohttp."""
        self._connector = None
        self._client = ClientPeer(snitun_server, snitun_port)
        self._socket = socket.socket()
        self._server_name = f"{snitun_server}:{snitun_port}"

        # Init interface
        self._socket.setblocking(False)
        self._socket.bind(("127.0.0.1", 0))
        self._site = SockSite(runner, self._socket, ssl_context=context)

    @property
    def is_connected(self) -> bool:
        """Return True if we are connected to snitun."""
        return self._client.is_connected

    @property
    def whitelist(self) -> set:
        """Return whitelist from connector."""
        if self._connector:
            return self._connector.whitelist
        return set()

    def wait(self) -> asyncio.Task:
        """Block until connection to snitun is closed."""
        return self._client.wait()

    async def start(
        self,
        whitelist: bool = False,
        endpoint_connection_error_callback: Coroutine[Any, Any, None] | None = None,
    ) -> None:
        """Start internal server."""
        await self._site.start()

        host, port = self._socket.getsockname()[:2]
        self._connector = Connector(
            host,
            port,
            whitelist,
            endpoint_connection_error_callback=endpoint_connection_error_callback,
        )

        _LOGGER.info("AioHTTP snitun client started on %s:%s", host, port)

    async def stop(self, *, wait: bool = False) -> None:
        """
        Stop internal server.

        Args:
            wait: wait for the socket to close.
        """
        await self.disconnect()
        with suppress(OSError):
            self._socket.close()

        with suppress(RuntimeError):
            self._site._runner._unreg_site(self._site)  # noqa: SLF001

        if wait:
            # Wait for the socket to close
            await _async_waitfor_socket_closed(self._socket)

        _LOGGER.info("AioHTTP snitun client closed")

    async def connect(
        self,
        fernet_key: bytes,
        aes_key: bytes,
        aes_iv: bytes,
        throttling: int | None = None,
    ) -> None:
        """Connect to SniTun server."""
        if self._client.is_connected:
            return
        await self._client.start(
            self._connector, fernet_key, aes_key, aes_iv, throttling=throttling,
        )
        _LOGGER.info("AioHTTP snitun client connected to: %s", self._server_name)

    async def disconnect(self) -> None:
        """Disconnect from SniTun server."""
        if not self._client.is_connected:
            return
        await self._client.stop()
        _LOGGER.info("AioHTTP snitun client disconnected from: %s", self._server_name)


async def _async_waitfor_socket_closed(sock: socket.socket | None = None) -> None:
    """Wait for the socket to be closed."""
    if sock is None:
        return
    loop = asyncio.get_event_loop()
    try:
        async with async_timeout.timeout(60):
            while (await loop.run_in_executor(None, sock.fileno)) != -1:
                await asyncio.sleep(1)
    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout while waiting for the socket to close.")
