"""Multiplexer channel."""
from __future__ import annotations

import asyncio
from contextlib import suppress
from ipaddress import IPv4Address
import logging

import async_timeout

from ..exceptions import MultiplexerTransportClose, MultiplexerTransportError
from ..utils.ipaddress import ip_address_to_bytes
from .message import (
    CHANNEL_FLOW_CLOSE,
    CHANNEL_FLOW_DATA,
    CHANNEL_FLOW_NEW,
    MultiplexerChannelId,
    MultiplexerMessage,
)

_LOGGER = logging.getLogger(__name__)


class MultiplexerChannel:
    """Represent a multiplexer channel."""

    __slots__ = ["_input", "_output", "_id", "_ip_address", "_throttling", "_closing"]

    def __init__(
        self,
        output: asyncio.Queue,
        ip_address: IPv4Address,
        channel_id: MultiplexerChannelId | None = None,
        throttling: float | None = None,
    ) -> None:
        """Initialize Multiplexer Channel."""
        self._input = asyncio.Queue(8000)
        self._output = output
        self._id = channel_id or MultiplexerChannelId()
        self._ip_address = ip_address
        self._throttling = throttling
        self._closing = False

    @property
    def id(self) -> MultiplexerChannelId:
        """Return ID of this channel."""
        return self._id

    @property
    def ip_address(self) -> IPv4Address:
        """Return caller IP4Address."""
        return self._ip_address

    @property
    def healthy(self) -> bool:
        """Return True if a error is occurse."""
        return self._input.full()

    @property
    def closing(self) -> bool:
        """Return True if channel is in closing state."""
        return self._closing

    def close(self) -> None:
        """Close channel on next run."""
        self._closing = True
        with suppress(asyncio.QueueFull):
            self._input.put_nowait(None)

    async def write(self, data: bytes) -> None:
        """Send data to peer."""
        if not data:
            raise MultiplexerTransportError
        if self._closing:
            raise MultiplexerTransportClose

        # Create message
        message = MultiplexerMessage(self._id, CHANNEL_FLOW_DATA, data)

        try:
            async with async_timeout.timeout(5):
                await self._output.put(message)
        except asyncio.TimeoutError:
            _LOGGER.debug("Can't write to peer transport")
            raise MultiplexerTransportError from None

        if not self._throttling:
            return
        await asyncio.sleep(self._throttling)

    async def read(self) -> MultiplexerMessage:
        """Read data from peer."""
        if self._closing and self._input.empty():
            message = None
        else:
            message = await self._input.get()

        # Send data
        if message is not None:
            return message.data

        _LOGGER.debug("Read a close message for channel %s", self._id)
        raise MultiplexerTransportClose

    def init_close(self) -> MultiplexerMessage:
        """Init close message for transport."""
        _LOGGER.debug("Close channel %s", self._id)
        return MultiplexerMessage(self._id, CHANNEL_FLOW_CLOSE)

    def init_new(self) -> MultiplexerMessage:
        """Init new session for transport."""
        _LOGGER.debug("New channel %s", self._id)
        extra = b"4" + ip_address_to_bytes(self.ip_address)
        return MultiplexerMessage(self._id, CHANNEL_FLOW_NEW, b"", extra)

    def message_transport(self, message: MultiplexerMessage) -> None:
        """Only for internal ussage of core transport."""
        if self._closing:
            return

        try:
            self._input.put_nowait(message)
        except asyncio.QueueFull:
            _LOGGER.warning("Channel %s input is full", self._id)
