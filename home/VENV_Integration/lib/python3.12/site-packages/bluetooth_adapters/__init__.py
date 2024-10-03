__version__ = "0.19.4"


from platform import system

from .adapters import BluetoothAdapters
from .const import (
    DEFAULT_ADDRESS,
    DEFAULT_CONNECTION_SLOTS,
    MACOS_DEFAULT_BLUETOOTH_ADAPTER,
    UNIX_DEFAULT_BLUETOOTH_ADAPTER,
    WINDOWS_DEFAULT_BLUETOOTH_ADAPTER,
)

if system() != "Windows":
    from .dbus import (
        BlueZDBusObjects,
        get_bluetooth_adapter_details,
        get_bluetooth_adapters,
        get_dbus_managed_objects,
    )

from .history import AdvertisementHistory, load_history_from_managed_objects
from .models import (
    ADAPTER_ADDRESS,
    ADAPTER_CONNECTION_SLOTS,
    ADAPTER_HW_VERSION,
    ADAPTER_MANUFACTURER,
    ADAPTER_PASSIVE_SCAN,
    ADAPTER_PRODUCT,
    ADAPTER_PRODUCT_ID,
    ADAPTER_SW_VERSION,
    ADAPTER_VENDOR_ID,
    AdapterDetails,
)
from .storage import (
    DiscoveredDeviceAdvertisementData,
    DiscoveredDeviceAdvertisementDataDict,
    DiscoveryStorageType,
    discovered_device_advertisement_data_from_dict,
    discovered_device_advertisement_data_to_dict,
    expire_stale_scanner_discovered_device_advertisement_data,
)
from .systems import get_adapters
from .systems.linux_hci import get_adapters_from_hci
from .util import adapter_human_name, adapter_model, adapter_unique_name

__all__ = [
    "AdvertisementHistory",
    "BluetoothAdapters",
    "BlueZDBusObjects",
    "DiscoveredDeviceAdvertisementData",
    "DiscoveredDeviceAdvertisementDataDict",
    "DiscoveryStorageType",
    "adapter_human_name",
    "adapter_unique_name",
    "adapter_model",
    "discovered_device_advertisement_data_to_dict",
    "discovered_device_advertisement_data_from_dict",
    "expire_stale_scanner_discovered_device_advertisement_data",
    "get_adapters_from_hci",
    "get_bluetooth_adapters",
    "get_bluetooth_adapter_details",
    "get_dbus_managed_objects",
    "get_adapters",
    "load_history_from_managed_objects",
    "AdapterDetails",
    "ADAPTER_ADDRESS",
    "ADAPTER_CONNECTION_SLOTS",
    "ADAPTER_SW_VERSION",
    "ADAPTER_HW_VERSION",
    "ADAPTER_PASSIVE_SCAN",
    "ADAPTER_MANUFACTURER",
    "ADAPTER_PRODUCT",
    "ADAPTER_VENDOR_ID",
    "ADAPTER_PRODUCT_ID",
    "WINDOWS_DEFAULT_BLUETOOTH_ADAPTER",
    "MACOS_DEFAULT_BLUETOOTH_ADAPTER",
    "UNIX_DEFAULT_BLUETOOTH_ADAPTER",
    "DEFAULT_ADDRESS",
    "DEFAULT_CONNECTION_SLOTS",
]
