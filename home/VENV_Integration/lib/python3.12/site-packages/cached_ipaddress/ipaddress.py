"""Base implementation."""

import sys
from functools import lru_cache
from ipaddress import AddressValueError, IPv4Address, IPv6Address, NetmaskValueError
from typing import Any, Optional, Union

from .backports.functools import cached_property

if sys.version_info < (3, 9):
    cache = lru_cache(maxsize=None)
else:
    from functools import cache


class CachedIPv4Address(IPv4Address):

    def __init__(self, address: Any) -> None:
        super().__init__(address)
        self.__hash__ = cache(lambda: IPv4Address.__hash__(self))  # type: ignore[method-assign]
        self.__int__ = cache(lambda: IPv4Address.__int__(self))  # type: ignore[method-assign]

    def __str__(self) -> str:
        """Return the string representation of the IPv4 address."""
        return self._str

    @cached_property
    def _str(self) -> str:
        """Return the string representation of the IPv4 address."""
        return super().__str__()

    @cached_property
    def is_link_local(self) -> bool:  # type: ignore[override]
        """Return True if this is a link-local address."""
        return super().is_link_local

    @cached_property
    def is_unspecified(self) -> bool:  # type: ignore[override]
        """Return True if this is an unspecified address."""
        return super().is_unspecified

    @cached_property
    def is_loopback(self) -> bool:  # type: ignore[override]
        """Return True if this is a loopback address."""
        return super().is_loopback

    @cached_property
    def is_multicast(self) -> bool:  # type: ignore[override]
        """Return True if this is a multicast address."""
        return super().is_multicast

    @cached_property
    def reverse_pointer(self) -> str:  # type: ignore[override]
        """Return the reverse DNS pointer name for the IPv4 address."""
        return super().reverse_pointer

    @cached_property
    def compressed(self) -> str:  # type: ignore[override]
        """Return the compressed value IPv4 address."""
        return super().compressed


class CachedIPv6Address(IPv6Address):

    def __init__(self, address: Any) -> None:
        super().__init__(address)
        self.__hash__ = cache(lambda: IPv6Address.__hash__(self))  # type: ignore[method-assign]
        self.__int__ = cache(lambda: IPv6Address.__int__(self))  # type: ignore[method-assign]

    def __str__(self) -> str:
        """Return the string representation of the IPv6 address."""
        return self._str

    @cached_property
    def _str(self) -> str:
        """Return the string representation of the IPv6 address."""
        return super().__str__()

    @cached_property
    def is_link_local(self) -> bool:  # type: ignore[override]
        """Return True if this is a link-local address."""
        return super().is_link_local

    @cached_property
    def is_unspecified(self) -> bool:  # type: ignore[override]
        """Return True if this is an unspecified address."""
        return super().is_unspecified

    @cached_property
    def is_loopback(self) -> bool:  # type: ignore[override]
        """Return True if this is a loopback address."""
        return super().is_loopback

    @cached_property
    def is_multicast(self) -> bool:  # type: ignore[override]
        """Return True if this is a multicast address."""
        return super().is_multicast

    @cached_property
    def reverse_pointer(self) -> str:  # type: ignore[override]
        """Return the reverse DNS pointer name for the IPv6 address."""
        return super().reverse_pointer

    @cached_property
    def compressed(self) -> str:  # type: ignore[override]
        """Return the compressed value IPv6 address."""
        return super().compressed


@lru_cache(maxsize=535)
def _cached_ip_addresses(
    address: Union[str, bytes, int]
) -> Optional[Union[IPv4Address, IPv6Address]]:
    """Cache IP addresses."""
    try:
        return CachedIPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return CachedIPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        return None


cached_ip_addresses_wrapper = _cached_ip_addresses
cached_ip_addresses = cached_ip_addresses_wrapper

__all__ = ("cached_ip_addresses",)
