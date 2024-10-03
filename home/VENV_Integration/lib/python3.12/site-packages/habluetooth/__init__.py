__version__ = "3.4.0"

from .advertisement_tracker import (
    TRACKER_BUFFERING_WOBBLE_SECONDS,
    AdvertisementTracker,
)
from .base_scanner import BaseHaRemoteScanner, BaseHaScanner
from .central_manager import get_manager, set_manager
from .const import (
    CONNECTABLE_FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
    SCANNER_WATCHDOG_INTERVAL,
    SCANNER_WATCHDOG_TIMEOUT,
    UNAVAILABLE_TRACK_SECONDS,
)
from .manager import BluetoothManager
from .models import (
    BluetoothServiceInfo,
    BluetoothServiceInfoBleak,
    HaBluetoothConnector,
)
from .scanner import BluetoothScanningMode, HaScanner, ScannerStartError
from .scanner_device import BluetoothScannerDevice
from .wrappers import HaBleakClientWrapper, HaBleakScannerWrapper

__all__ = [
    "BluetoothServiceInfo",
    "BluetoothServiceInfoBleak",
    "HaBleakScannerWrapper",
    "HaBleakClientWrapper",
    "BluetoothManager",
    "get_manager",
    "set_manager",
    "BluetoothScannerDevice",
    "UNAVAILABLE_TRACK_SECONDS",
    "TRACKER_BUFFERING_WOBBLE_SECONDS",
    "AdvertisementTracker",
    "BluetoothScanningMode",
    "ScannerStartError",
    "HaScanner",
    "BaseHaScanner",
    "BaseHaRemoteScanner",
    "HaBluetoothConnector",
    "FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS",
    "CONNECTABLE_FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS",
    "SCANNER_WATCHDOG_TIMEOUT",
    "SCANNER_WATCHDOG_INTERVAL",
]
