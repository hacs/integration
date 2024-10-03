# -*- coding: utf-8 -*-
"""async_upnp_client.search module."""

import asyncio
import logging
import socket
import sys
from asyncio import DatagramTransport
from asyncio.events import AbstractEventLoop
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Callable, Coroutine, Optional, cast

from async_upnp_client.const import SsdpSource
from async_upnp_client.ssdp import (
    SSDP_DISCOVER,
    SSDP_MX,
    SSDP_ST_ALL,
    AddressTupleVXType,
    IPvXAddress,
    SsdpProtocol,
    build_ssdp_search_packet,
    determine_source_target,
    get_host_string,
    get_ssdp_socket,
)
from async_upnp_client.utils import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)


class SsdpSearchListener:  # pylint: disable=too-many-arguments,too-many-instance-attributes
    """SSDP Search (response) listener."""

    def __init__(
        self,
        async_callback: Optional[
            Callable[[CaseInsensitiveDict], Coroutine[Any, Any, None]]
        ] = None,
        callback: Optional[Callable[[CaseInsensitiveDict], None]] = None,
        loop: Optional[AbstractEventLoop] = None,
        source: Optional[AddressTupleVXType] = None,
        target: Optional[AddressTupleVXType] = None,
        timeout: int = SSDP_MX,
        search_target: str = SSDP_ST_ALL,
        async_connect_callback: Optional[
            Callable[[], Coroutine[Any, Any, None]]
        ] = None,
        connect_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Init the ssdp listener class."""
        assert (
            callback is not None or async_callback is not None
        ), "Provide at least one callback"

        self.async_callback = async_callback
        self.callback = callback
        self.async_connect_callback = async_connect_callback
        self.connect_callback = connect_callback
        self.search_target = search_target
        self.source, self.target = determine_source_target(source, target)
        self.timeout = timeout
        self.loop = loop or asyncio.get_event_loop()
        self._target_host: Optional[str] = None
        self._transport: Optional[DatagramTransport] = None

    def async_search(
        self, override_target: Optional[AddressTupleVXType] = None
    ) -> None:
        """Start an SSDP search."""
        assert self._transport is not None
        sock: Optional[socket.socket] = self._transport.get_extra_info("socket")
        _LOGGER.debug(
            "Sending SEARCH packet, transport: %s, socket: %s, override_target: %s",
            self._transport,
            sock,
            override_target,
        )

        assert self._target_host is not None, "Call async_start() first"
        packet = build_ssdp_search_packet(self.target, self.timeout, self.search_target)

        protocol = cast(SsdpProtocol, self._transport.get_protocol())
        target = override_target or self.target
        protocol.send_ssdp_packet(packet, target)

    def _on_data(self, request_line: str, headers: CaseInsensitiveDict) -> None:
        """Handle data."""
        if headers.get_lower("man") == SSDP_DISCOVER:
            # Ignore discover packets.
            return
        if headers.get_lower("nts"):
            _LOGGER.debug(
                "Got non-search response packet: %s, %s", request_line, headers
            )
            return

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Received search response, _remote_addr: %s, USN: %s, location: %s",
                headers.get_lower("_remote_addr", ""),
                headers.get_lower("usn", "<no USN>"),
                headers.get_lower("location", ""),
            )
        headers["_source"] = SsdpSource.SEARCH
        if self._target_host and self._target_host != headers["_host"]:
            return
        if self.async_callback:
            coro = self.async_callback(headers)
            self.loop.create_task(coro)
        if self.callback:
            self.callback(headers)

    def _on_connect(self, transport: DatagramTransport) -> None:
        sock: Optional[socket.socket] = transport.get_extra_info("socket")
        _LOGGER.debug("On connect, transport: %s, socket: %s", transport, sock)
        self._transport = transport
        if self.async_connect_callback:
            coro = self.async_connect_callback()
            self.loop.create_task(coro)
        if self.connect_callback:
            self.connect_callback()

    @property
    def target_ip(self) -> IPvXAddress:
        """Get target IP."""
        if len(self.target) == 4:
            return IPv6Address(self.target[0])

        return IPv4Address(self.target[0])

    async def async_start(self) -> None:
        """Start the listener."""
        _LOGGER.debug("Start listening for search responses")

        sock, _source, _target = get_ssdp_socket(self.source, self.target)
        if sys.platform.startswith("win32"):
            address = self.source
            _LOGGER.debug("Binding socket, socket: %s, address: %s", sock, address)
            sock.bind(address)

        if not self.target_ip.is_multicast:
            self._target_host = get_host_string(self.target)
        else:
            self._target_host = ""

        loop = self.loop
        await loop.create_datagram_endpoint(
            lambda: SsdpProtocol(
                loop,
                on_connect=self._on_connect,
                on_data=self._on_data,
            ),
            sock=sock,
        )

    def async_stop(self) -> None:
        """Stop the listener."""
        if self._transport:
            self._transport.close()


async def async_search(
    async_callback: Callable[[CaseInsensitiveDict], Coroutine[Any, Any, None]],
    timeout: int = SSDP_MX,
    search_target: str = SSDP_ST_ALL,
    source: Optional[AddressTupleVXType] = None,
    target: Optional[AddressTupleVXType] = None,
    loop: Optional[AbstractEventLoop] = None,
) -> None:
    """Discover devices via SSDP."""
    # pylint: disable=too-many-arguments
    loop_: AbstractEventLoop = loop or asyncio.get_event_loop()
    listener: Optional[SsdpSearchListener] = None

    async def _async_connected() -> None:
        nonlocal listener
        assert listener is not None
        listener.async_search()

    listener = SsdpSearchListener(
        async_callback=async_callback,
        loop=loop_,
        source=source,
        target=target,
        timeout=timeout,
        search_target=search_target,
        async_connect_callback=_async_connected,
    )

    await listener.async_start()

    # Wait for devices to respond.
    await asyncio.sleep(timeout)

    listener.async_stop()
