"""Bluetooth data tools."""

from __future__ import annotations

from .distance import calculate_distance_meters
from .gap import (
    BLEGAPAdvertisement,
    BLEGAPType,
    parse_advertisement_data,
    parse_advertisement_data_tuple,
)
from .privacy import get_cipher_for_irk, resolve_private_address
from .time import monotonic_time_coarse
from .utils import (
    address_to_bytes,
    human_readable_name,
    int_to_bluetooth_address,
    mac_to_int,
    manufacturer_data_to_raw,
    newest_manufacturer_data,
    short_address,
)

__version__ = "1.20.0"


__all__ = [
    "address_to_bytes",
    "manufacturer_data_to_raw",
    "newest_manufacturer_data",
    "human_readable_name",
    "int_to_bluetooth_address",
    "short_address",
    "BLEGAPType",
    "BLEGAPAdvertisement",
    "parse_advertisement_data",
    "parse_advertisement_data_tuple",
    "calculate_distance_meters",
    "get_cipher_for_irk",
    "resolve_private_address",
    "monotonic_time_coarse",
    "mac_to_int",
]
