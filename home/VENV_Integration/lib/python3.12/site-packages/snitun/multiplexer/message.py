"""Multiplexer message handling."""
import binascii
import os

import attr

CHANNEL_FLOW_NEW = 0x01
CHANNEL_FLOW_DATA = 0x02
CHANNEL_FLOW_CLOSE = 0x04
CHANNEL_FLOW_PING = 0x08

CHANNEL_FLOW_ALL = [
    CHANNEL_FLOW_NEW,
    CHANNEL_FLOW_CLOSE,
    CHANNEL_FLOW_DATA,
    CHANNEL_FLOW_PING,
]


@attr.s(frozen=True, slots=True, eq=True, hash=True)
class MultiplexerChannelId:
    """Represent a channel ID aka multiplexer stream."""

    bytes: bytes = attr.ib(default=attr.Factory(lambda: os.urandom(16)), eq=True)
    hex: str = attr.ib(
        default=attr.Factory(
            lambda self: binascii.hexlify(self.bytes).decode("utf-8"), takes_self=True,
        ),
        eq=False,
    )

    def __str__(self) -> str:
        """Return string representation for logger."""
        return self.hex


@attr.s(frozen=True, slots=True)
class MultiplexerMessage:
    """Represent a message from multiplexer stream."""

    id: MultiplexerChannelId = attr.ib()
    flow_type: int = attr.ib(validator=attr.validators.in_(CHANNEL_FLOW_ALL))
    data: bytes = attr.ib(default=b"")
    extra: bytes = attr.ib(default=b"")
