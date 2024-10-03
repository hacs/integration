"""Public peer interface."""
from __future__ import annotations

import asyncio
from contextlib import suppress
import logging

import async_timeout

from ..exceptions import SniTunChallengeError, SniTunInvalidPeer
from .peer_manager import PeerManager

_LOGGER = logging.getLogger(__name__)

CHECK_VALID_EXPIRE = 14400


class PeerListener:
    """Peer Listener class."""

    def __init__(
        self,
        peer_manager: PeerManager,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialize SNI Proxy interface."""
        self._peer_manager = peer_manager
        self._host = host
        self._port = port or 8080
        self._server = None

    async def start(self) -> None:
        """Start peer server."""
        self._server = await asyncio.start_server(
            self.handle_connection,
            host=self._host,
            port=self._port,
        )

    async def stop(self) -> None:
        """Stop peer server."""
        self._server.close()
        await self._server.wait_closed()

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        data: bytes | None = None,
    ) -> None:
        """Handle incoming requests."""
        if not data:
            try:
                async with async_timeout.timeout(2):
                    fernet_data = await reader.read(2048)
            except asyncio.TimeoutError:
                _LOGGER.warning("Abort peer handshake")
                writer.close()
                return
            except OSError:
                return
        else:
            fernet_data = data

        peer = None
        try:
            # Connection closed before data received
            if not fernet_data:
                return
            peer = self._peer_manager.create_peer(fernet_data)

            # Start multiplexer
            await peer.init_multiplexer_challenge(reader, writer)

            self._peer_manager.add_peer(peer)
            while peer.is_connected:
                try:
                    async with async_timeout.timeout(CHECK_VALID_EXPIRE):
                        await peer.wait_disconnect()
                except asyncio.TimeoutError:
                    if not peer.is_valid:
                        break

        except SniTunInvalidPeer:
            _LOGGER.debug("Close because invalid fernet data")

        except SniTunChallengeError:
            _LOGGER.debug("Close because challenge was wrong")

        finally:
            if peer:
                self._peer_manager.remove_peer(peer)

            # Cleanup transport
            if not writer.transport.is_closing():
                with suppress(OSError):
                    writer.close()
