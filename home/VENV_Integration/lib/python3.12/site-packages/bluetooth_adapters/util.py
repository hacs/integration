"""Utils."""

from __future__ import annotations

import sys

from .const import DEFAULT_ADDRESS
from .models import (
    ADAPTER_PRODUCT,
    ADAPTER_PRODUCT_ID,
    ADAPTER_VENDOR_ID,
    AdapterDetails,
)

if sys.version_info[:2] < (3, 11):
    from async_timeout import timeout as asyncio_timeout  # noqa: F401
else:
    from asyncio import timeout as asyncio_timeout  # noqa: F401


def adapter_human_name(adapter: str, address: str) -> str:
    """Return a human readable name for the adapter."""
    return adapter if address == DEFAULT_ADDRESS else f"{adapter} ({address})"


def adapter_unique_name(adapter: str, address: str) -> str:
    """Return a unique name for the adapter."""
    return adapter if address == DEFAULT_ADDRESS else address


def adapter_model(details: AdapterDetails) -> str:
    """Return a model for the adapter."""
    if (vendor_id := details.get(ADAPTER_VENDOR_ID)) and vendor_id != "Unknown":
        return f"{details[ADAPTER_PRODUCT]} ({vendor_id}:{details[ADAPTER_PRODUCT_ID]})"
    return details.get(ADAPTER_PRODUCT) or "Unknown"
