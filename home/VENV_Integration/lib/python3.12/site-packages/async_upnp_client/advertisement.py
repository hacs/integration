# -*- coding: utf-8 -*-
"""async_upnp_client.advertisement module."""

import asyncio
import logging
import socket
from asyncio.events import AbstractEventLoop
from asyncio.transports import BaseTransport, DatagramTransport
from typing import Any, Callable, Coroutine, Optional

from async_upnp_client.const import AddressTupleVXType, NotificationSubType, SsdpSource
from async_upnp_client.ssdp import (
    SSDP_DISCOVER,
    SsdpProtocol,
    determine_source_target,
    get_ssdp_socket,
)
from async_upnp_client.utils import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)


class SsdpAdvertisementListener:
    """SSDP Advertisement listener."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        async_on_alive: Optional[
            Callable[[CaseInsensitiveDict], Coroutine[Any, Any, None]]
        ] = None,
        async_on_byebye: Optional[
            Callable[[CaseInsensitiveDict], Coroutine[Any, Any, None]]
        ] = None,
        async_on_update: Optional[
            Callable[[CaseInsensitiveDict], Coroutine[Any, Any, None]]
        ] = None,
        on_alive: Optional[Callable[[CaseInsensitiveDict], None]] = None,
        on_byebye: Optional[Callable[[CaseInsensitiveDict], None]] = None,
        on_update: Optional[Callable[[CaseInsensitiveDict], None]] = None,
        source: Optional[AddressTupleVXType] = None,
        target: Optional[AddressTupleVXType] = None,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        assert (
            async_on_alive
            or async_on_byebye
            or async_on_update
            or on_alive
            or on_byebye
            or on_update
        ), "Provide at least one callback"

        self.async_on_alive = async_on_alive
        self.async_on_byebye = async_on_byebye
        self.async_on_update = async_on_update
        self.on_alive = on_alive
        self.on_byebye = on_byebye
        self.on_update = on_update
        self.source, self.target = determine_source_target(source, target)
        self.loop: AbstractEventLoop = loop or asyncio.get_event_loop()
        self._transport: Optional[BaseTransport] = None

    def _on_data(self, request_line: str, headers: CaseInsensitiveDict) -> None:
        """Handle data."""
        if headers.get_lower("man") == SSDP_DISCOVER:
            # Ignore discover packets.
            return

        notification_sub_type = headers.get_lower("nts")
        if notification_sub_type is None:
            _LOGGER.debug("Got non-advertisement packet: %s, %s", request_line, headers)
            return

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Received advertisement, _remote_addr: %s, NT: %s, NTS: %s, USN: %s, location: %s",
                headers.get_lower("_remote_addr", ""),
                headers.get_lower("nt", "<no NT>"),
                headers.get_lower("nts", "<no NTS>"),
                headers.get_lower("usn", "<no USN>"),
                headers.get_lower("location", ""),
            )

        headers["_source"] = SsdpSource.ADVERTISEMENT
        if notification_sub_type == NotificationSubType.SSDP_ALIVE:
            if self.async_on_alive:
                coro = self.async_on_alive(headers)
                self.loop.create_task(coro)
            if self.on_alive:
                self.on_alive(headers)
        elif notification_sub_type == NotificationSubType.SSDP_BYEBYE:
            if self.async_on_byebye:
                coro = self.async_on_byebye(headers)
                self.loop.create_task(coro)
            if self.on_byebye:
                self.on_byebye(headers)
        elif notification_sub_type == NotificationSubType.SSDP_UPDATE:
            if self.async_on_update:
                coro = self.async_on_update(headers)
                self.loop.create_task(coro)
            if self.on_update:
                self.on_update(headers)

    def _on_connect(self, transport: DatagramTransport) -> None:
        sock: Optional[socket.socket] = transport.get_extra_info("socket")
        _LOGGER.debug("On connect, transport: %s, socket: %s", transport, sock)
        self._transport = transport

    async def async_start(self) -> None:
        """Start listening for advertisements."""
        _LOGGER.debug("Start listening for advertisements")

        # Construct a socket for use with this pairs of endpoints.
        sock, _source, _target = get_ssdp_socket(self.source, self.target)

        # Bind to address.
        address = ("", self.target[1])
        _LOGGER.debug("Binding socket, socket: %s, address: %s", sock, address)
        sock.bind(address)

        # Create protocol and send discovery packet.
        await self.loop.create_datagram_endpoint(
            lambda: SsdpProtocol(
                self.loop,
                on_connect=self._on_connect,
                on_data=self._on_data,
            ),
            sock=sock,
        )

    async def async_stop(self) -> None:
        """Stop listening for advertisements."""
        _LOGGER.debug("Stop listening for advertisements")
        if self._transport:
            self._transport.close()
