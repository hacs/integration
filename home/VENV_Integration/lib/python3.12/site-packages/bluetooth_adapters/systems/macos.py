import platform

from ..adapters import BluetoothAdapters
from ..const import DEFAULT_ADDRESS, MACOS_DEFAULT_BLUETOOTH_ADAPTER
from ..models import AdapterDetails


class MacOSAdapters(BluetoothAdapters):
    """Class for getting the bluetooth adapters on a MacOS system."""

    @property
    def adapters(self) -> dict[str, AdapterDetails]:
        """Get the adapter details."""
        return {
            MACOS_DEFAULT_BLUETOOTH_ADAPTER: AdapterDetails(
                address=DEFAULT_ADDRESS,
                sw_version=platform.release(),
                passive_scan=False,
                manufacturer="Apple",
                product="Unknown MacOS Model",
                vendor_id="Unknown",
                product_id="Unknown",
            )
        }

    @property
    def default_adapter(self) -> str:
        """Get the default adapter."""
        return MACOS_DEFAULT_BLUETOOTH_ADAPTER
