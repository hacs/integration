from __future__ import annotations

import asyncio
import re
import socket
import sys
from contextlib import suppress
from ipaddress import IPv4Network, ip_network
from typing import TYPE_CHECKING, Any, Iterable

import ifaddr  # type: ignore
from cached_ipaddress import cached_ip_addresses

from .util import asyncio_timeout

if TYPE_CHECKING:
    from pyroute2.iproute import IPRoute
# Some MAC addresses will drop the leading zero so
# our mac validation must allow a single char
VALID_MAC_ADDRESS = re.compile("^([0-9A-Fa-f]{1,2}[:-]){5}([0-9A-Fa-f]{1,2})$")

ARP_CACHE_POPULATE_TIME = 10
ARP_TIMEOUT = 10

DEFAULT_NETWORK_PREFIX = 24


PRIVATE_AND_LOCAL_NETWORKS = (
    ip_network("127.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
)

DEFAULT_TARGET = "10.255.255.255"
MDNS_TARGET_IP = "224.0.0.251"
PUBLIC_TARGET_IP = "8.8.8.8"
LOOPBACK_TARGET_IP = "127.0.0.1"

IGNORE_MACS = {"00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"}


def load_resolv_conf() -> list[str]:
    """Load the resolv.conf."""
    with open("/etc/resolv.conf") as file:
        lines = tuple(file)
    nameservers = set()
    for line in lines:
        line = line.strip()
        if not len(line):
            continue
        if line[0] in ("#", ";"):
            continue
        key, value = line.split(None, 1)
        if key == "nameserver":
            if ip_addr := cached_ip_addresses(value):
                nameservers.add(ip_addr)
    return list(nameservers)


def get_local_ip(target: str = DEFAULT_TARGET) -> str | None:
    """Find the local ip address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    try:
        s.connect((target, 1))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def get_network(local_ip: str, adapters: Any) -> IPv4Network:
    """Search adapters for the network and broadcast ip."""
    network_prefix = (
        get_ip_prefix_from_adapters(local_ip, adapters) or DEFAULT_NETWORK_PREFIX
    )
    return ip_network(f"{local_ip}/{network_prefix}", False)


def get_ip_prefix_from_adapters(local_ip: str, adapters: Any) -> int | None:
    """Find the nework prefix for an adapter."""
    for adapter in adapters:
        for ip in adapter.ips:
            if local_ip == ip.ip:
                return ip.network_prefix
    return None


def get_attrs_key(data: Any, key: Any) -> Any:
    """Lookup an attrs key in pyroute2 data."""
    for attr_key, attr_value in data["attrs"]:
        if attr_key == key:
            return attr_value


def get_router_ip(ipr: "IPRoute") -> Any:
    """Obtain the router ip from the default route."""
    return get_attrs_key(ipr.get_default_routes()[0], "RTA_GATEWAY")


def _fill_neighbor(neighbours: dict[str, str], ip: str, mac: str) -> None:
    """Add a neighbor if it is valid."""
    if not (ip_addr := cached_ip_addresses(ip)):
        return
    if (
        ip_addr.is_loopback
        or ip_addr.is_link_local
        or ip_addr.is_multicast
        or ip_addr.is_unspecified
    ):
        return
    if not VALID_MAC_ADDRESS.match(mac):
        return
    mac = ":".join([i.zfill(2) for i in mac.split(":")])
    if mac in IGNORE_MACS:
        return
    neighbours[ip] = mac


def async_populate_arp(ip_addresses):
    """Send an empty packet to a host to populate the arp cache."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.setblocking(False)
    for ip_addr in ip_addresses:
        try:
            sock.sendto(b"", (ip_addr, 80))
        except Exception:
            pass
    return sock


class SystemNetworkData:
    """Gather system network data."""

    def __init__(self, ip_route: "IPRoute" | None, local_ip: str | None = None) -> None:
        """Init system network data."""
        self.ip_route = ip_route
        self.local_ip = local_ip
        self.broadcast_ip: str | None = None
        self.router_ip: str | None = None
        self.network: IPv4Network | None = None
        self.adapters: Any = None
        self.nameservers: list[str] = []

    def setup(self) -> None:
        """Obtain the local network data."""
        try:
            resolvers = load_resolv_conf()
        except FileNotFoundError:
            if sys.platform != "win32":
                raise
        else:
            self.nameservers = [
                str(ip_addr)
                for ip_addr in resolvers
                if any(ip_addr in network for network in PRIVATE_AND_LOCAL_NETWORKS)
            ]
        self.adapters = ifaddr.get_adapters()
        if not self.local_ip:
            self.local_ip = (
                get_local_ip(DEFAULT_TARGET)
                or get_local_ip(MDNS_TARGET_IP)
                or get_local_ip(PUBLIC_TARGET_IP)
                or get_local_ip(LOOPBACK_TARGET_IP)
            )
        assert self.local_ip is not None
        self.network = get_network(self.local_ip, self.adapters)
        if self.ip_route:
            try:
                self.router_ip = get_router_ip(self.ip_route)
            except Exception:
                pass
        if not self.router_ip:
            # On MacOS netifaces is the only reliable way to get the default gateway
            with suppress(Exception):
                import netifaces  # type: ignore # pylint: disable=import-outside-toplevel

                self.router_ip = netifaces.gateways()["default"][netifaces.AF_INET][0]
        if not self.router_ip:
            network_address = str(self.network.network_address)
            self.router_ip = f"{network_address[:-1]}1"

    async def async_get_neighbors(self, ips: Iterable[str]) -> dict[str, str]:
        """Get neighbors with best available method."""
        neighbors = await self._async_get_neighbors()
        ips_missing_arp = [ip for ip in ips if ip not in neighbors]
        if not ips_missing_arp:
            return neighbors
        sock = async_populate_arp(ips_missing_arp)
        await asyncio.sleep(ARP_CACHE_POPULATE_TIME)
        sock.close()
        neighbors.update(await self._async_get_neighbors())
        return neighbors

    async def _async_get_neighbors(self) -> dict[str, str]:
        """Get neighbors from the arp table."""
        if self.ip_route:
            return await self._async_get_neighbors_ip_route()
        return await self._async_get_neighbors_arp()

    async def _async_get_neighbors_arp(self) -> dict[str, str]:
        """Get neighbors with arp command."""
        neighbours: dict[str, str] = {}
        arp = await asyncio.create_subprocess_exec(
            "arp",
            "-a",
            "-n",
            stdin=None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            close_fds=False,
        )
        try:
            async with asyncio_timeout(ARP_TIMEOUT):
                out_data, _ = await arp.communicate()
        except asyncio.TimeoutError:
            if arp:
                with suppress(TypeError):
                    await arp.kill()  # type: ignore
                del arp
            return neighbours
        except AttributeError:
            return neighbours

        for line in out_data.decode().splitlines():
            chomped = line.strip()
            data = chomped.split()
            if len(data) < 4:
                continue
            ip = data[1].strip("()")
            mac = data[3]
            _fill_neighbor(neighbours, ip, mac)

        return neighbours

    async def _async_get_neighbors_ip_route(self):
        """Get neighbors with pyroute2."""
        neighbours = {}
        loop = asyncio.get_running_loop()
        # This shouldn't ever block but it does
        # interact with netlink so its safer to run
        # in the executor
        for neighbour in await loop.run_in_executor(None, self.ip_route.get_neighbours):
            ip = None
            mac = None
            for key, value in neighbour["attrs"]:
                if key == "NDA_DST":
                    ip = value
                elif key == "NDA_LLADDR":
                    mac = value
            if ip and mac:
                _fill_neighbor(neighbours, ip, mac)

        return neighbours
