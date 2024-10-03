"""Manage peer connections."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
import json
import logging

import async_timeout
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from ..exceptions import SniTunInvalidPeer
from .peer import Peer

_LOGGER = logging.getLogger(__name__)


class PeerManagerEvent(str, Enum):
    """Peer Manager event flags."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class PeerManager:
    """Manage Peer connections."""

    def __init__(
        self,
        fernet_tokens: list[str],
        throttling: int | None = None,
        event_callback: Callable[[Peer, PeerManagerEvent], None] | None = None,
    ) -> None:
        """Initialize Peer Manager."""
        self._fernet = MultiFernet([Fernet(key) for key in fernet_tokens])
        self._loop = asyncio.get_event_loop()
        self._throttling = throttling
        self._event_callback = event_callback
        self._peers: dict[str, Peer] = {}

    @property
    def connections(self) -> int:
        """Return count of connected devices."""
        return len(self._peers)

    def create_peer(self, fernet_data: bytes) -> Peer:
        """Create a new peer from crypt config."""
        try:
            data = self._fernet.decrypt(fernet_data).decode("utf-8")
            config = json.loads(data)
        except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError) as err:
            raise SniTunInvalidPeer("Invalid fernet token") from err

        # Check if token is valid
        valid = datetime.fromtimestamp(config["valid"], tz=timezone.utc)
        if valid < datetime.now(tz=timezone.utc):
            raise SniTunInvalidPeer("Token was expired")

        # Extract configuration
        hostname = config["hostname"]
        aes_key = bytes.fromhex(config["aes_key"])
        aes_iv = bytes.fromhex(config["aes_iv"])

        return Peer(
            hostname,
            valid,
            aes_key,
            aes_iv,
            throttling=self._throttling,
            alias=config.get("alias", []),
        )

    def add_peer(self, peer: Peer) -> None:
        """Register peer to internal hostname list."""
        if self.peer_available(peer.hostname):
            _LOGGER.warning("Found stale peer connection")
            self._peers[peer.hostname].multiplexer.shutdown()

        _LOGGER.debug("New peer connection: %s", peer.hostname)
        self._peers[peer.hostname] = peer
        for alias in peer.alias:
            _LOGGER.debug("New peer connection alias: %s for %s", alias, peer.hostname)
            self._peers[alias] = peer

        if self._event_callback:
            self._loop.call_soon(self._event_callback, peer, PeerManagerEvent.CONNECTED)

    def remove_peer(self, peer: Peer) -> None:
        """Remove peer from list."""
        if self._peers.get(peer.hostname) != peer:
            return
        _LOGGER.debug("Close peer connection: %s", peer.hostname)
        for hostname in peer.all_hostnames:
            self._peers.pop(hostname, None)

        if self._event_callback:
            self._loop.call_soon(
                self._event_callback,
                peer,
                PeerManagerEvent.DISCONNECTED,
            )

    def peer_available(self, hostname: str) -> bool:
        """Check if peer available and return True or False."""
        if hostname in self._peers:
            return self._peers[hostname].is_ready
        return False

    def get_peer(self, hostname: str) -> Peer | None:
        """Get peer."""
        return self._peers.get(hostname)

    async def close_connections(self, timeout: int = 10) -> None:
        """Close all peer connections.

        Use this function only if you do not controll the server socket.
        """
        peers = list(self._peers.values())
        for peer in peers:
            if peer.is_connected:
                peer.multiplexer.shutdown()

        if waiters := [peer.wait_disconnect() for peer in peers]:
            try:
                async with async_timeout.timeout(timeout):
                    await asyncio.gather(*waiters, return_exceptions=True)
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout while waiting for peer disconnect")
