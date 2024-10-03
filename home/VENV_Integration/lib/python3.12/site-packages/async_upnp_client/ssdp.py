# -*- coding: utf-8 -*-
"""async_upnp_client.ssdp module."""

import logging
import socket
import sys
from asyncio import BaseTransport, DatagramProtocol, DatagramTransport
from asyncio.events import AbstractEventLoop
from datetime import datetime
from functools import lru_cache
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Optional,
    Tuple,
    Union,
    cast,
)
from urllib.parse import urlsplit, urlunsplit

from aiohttp.http_exceptions import InvalidHeader
from aiohttp.http_parser import HeadersParser
from multidict import CIMultiDictProxy

from async_upnp_client.const import (
    AddressTupleV4Type,
    AddressTupleV6Type,
    AddressTupleVXType,
    IPvXAddress,
    SsdpHeaders,
    UniqueDeviceName,
)
from async_upnp_client.exceptions import UpnpError
from async_upnp_client.utils import CaseInsensitiveDict, lowerstr

SSDP_PORT = 1900
SSDP_IP_V4 = "239.255.255.250"
SSDP_IP_V6_LINK_LOCAL = "FF02::C"
SSDP_IP_V6_SITE_LOCAL = "FF05::C"
SSDP_IP_V6_ORGANISATION_LOCAL = "FF08::C"
SSDP_IP_V6_GLOBAL = "FF0E::C"
SSDP_IP_V6 = SSDP_IP_V6_LINK_LOCAL
SSDP_TARGET_V4 = (SSDP_IP_V4, SSDP_PORT)
SSDP_TARGET_V6 = (
    SSDP_IP_V6,
    SSDP_PORT,
    0,
    0,
)  # Replace the last item with your scope_id!
SSDP_TARGET = SSDP_TARGET_V4
SSDP_ST_ALL = "ssdp:all"
SSDP_ST_ROOTDEVICE = "upnp:rootdevice"
SSDP_MX = 4
SSDP_DISCOVER = '"ssdp:discover"'

_LOGGER = logging.getLogger(__name__)
_LOGGER_TRAFFIC_SSDP = logging.getLogger("async_upnp_client.traffic.ssdp")


def get_host_string(addr: AddressTupleVXType) -> str:
    """Construct host string from address tuple."""
    if len(addr) == 4:
        if TYPE_CHECKING:
            addr = cast(AddressTupleV6Type, addr)
        if addr[3]:
            return f"{addr[0]}%{addr[3]}"

    return addr[0]


def get_host_port_string(addr: AddressTupleVXType) -> str:
    """Return a properly escaped host port pair."""
    host = get_host_string(addr)
    if ":" in host:
        return f"[{host}]:{addr[1]}"
    return f"{host}:{addr[1]}"


@lru_cache(maxsize=256)
def get_adjusted_url(url: str, addr: AddressTupleVXType) -> str:
    """Adjust a url with correction for link local scope."""
    if len(addr) < 4:
        return url

    if TYPE_CHECKING:
        addr = cast(AddressTupleV6Type, addr)

    if not addr[3]:
        return url

    data = urlsplit(url)
    assert data.hostname
    try:
        address = ip_address(data.hostname)
    except ValueError:
        return url

    if not address.is_link_local:
        return url

    netloc = f"[{data.hostname}%{addr[3]}]"
    if data.port:
        netloc += f":{data.port}"
    return urlunsplit(data._replace(netloc=netloc))


def is_ipv4_address(addr: AddressTupleVXType) -> bool:
    """Test if addr is a IPv4 tuple."""
    return len(addr) == 2


def is_ipv6_address(addr: AddressTupleVXType) -> bool:
    """Test if addr is a IPv6 tuple."""
    return len(addr) == 4


def build_ssdp_packet(status_line: str, headers: SsdpHeaders) -> bytes:
    """Construct a SSDP packet."""
    headers_str = "\r\n".join([f"{key}:{value}" for key, value in headers.items()])
    return f"{status_line}\r\n{headers_str}\r\n\r\n".encode()


