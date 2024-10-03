"""Bluetooth utils."""

from __future__ import annotations

from functools import lru_cache
from struct import Struct

L_PACK = Struct(">L")

try:
    from ._utils_impl import _int_to_bluetooth_address  # noqa: F811 F401


except ImportError:

    def _int_to_bluetooth_address(address: int) -> str:
        """Convert an integer to a bluetooth address."""
        mac_hex = f"{address:012X}"
        return f"{mac_hex[0:2]}:{mac_hex[2:4]}:{mac_hex[4:6]}:{mac_hex[6:8]}:{mac_hex[8:10]}:{mac_hex[10:12]}"  # noqa: E501


int_to_bluetooth_address = lru_cache(maxsize=256)(_int_to_bluetooth_address)


def mac_to_int(address: str) -> int:
    """Convert a mac address to an integer."""
    return int(address.replace(":", ""), 16)


def short_address(address: str) -> str:
    """Convert a Bluetooth address to a short address."""
    results = address.replace("-", ":").split(":")
    last: str = results[-1]
    second_last: str = results[-2]
    return f"{second_last.upper()}{last.upper()}"[-4:]


def human_readable_name(name: str | None, local_name: str, address: str) -> str:
    """Return a human readable name for the given name, local_name, and address."""
    return f"{name or local_name} ({short_address(address)})"


def newest_manufacturer_data(manufacturer_data: dict[int, bytes]) -> bytes | None:
    """Return the raw data from manufacturer data."""
    if manufacturer_data and (last_id := list(manufacturer_data)[-1]):
        return manufacturer_data[last_id]
    return None


def address_to_bytes(address: str) -> bytes:
    """Return the address as bytes."""
    if ":" not in address:
        address_as_int = 0
    else:
        address_as_int = mac_to_int(address)
    return L_PACK.pack(address_as_int)


def manufacturer_data_to_raw(manufacturer_id: int, manufacturer_data: bytes) -> bytes:
    """Return the raw data from manufacturer data."""
    init_bytes: bytes = int(manufacturer_id).to_bytes(2, byteorder="little")
    return b"\x00" * 2 + init_bytes + manufacturer_data
