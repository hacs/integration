"""Models for bluetooth adapters."""

from __future__ import annotations

from typing import Final, TypedDict


class AdapterDetails(TypedDict, total=False):
    """Adapter details."""

    address: str
    sw_version: str
    hw_version: str | None
    manufacturer: str | None
    product: str | None
    vendor_id: str | None
    product_id: str | None
    passive_scan: bool
    connection_slots: int | None


ADAPTER_ADDRESS: Final = "address"
ADAPTER_SW_VERSION: Final = "sw_version"
ADAPTER_HW_VERSION: Final = "hw_version"
ADAPTER_PASSIVE_SCAN: Final = "passive_scan"
ADAPTER_MANUFACTURER: Final = "manufacturer"
ADAPTER_PRODUCT: Final = "product"
ADAPTER_VENDOR_ID: Final = "vendor_id"
ADAPTER_PRODUCT_ID: Final = "product_id"
ADAPTER_CONNECTION_SLOTS: Final = "connection_slots"
