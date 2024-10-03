from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from functools import lru_cache, partial
from ipaddress import IPv4Address
from itertools import islice
from typing import TYPE_CHECKING, Any, Iterable, cast

from aiodns import DNSResolver

from .network import SystemNetworkData

if TYPE_CHECKING:
    from pyroute2.iproute import IPRoute  # noqa: F401

HOSTNAME = "hostname"
MAC_ADDRESS = "macaddress"
IP_ADDRESS = "ip"
MAX_ADDRESSES = 2048
QUERY_BUCKET_SIZE = 64

DNS_RESPONSE_TIMEOUT = 2


_LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=MAX_ADDRESSES)
def decode_idna(name: str) -> str:
    """Decode an idna name."""
    try:
        return name.encode().decode("idna")
    except UnicodeError:
        return name


def dns_message_short_hostname(dns_message: Any | None) -> str | None:
    """Get the short hostname from a dns message."""
    if dns_message is None:
        return None
    name: str = dns_message.name
    if name.startswith("xn--"):
        name = decode_idna(name)
    return name.partition(".")[0]


async def async_query_for_ptrs(
    nameserver: str, ips_to_lookup: list[IPv4Address]
) -> list[Any | None]:
    """Fetch PTR records for a list of ips."""
    resolver = DNSResolver(nameservers=[nameserver], timeout=DNS_RESPONSE_TIMEOUT)
    results: list[Any | None] = []
    for ip_chunk in chunked(ips_to_lookup, QUERY_BUCKET_SIZE):
        if TYPE_CHECKING:
            ip_chunk = cast("list[IPv4Address]", ip_chunk)
        futures = [resolver.query(ip.reverse_pointer, "PTR") for ip in ip_chunk]
        await asyncio.wait(futures)
        results.extend(
            None if future.exception() else future.result() for future in futures
        )
    resolver.cancel()
    return results


def take(take_num: int, iterable: Iterable) -> list[Any]:
    """Return first n items of the iterable as a list.

    From itertools recipes
    """
    return list(islice(iterable, take_num))


def chunked(iterable: Iterable, chunked_num: int) -> Iterable[Any]:
    """Break *iterable* into lists of length *n*.

    From more-itertools
    """
    return iter(partial(take, chunked_num, iter(iterable)), [])


class DiscoverHosts:
    """Discover hosts on the network by ARP and PTR lookup."""

    def __init__(self) -> None:
        """Init the discovery hosts."""
        self._sys_network_data: SystemNetworkData | None = None

    def _setup_sys_network_data(self) -> None:
        ip_route: "IPRoute" | None = None
        with suppress(Exception):
            from pyroute2.iproute import (  # noqa: F811
                IPRoute,
            )  # type: ignore # pylint: disable=import-outside-toplevel

            ip_route = IPRoute()
        sys_network_data = SystemNetworkData(ip_route)
        sys_network_data.setup()
        self._sys_network_data = sys_network_data

    async def async_discover(self) -> list[dict[str, str]]:
        """Discover hosts on the network by ARP and PTR lookup."""
        if not self._sys_network_data:
            await asyncio.get_running_loop().run_in_executor(
                None, self._setup_sys_network_data
            )
        sys_network_data = self._sys_network_data
        network = sys_network_data.network
        assert network is not None
        if network.num_addresses > MAX_ADDRESSES:
            _LOGGER.debug(
                "The network %s exceeds the maximum number of addresses, %s; No scanning performed",
                network,
                MAX_ADDRESSES,
            )
            return []
        hostnames = await self.async_get_hostnames(sys_network_data)
        neighbours = await sys_network_data.async_get_neighbors(hostnames.keys())
        return [
            {
                HOSTNAME: hostname,
                MAC_ADDRESS: neighbours[ip],
                IP_ADDRESS: ip,
            }
            for ip, hostname in hostnames.items()
            if ip in neighbours
        ]

    async def _async_get_nameservers(
        self, sys_network_data: SystemNetworkData
    ) -> list[str]:
        """Get nameservers to query."""
        all_nameservers = list(sys_network_data.nameservers)
        router_ip = sys_network_data.router_ip
        assert router_ip is not None
        if router_ip not in all_nameservers:
            neighbours = await sys_network_data.async_get_neighbors([router_ip])
            if router_ip in neighbours:
                all_nameservers.insert(0, router_ip)
        return all_nameservers

    async def async_get_hostnames(
        self, sys_network_data: SystemNetworkData
    ) -> dict[str, str]:
        """Lookup PTR records for all addresses in the network."""
        all_nameservers = await self._async_get_nameservers(sys_network_data)
        assert sys_network_data.network is not None
        ips = list(sys_network_data.network.hosts())
        hostnames: dict[str, str] = {}
        for nameserver in all_nameservers:
            ips_to_lookup = [ip for ip in ips if str(ip) not in hostnames]
            results = await async_query_for_ptrs(nameserver, ips_to_lookup)
            for idx, ip in enumerate(ips_to_lookup):
                short_host = dns_message_short_hostname(results[idx])
                if short_host is None:
                    continue
                hostnames[str(ip)] = short_host
            if hostnames:
                # As soon as we have a responsive nameserver, there
                # is no need to query additional fallbacks
                break
        return hostnames
