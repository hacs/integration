"""Public proxy interface with SNI."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import ipaddress
import logging

import async_timeout

from ..exceptions import (
    MultiplexerTransportClose,
    MultiplexerTransportError,
    ParseSNIError,
)
from ..multiplexer.core import Multiplexer
from .peer_manager import PeerManager
from .sni import parse_tls_sni, payload_reader

_LOGGER = logging.getLogger(__name__)

TCP_SESSION_TIMEOUT = 60


class SNIProxy:
    """SNI Proxy class."""

    def __init__(
        self,
        peer_manager: PeerManager,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialize SNI Proxy interface."""
        self._peer_manager = peer_manager
        self._loop = asyncio.get_event_loop()
        self._host = host
        self._port = port or 443
        self._server = None

    async def start(self) -> None:
        """Start Proxy server."""
        self._server = await asyncio.start_server(
            self.handle_connection,
            host=self._host,
            port=self._port,
        )

    async def stop(self) -> None:
        """Stop proxy server."""
        self._server.close()
        await self._server.wait_closed()

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        data: bytes | None = None,
        sni: str | None = None,
    ) -> None:
        """Handle incoming requests."""
        if data is None:
            try:
                async with async_timeout.timeout(2):
                    client_hello = await payload_reader(reader)
            except asyncio.TimeoutError:
                _LOGGER.warning("Abort SNI handshake")
                writer.close()
                return
            except OSError:
                return
        else:
            client_hello = data

        # Connection closed before data received
        if not client_hello:
            with suppress(OSError):
                writer.close()
            return

        try:
            # Read Hostname
            if sni is None:
                try:
                    hostname = parse_tls_sni(client_hello)
                except ParseSNIError:
                    _LOGGER.warning("Receive invalid ClientHello on public Interface")
                    return
            else:
                hostname = sni

            # Peer available?
            if not self._peer_manager.peer_available(hostname):
                _LOGGER.debug("Hostname %s not connected", hostname)
                return
            peer = self._peer_manager.get_peer(hostname)

            # Proxy data over mutliplexer to client
            _LOGGER.debug("Processing for hostname %s started", hostname)
            await self._proxy_peer(peer.multiplexer, client_hello, reader, writer)

        finally:
            if not writer.transport.is_closing():
                with suppress(OSError):
                    writer.close()

    async def _proxy_peer(
        self,
        multiplexer: Multiplexer,
        client_hello: bytes,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Proxy data between end points."""
        transport = writer.transport
        try:
            ip_address = ipaddress.ip_address(writer.get_extra_info("peername")[0])
        except (TypeError, AttributeError):
            _LOGGER.error("Can't read source IP")
            return

        # Open multiplexer channel
        try:
            channel = await multiplexer.create_channel(ip_address)
        except MultiplexerTransportError:
            _LOGGER.error("New transport channel to peer fails")
            return

        from_proxy = None
        from_peer = None
        try:
            await channel.write(client_hello)

            # Process stream into multiplexer
            while not transport.is_closing():
                if not from_proxy:
                    from_proxy = self._loop.create_task(reader.read(4096))
                if not from_peer:
                    from_peer = self._loop.create_task(channel.read())

                # Wait until data need to be processed
                async with async_timeout.timeout(TCP_SESSION_TIMEOUT):
                    await asyncio.wait(
                        [from_proxy, from_peer],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                # From proxy
                if from_proxy.done():
                    if from_proxy.exception():
                        raise from_proxy.exception()

                    await channel.write(from_proxy.result())
                    from_proxy = None

                # From peer
                if from_peer.done():
                    if from_peer.exception():
                        raise from_peer.exception()

                    writer.write(from_peer.result())
                    from_peer = None

                    # Flush buffer
                    await writer.drain()

        except (asyncio.TimeoutError, TimeoutError):
            _LOGGER.debug("Close TCP session after timeout for %s", channel.id)
            with suppress(MultiplexerTransportError):
                await multiplexer.delete_channel(channel)

        except (MultiplexerTransportError, OSError, RuntimeError, ConnectionResetError):
            _LOGGER.debug("Transport closed by Proxy for %s", channel.id)
            with suppress(MultiplexerTransportError):
                await multiplexer.delete_channel(channel)

        except MultiplexerTransportClose:
            _LOGGER.debug("Peer close connection for %s", channel.id)

        finally:
            # Cleanup peer reader
            if from_peer:
                if not from_peer.done():
                    from_peer.cancel()
                else:
                    # Avoid exception was never retrieved
                    from_peer.exception()

            # Cleanup proxy reader
            if from_proxy and not from_proxy.done():
                from_proxy.cancel()