def build_ssdp_search_packet(
    ssdp_target: AddressTupleVXType, ssdp_mx: int, ssdp_st: str
) -> bytes:
    """Construct a SSDP M-SEARCH packet."""
    request_line = "M-SEARCH * HTTP/1.1"
    headers = {
        "HOST": f"{get_host_port_string(ssdp_target)}",
        "MAN": SSDP_DISCOVER,
        "MX": f"{ssdp_mx}",
        "ST": f"{ssdp_st}",
    }
    return build_ssdp_packet(request_line, headers)


@lru_cache(maxsize=128)
def is_valid_ssdp_packet(data: bytes) -> bool:
    """Check if data is a valid and decodable packet."""
    return (
        bool(data)
        and b"\n" in data
        and (
            data.startswith(b"NOTIFY * HTTP/1.1")
            or data.startswith(b"M-SEARCH * HTTP/1.1")
            or data.startswith(b"HTTP/1.1 200 OK")
        )
    )


# No longer used internally, but left for backwards compatibility
def udn_from_headers(
    headers: Union[CIMultiDictProxy, CaseInsensitiveDict]
) -> Optional[UniqueDeviceName]:
    """Get UDN from USN in headers."""
    usn: str = headers.get("usn", "")
    return udn_from_usn(usn)


@lru_cache(maxsize=128)
def udn_from_usn(usn: str) -> Optional[UniqueDeviceName]:
    """Get UDN from USN in headers."""
    if usn.lower().startswith("uuid:"):
        return usn.partition("::")[0]
    return None


@lru_cache(maxsize=128)
def _cached_header_parse(
    data: bytes,
) -> Tuple[CIMultiDictProxy[str], str, Optional[UniqueDeviceName]]:
    """Cache parsing headers.

    SSDP discover packets frequently end up being sent multiple
    times on multiple interfaces.

    We can avoid parsing the sames ones over and over
    again with a simple lru_cache.
    """
    lines = data.replace(b"\r\n", b"\n").split(b"\n")

    # request_line
    request_line = lines[0].strip().decode()

    if lines and lines[-1] != b"":
        lines.append(b"")

    parsed_headers, _ = HeadersParser().parse_headers(lines)

    usn = parsed_headers.get("usn")
    udn = udn_from_usn(usn) if usn else None

    return parsed_headers, request_line, udn


LOWER__TIMESTAMP = lowerstr("_timestamp")
LOWER__HOST = lowerstr("_host")
LOWER__PORT = lowerstr("_port")
LOWER__LOCAL_ADDR = lowerstr("_local_addr")
LOWER__REMOTE_ADDR = lowerstr("_remote_addr")
LOWER__UDN = lowerstr("_udn")
LOWER__LOCATION_ORIGINAL = lowerstr("_location_original")
LOWER_LOCATION = lowerstr("location")


@lru_cache(maxsize=512)
def _cached_decode_ssdp_packet(
    data: bytes,
    remote_addr_without_port: AddressTupleVXType,
) -> Tuple[str, CaseInsensitiveDict]:
    """Cache decoding SSDP packets."""
    parsed_headers, request_line, udn = _cached_header_parse(data)
    # own data
    extra: Dict[str, Any] = {LOWER__HOST: get_host_string(remote_addr_without_port)}
    if udn:
        extra[LOWER__UDN] = udn

    # adjust some headers
    location = parsed_headers.get("location", "")
    if location.strip():
        extra[LOWER__LOCATION_ORIGINAL] = location
        extra[LOWER_LOCATION] = get_adjusted_url(location, remote_addr_without_port)

    headers = CaseInsensitiveDict(parsed_headers, **extra)
    return request_line, headers


