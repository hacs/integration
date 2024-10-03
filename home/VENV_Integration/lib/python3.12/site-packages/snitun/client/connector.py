"""Connector to end resource."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from contextlib import suppress
import ipaddress
import logging
from typing import Any

from ..exceptions import MultiplexerTransportClose, MultiplexerTransportError
from ..multiplexer.channel import MultiplexerChannel
from ..multiplexer.core import Multiplexer

_LOGGER = logging.getLogger(__name__)


class Connector:
    """Connector to end resource."""

    def __init__(
        self,
        end_host: str,
        end_port: int | None=None,
        whitelist: bool=False,
        endpoint_connection_error_callback: Coroutine[Any, Any, None] | None = None,
    ) -> None:
        """Initialize Connector."""
        self._loop = asyncio.get_event_loop()
        self._end_host = end_host
        self._end_port = end_port or 443
        self._whitelist = set()
        self._whitelist_enabled = whitelist
        self._endpoint_connection_error_callback = endpoint_connection_error_callback

    @property
    def whitelist(self) -> set:
        """Allow to block requests per IP Return None or access to a set."""
        return self._whitelist

    def _whitelist_policy(self, ip_address: ipaddress.IPv4Address) -> bool:
        """Return True if the ip address can access to endpoint."""
        if self._whitelist_enabled:
            return ip_address in self._whitelist
        return True

    async def handler(
        self, multiplexer: Multiplexer, channel: MultiplexerChannel,
    ) -> None:
        """Handle new connection from SNIProxy."""
        from_endpoint = None
        from_peer = None

        _LOGGER.debug(
            "Receive from %s a request for %s", channel.ip_address, self._end_host,
        )

        # Check policy
        if not self._whitelist_policy(channel.ip_address):
            _LOGGER.warning("Block request from %s per policy", channel.ip_address)
            await multiplexer.delete_channel(channel)
            return

        # Open connection to endpoint
        try:
            reader, writer = await asyncio.open_connection(
                host=self._end_host, port=self._end_port,
            )
        except OSError:
            _LOGGER.error(
                "Can't connect to endpoint %s:%s", self._end_host, self._end_port,
            )
            await multiplexer.delete_channel(channel)
            if self._endpoint_connection_error_callback:
                await self._endpoint_connection_error_callback()
            return

        try:
            # Process stream from multiplexer
            while not writer.transport.is_closing():
                if not from_endpoint:
                    from_endpoint = self._loop.create_task(reader.read(4096))
                if not from_peer:
                    from_peer = self._loop.create_task(channel.read())

                # Wait until data need to be processed
                await asyncio.wait(
                    [from_endpoint, from_peer], return_when=asyncio.FIRST_COMPLETED,
                )

                # From proxy
                if from_endpoint.done():
                    if from_endpoint.exception():
                        raise from_endpoint.exception()

                    await channel.write(from_endpoint.result())
                    from_endpoint = None

                # From peer
                if from_peer.done():
                    if from_peer.exception():
                        raise from_peer.exception()

                    writer.write(from_peer.result())
                    from_peer = None

                    # Flush buffer
                    await writer.drain()

        except (MultiplexerTransportError, OSError, RuntimeError):
            _LOGGER.debug("Transport closed by endpoint for %s", channel.id)
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

            # Cleanup endpoint reader
            if from_endpoint and not from_endpoint.done():
                from_endpoint.cancel()

            # Close Transport
            if not writer.transport.is_closing():
                with suppress(OSError):
                    writer.close()
