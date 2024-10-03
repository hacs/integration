"""Represent a single Peer."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
import hashlib
import logging
import os

import async_timeout

from ..exceptions import MultiplexerTransportDecrypt, SniTunChallengeError
from ..multiplexer.core import Multiplexer
from ..multiplexer.crypto import CryptoTransport

_LOGGER = logging.getLogger(__name__)


class Peer:
    """Representation of a Peer."""

    def __init__(
        self,
        hostname: str,
        valid: datetime,
        aes_key: bytes,
        aes_iv: bytes,
        throttling: int | None = None,
        alias: list[str] | None = None,
    ) -> None:
        """Initialize a Peer."""
        self._hostname = hostname
        self._valid = valid
        self._throttling = throttling
        self._alias = alias or []
        self._multiplexer = None
        self._crypto = CryptoTransport(aes_key, aes_iv)

    @property
    def hostname(self) -> str:
        """Return his hostname."""
        return self._hostname

    @property
    def alias(self) -> list[str]:
        """Return the alias."""
        return self._alias

    @property
    def all_hostnames(self) -> list[str]:
        """Return a list of the base hostname and any alias."""
        return [self._hostname, *self._alias]

    @property
    def is_connected(self) -> bool:
        """Return True if we are connected to peer."""
        if not self._multiplexer:
            return False
        return self._multiplexer.is_connected

    @property
    def is_valid(self) -> bool:
        """Return True if the peer is valid."""
        return self._valid > datetime.now(tz=timezone.utc)

    @property
    def multiplexer(self) -> Multiplexer | None:
        """Return Multiplexer object."""
        return self._multiplexer

    @property
    def is_ready(self) -> bool:
        """Return true if the Peer is ready to process data."""
        if self.multiplexer is None:
            return False
        if not self.multiplexer.is_connected:
            return False
        return True

    async def init_multiplexer_challenge(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """Initialize multiplexer."""
        try:
            token = hashlib.sha256(os.urandom(40)).digest()
            writer.write(self._crypto.encrypt(token))

            async with async_timeout.timeout(60):
                await writer.drain()
                data = await reader.readexactly(32)

            # Check Token
            data = self._crypto.decrypt(data)
            assert hashlib.sha256(token).digest() == data

        except (
            asyncio.TimeoutError,
            asyncio.IncompleteReadError,
            MultiplexerTransportDecrypt,
            AssertionError,
            OSError,
        ) as err:
            raise SniTunChallengeError("Wrong challenge from peer") from err

        # Start Multiplexer
        self._multiplexer = Multiplexer(
            self._crypto, reader, writer, throttling=self._throttling,
        )

    def wait_disconnect(self) -> Coroutine:
        """Wait until peer is disconnected.

        Return a coroutine.
        """
        if not self._multiplexer:
            raise RuntimeError("No Transport initialize for peer")

        return self._multiplexer.wait()