def decode_ssdp_packet(
    data: bytes,
    local_addr: Optional[AddressTupleVXType],
    remote_addr: AddressTupleVXType,
) -> Tuple[str, CaseInsensitiveDict]:
    """Decode a message."""
    # We want to use remote_addr_without_port as the cache
    # key since nothing in _cached_decode_ssdp_packet cares
    # about the port
    if len(remote_addr) == 4:
        if TYPE_CHECKING:
            remote_addr = cast(AddressTupleV6Type, remote_addr)
        addr, port, flow, scope = remote_addr
        remote_addr_without_port: AddressTupleVXType = addr, 0, flow, scope
    else:
        if TYPE_CHECKING:
            remote_addr = cast(AddressTupleV4Type, remote_addr)
        addr, port = remote_addr
        remote_addr_without_port = remote_addr[0], 0
    request_line, headers = _cached_decode_ssdp_packet(data, remote_addr_without_port)
    return request_line, headers.combine_lower_dict(
        {
            LOWER__TIMESTAMP: datetime.now(),
            LOWER__REMOTE_ADDR: remote_addr,
            LOWER__PORT: port,
            LOWER__LOCAL_ADDR: local_addr,
        }
    )


class SsdpProtocol(DatagramProtocol):
    """SSDP Protocol."""

    def __init__(
        self,
        loop: AbstractEventLoop,
        async_on_connect: Optional[
            Callable[[DatagramTransport], Coroutine[Any, Any, None]]
        ] = None,
        on_connect: Optional[Callable[[DatagramTransport], None]] = None,
        async_on_data: Optional[
            Callable[[str, CaseInsensitiveDict], Coroutine[Any, Any, None]]
        ] = None,
        on_data: Optional[Callable[[str, CaseInsensitiveDict], None]] = None,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        self.loop = loop
        self.async_on_connect = async_on_connect
        self.on_connect = on_connect
        self.async_on_data = async_on_data
        self.on_data = on_data

        self.transport: Optional[DatagramTransport] = None
        self.local_addr: Optional[AddressTupleVXType] = None

    def connection_made(self, transport: BaseTransport) -> None:
        """Handle connection made."""
        self.transport = cast(DatagramTransport, transport)
        sock: Optional[socket.socket] = transport.get_extra_info("socket")
        self.local_addr = sock.getsockname() if sock is not None else None
        _LOGGER.debug(
            "Connection made, transport: %s, socket: %s",
            transport,
            sock,
        )

        if self.async_on_connect:
            coro = self.async_on_connect(self.transport)
            self.loop.create_task(coro)
        if self.on_connect:
            self.on_connect(self.transport)

    def datagram_received(self, data: bytes, addr: AddressTupleVXType) -> None:
        """Handle a discovery-response."""
        _LOGGER_TRAFFIC_SSDP.debug("Received packet from %s: %s", addr, data)
        assert self.transport

        if is_valid_ssdp_packet(data):
            try:
                request_line, headers = decode_ssdp_packet(data, self.local_addr, addr)
            except InvalidHeader as exc:
                _LOGGER.debug("Ignoring received packet with invalid headers: %s", exc)
                return

            if self.async_on_data:
                coro = self.async_on_data(request_line, headers)
                self.loop.create_task(coro)
            if self.on_data:
                self.on_data(request_line, headers)

    def error_received(self, exc: Exception) -> None:
        """Handle an error."""
        sock: Optional[socket.socket] = (
            self.transport.get_extra_info("socket") if self.transport else None
        )
        _LOGGER.error(
            "Received error: %s, transport: %s, socket: %s", exc, self.transport, sock
        )

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Handle connection lost."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return
        assert self.transport
        sock: Optional[socket.socket] = self.transport.get_extra_info("socket")
        _LOGGER.debug(
            "Lost connection, error: %s, transport: %s, socket: %s",
            exc,
            self.transport,
            sock,
        )

    def send_ssdp_packet(self, packet: bytes, target: AddressTupleVXType) -> None:
        """Send a SSDP packet."""
        assert self.transport
        if _LOGGER.isEnabledFor(logging.DEBUG):
            sock: Optional[socket.socket] = self.transport.get_extra_info("socket")
            _LOGGER.debug(
                "Sending SSDP packet, transport: %s, socket: %s, target: %s",
                self.transport,
                sock,
                target,
            )
        if _LOGGER_TRAFFIC_SSDP.isEnabledFor(logging.DEBUG):
            _LOGGER_TRAFFIC_SSDP.debug(
                "Sending SSDP packet, target: %s, data: %s", target, packet
            )
        self.transport.sendto(packet, target)


def determine_source_target(
    source: Optional[AddressTupleVXType] = None,
    target: Optional[AddressTupleVXType] = None,
) -> Tuple[AddressTupleVXType, AddressTupleVXType]:
    """Determine source and target."""
    if source is None and target is None:
        return ("0.0.0.0", 0), (SSDP_IP_V4, SSDP_PORT)

    if source is not None and target is None:
        if len(source) == 2:
            return source, (SSDP_IP_V4, SSDP_PORT)

        source = cast(AddressTupleV6Type, source)
        return source, (SSDP_IP_V6, SSDP_PORT, 0, source[3])

    if source is None and target is not None:
        if len(target) == 2:
            return (
                "0.0.0.0",
                0,
            ), target

        target = cast(AddressTupleV6Type, target)
        return ("::", 0, 0, target[3]), target

    if source is not None and target is not None and len(source) != len(target):
        raise UpnpError("Source and target do not match protocol")

    return cast(AddressTupleVXType, source), cast(AddressTupleVXType, target)


def fix_ipv6_address_scope_id(
    address: Optional[AddressTupleVXType],
) -> Optional[AddressTupleVXType]:
    """Fix scope_id for an IPv6 address, if needed."""
    if address is None or is_ipv4_address(address):
        return address

    ip_str = address[0]
    if "%" not in ip_str:
        # Nothing to fix.
        return address

    address = cast(AddressTupleV6Type, address)
    idx = ip_str.index("%")
    try:
        ip_scope_id = int(ip_str[idx + 1 :])
    except ValueError:
        pass
    scope_id = address[3]
    new_scope_id = ip_scope_id if not scope_id and ip_scope_id else address[3]
    new_ip = ip_str[:idx]
    return (
        new_ip,
        address[1],
        address[2],
        new_scope_id,
    )


def ip_port_from_address_tuple(
    address_tuple: AddressTupleVXType,
) -> Tuple[IPvXAddress, int]:
    """Get IPvXAddress from AddressTupleVXType."""
    if len(address_tuple) == 4:
        address_tuple = cast(AddressTupleV6Type, address_tuple)
        if "%" in address_tuple[0]:
            return IPv6Address(address_tuple[0]), address_tuple[1]

        return IPv6Address(f"{address_tuple[0]}%{address_tuple[3]}"), address_tuple[1]

    return IPv4Address(address_tuple[0]), address_tuple[1]


def get_ssdp_socket(
    source: AddressTupleVXType,
    target: AddressTupleVXType,
) -> Tuple[socket.socket, AddressTupleVXType, AddressTupleVXType]:
    """Create a socket to listen on."""
    # Ensure a proper IPv6 source/target.
    if is_ipv6_address(source):
        source = cast(AddressTupleV6Type, source)
        if not source[3]:
            raise UpnpError(f"Source missing scope_id, source: {source}")

    if is_ipv6_address(target):
        target = cast(AddressTupleV6Type, target)
        if not target[3]:
            raise UpnpError(f"Target missing scope_id, target: {target}")

    target_ip, target_port = ip_port_from_address_tuple(target)
    target_info = socket.getaddrinfo(
        str(target_ip),
        target_port,
        type=socket.SOCK_DGRAM,
        proto=socket.IPPROTO_UDP,
    )[0]
    source_ip, source_port = ip_port_from_address_tuple(source)
    source_info = socket.getaddrinfo(
        str(source_ip), source_port, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
    )[0]
    _LOGGER.debug("Creating socket, source: %s, target: %s", source_info, target_info)

    # create socket
    sock = socket.socket(source_info[0], source_info[1])

    # set options
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # multicast
    if target_ip.is_multicast:
        if source_info[0] == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 2)
            addr = cast(AddressTupleV6Type, source_info[4])
            if addr[3]:
                mreq = target_ip.packed + addr[3].to_bytes(4, sys.byteorder)
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, addr[3])
            else:
                _LOGGER.debug("Skipping setting multicast interface")
        else:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, source_ip.packed)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                target_ip.packed + source_ip.packed,
            )

    return sock, source_info[4], target_info[4]
