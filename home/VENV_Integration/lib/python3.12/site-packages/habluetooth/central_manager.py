"""Central manager for bluetooth."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import BluetoothManager


class CentralBluetoothManager:
    """Central Bluetooth Manager."""

    manager: BluetoothManager | None = None


def get_manager() -> BluetoothManager:
    """Get the BluetoothManager."""
    if CentralBluetoothManager.manager is None:
        raise RuntimeError("BluetoothManager has not been set")
    return CentralBluetoothManager.manager


def set_manager(manager: BluetoothManager) -> None:
    """Set the BluetoothManager."""
    CentralBluetoothManager.manager = manager
