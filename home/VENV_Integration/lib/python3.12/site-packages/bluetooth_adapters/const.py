"""Constants for bluetooth adapters."""

from typing import Final

WINDOWS_DEFAULT_BLUETOOTH_ADAPTER: Final = "bluetooth"
MACOS_DEFAULT_BLUETOOTH_ADAPTER: Final = "Core Bluetooth"
UNIX_DEFAULT_BLUETOOTH_ADAPTER: Final = "hci0"

# Some operating systems hide the adapter address for privacy reasons (ex MacOS)
DEFAULT_ADDRESS: Final = "00:00:00:00:00:00"

EMPTY_MAC_ADDRESS: Final = "00:00:00:00:00:00"

DEFAULT_CONNECTION_SLOTS: Final = 5
