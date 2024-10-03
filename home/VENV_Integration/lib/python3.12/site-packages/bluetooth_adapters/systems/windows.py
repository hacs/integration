from __future__ import annotations

import platform

from ..adapters import BluetoothAdapters
from ..const import DEFAULT_ADDRESS, WINDOWS_DEFAULT_BLUETOOTH_ADAPTER
from ..models import AdapterDetails


class WindowsAdapters(BluetoothAdapters):
    """Class for getting the bluetooth adapters on a Windows system."""

    @property
    def adapters(self) -> dict[str, AdapterDetails]:
        """Get the adapter details."""
        return {
            WINDOWS_DEFAULT_BLUETOOTH_ADAPTER: AdapterDetails(
                address=DEFAULT_ADDRESS,
                sw_version=platform.release(),
                passive_scan=False,
                manufacturer="Microsoft",
                product="Unknown Windows Model",
                vendor_id="Unknown",
                product_id="Unknown",
            )
        }

    @property
    def default_adapter(self) -> str:
        """Get the default adapter."""
        return WINDOWS_DEFAULT_BLUETOOTH_ADAPTER
