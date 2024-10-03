from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Generator
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .bleak_manager import get_global_bluez_manager_with_timeout
from .const import (
    DISCONNECT_TIMEOUT,
    IS_LINUX,
    NO_RSSI_VALUE,
    REAPPEAR_WAIT_INTERVAL,
    RSSI_SWITCH_THRESHOLD,
)
from .util import asyncio_timeout

if IS_LINUX:
    from dbus_fast.message import Message

_LOGGER = logging.getLogger(__name__)


if IS_LINUX:
    with contextlib.suppress(ImportError):  # pragma: no cover
        from bleak.backends.bluezdbus import defs  # pragma: no cover
        from bleak.backends.bluezdbus.manager import (  # pragma: no cover
            BlueZManager,
            DeviceWatcher,
        )


def device_source(device: BLEDevice) -> str | None:
    """Return the device source."""
    return _device_details_value_or_none(device, "source")


def _device_details_value_or_none(device: BLEDevice, key: str) -> Any | None:
    """Return a value from device details or None."""
    details = device.details
    if not isinstance(details, dict) or key not in details:
        return None
    key_value: str = device.details[key]
    return key_value


def adapter_from_path(path: str) -> str:
    """Get the adapter from a ble device path."""
    return path.split("/")[3]


def path_from_ble_device(device: BLEDevice) -> str | None:
    """Get the adapter from a ble device."""
    return _device_details_value_or_none(device, "path")


def _on_characteristic_value_changed(*args: Any, **kwargs: Any) -> None:
    """Dummy callback for registering characteristic value changed."""


class BleakSlotManager:

    """A class to manage the connection slots."""

    def __init__(self) -> None:
        """Initialize the class."""
        self._adapter_slots: dict[str, int] = {}
        self._allocations_by_adapter: dict[str, dict[str, DeviceWatcher]] = {}
        self._manager: BlueZManager | None = None

    async def async_setup(self) -> None:
        """Set up the class."""
        self._manager = await get_global_bluez_manager_with_timeout()

    def diagnostics(self) -> dict[str, Any]:
        """Return diagnostics."""
        return {
            "manager": self._manager is not None,
            "adapter_slots": self._adapter_slots,
            "allocations_by_adapter": {
                adapter: self._get_allocations(adapter)
                for adapter in self._adapter_slots
            },
        }

    def _get_allocations(self, adapter: str) -> list[str]:
        """Get connected path allocations."""
        if self._manager is None:
            return []
        return list(self._allocations_by_adapter[adapter])

    def remove_adapter(self, adapter: str) -> None:
        """Remove an adapter."""
        del self._adapter_slots[adapter]
        watchers = self._allocations_by_adapter[adapter]
        if self._manager is None:
            return
        for watcher in watchers.values():
            self._manager.remove_device_watcher(watcher)
        del self._allocations_by_adapter[adapter]

    def register_adapter(self, adapter: str, slots: int) -> None:
        """Register an adapter."""
        self._allocations_by_adapter[adapter] = {}
        self._adapter_slots[adapter] = slots
        if self._manager is None:
            return
        for path, device in self._manager._properties.items():
            if (
                defs.DEVICE_INTERFACE in device
                and device[defs.DEVICE_INTERFACE].get("Connected")
                and adapter_from_path(path) == adapter
            ):
                self._allocate_and_watch_slot(path)

    def _allocate_and_watch_slot(self, path: str) -> None:
        """Setup a device watcher."""
        assert self._manager is not None  # nosec
        adapter = adapter_from_path(path)
        allocations = self._allocations_by_adapter[adapter]

        def _on_device_connected_changed(connected: bool) -> None:
            if not connected:
                self._release_slot(path)

        allocations[path] = self._manager.add_device_watcher(
            path,
            on_connected_changed=_on_device_connected_changed,
            on_characteristic_value_changed=_on_characteristic_value_changed,
        )

    def release_slot(self, device: BLEDevice) -> None:
        """Release a slot."""
        if (
            self._manager is None
            or not (path := path_from_ble_device(device))
            or self._manager.is_connected(path)
        ):
            return
        self._release_slot(path)

    def _release_slot(self, path: str) -> None:
        """Unconditional release of the slot."""
        assert self._manager is not None  # nosec
        adapter = adapter_from_path(path)
        allocations = self._allocations_by_adapter[adapter]
        if watcher := allocations.pop(path, None):
            self._manager.remove_device_watcher(watcher)

    def allocate_slot(self, device: BLEDevice) -> bool:
        """Allocate a slot."""
        if (
            self._manager is None
            or not (path := path_from_ble_device(device))
            or not (adapter := adapter_from_path(path))
            or adapter not in self._allocations_by_adapter
        ):
            return True
        allocations = self._allocations_by_adapter[adapter]
        if path in allocations:
            # Already connected
            return True
        if len(allocations) >= self._adapter_slots[adapter]:
            _LOGGER.debug(
                "No slots available for %s (used by: %s)",
                path,
                self._get_allocations(adapter),
            )
            return False
        self._allocate_and_watch_slot(path)
        return True


async def _get_properties() -> dict[str, dict[str, dict[str, Any]]] | None:
    """Get the properties."""
    if bluez_manager := await get_global_bluez_manager_with_timeout():
        return bluez_manager._properties  # pylint: disable=protected-access
    return None


async def clear_cache(address: str) -> bool:
    """Clear the cache for a device."""
    if not IS_LINUX or not await get_device(address):
        return False
    caches_cleared: list[str] = []
    with contextlib.suppress(Exception):
        if not (manager := await get_global_bluez_manager_with_timeout()):
            _LOGGER.warning("Failed to clear cache for %s because no manager", address)
            return False
        services_cache = manager._services_cache
        bluez_path = address_to_bluez_path(address)
        for path in _get_possible_paths(bluez_path):
            if services_cache.pop(path, None):
                caches_cleared.append(path)
        _LOGGER.debug("Cleared cache for %s: %s", address, caches_cleared)
        async with asyncio_timeout(DISCONNECT_TIMEOUT):
            for device_path in caches_cleared:
                # Send since we are going to ignore errors
                # in case the device is already gone
                await manager._bus.send(
                    Message(
                        destination=defs.BLUEZ_SERVICE,
                        path=adapter_path_from_device_path(device_path),
                        interface=defs.ADAPTER_INTERFACE,
                        member="RemoveDevice",
                        signature="o",
                        body=[device_path],
                    )
                )
    return bool(caches_cleared)


def adapter_path_from_device_path(device_path: str) -> str:
    """
    Scrape the adapter path from a D-Bus device path.

    Args:
        device_path: The D-Bus object path of the device.

    Returns:
        A D-Bus object path of the adapter.
    """
    # /org/bluez/hci1/dev_FA_23_9D_AA_45_46
    return device_path[:15]


async def wait_for_device_to_reappear(device: BLEDevice, wait_timeout: float) -> bool:
    """Wait for a device to reappear on the bus."""
    await asyncio.sleep(0)
    if (
        not IS_LINUX
        or not isinstance(device.details, dict)
        or "path" not in device.details
        or not (properties := await _get_properties())
    ):
        await asyncio.sleep(wait_timeout)
        return False

    debug = _LOGGER.isEnabledFor(logging.DEBUG)
    device_path = address_to_bluez_path(device.address)
    for i in range(int(wait_timeout / REAPPEAR_WAIT_INTERVAL)):
        for path in _get_possible_paths(device_path):
            if path in properties and properties[path].get(defs.DEVICE_INTERFACE):
                if debug:
                    _LOGGER.debug(
                        "%s - %s: Device re-appeared on bus after %s seconds as %s",
                        device.name,
                        device.address,
                        i * REAPPEAR_WAIT_INTERVAL,
                        path,
                    )
                return True
        if debug:
            _LOGGER.debug(
                "%s - %s: Waiting %s/%s for device to re-appear on bus",
                device.name,
                device.address,
                (i + 1) * REAPPEAR_WAIT_INTERVAL,
                wait_timeout,
            )
        await asyncio.sleep(REAPPEAR_WAIT_INTERVAL)
    if debug:
        _LOGGER.debug(
            "%s - %s: Device did not re-appear on bus after %s seconds",
            device.name,
            device.address,
            wait_timeout,
        )
    return False


async def wait_for_disconnect(device: BLEDevice, min_wait_time: float) -> None:
    """Wait for the device to disconnect.

    After a connection failure, the device may not have
    had time to disconnect so we wait for it to do so.

    If we do not wait, we may end up connecting to the
    same device again before it has had time to disconnect.
    """
    if (
        not IS_LINUX
        or not isinstance(device.details, dict)
        or "path" not in device.details
    ):
        await asyncio.sleep(min_wait_time)
        return
    device_path = device.details["path"]
    start = time.monotonic() if min_wait_time else 0
    try:
        if not (manager := await get_global_bluez_manager_with_timeout()):
            _LOGGER.debug(
                "%s - %s: Failed to wait for disconnect because no manager",
                device.name,
                device.address,
            )
            return
        async with asyncio_timeout(DISCONNECT_TIMEOUT):
            await manager._wait_condition(device_path, "Connected", False)
        end = time.monotonic() if min_wait_time else 0
        waited = end - start
        _LOGGER.debug(
            "%s - %s: Waited %s seconds to disconnect",
            device.name,
            device.address,
            waited,
        )
        if min_wait_time and waited < min_wait_time:
            await asyncio.sleep(min_wait_time - waited)
    except (BleakError, KeyError) as ex:
        # Device was removed from bus
        #
        # In testing it was found that most of the CSR adapters
        # only support 5 slots and the broadcom only support 7 slots.
        #
        # When they run out of slots the device they are trying to
        # connect to disappears from the bus so we must backoff
        _LOGGER.debug(
            "%s - %s: Device was removed from bus at %s, waiting %s for it to re-appear: (%s) %s",
            device.name,
            device.address,
            device_path,
            min_wait_time,
            type(ex),
            ex,
        )
        await wait_for_device_to_reappear(device, min_wait_time)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.debug(
            "%s - %s: Failed waiting for disconnect at %s",
            device.name,
            device.address,
            device_path,
            exc_info=True,
        )


async def get_device_by_adapter(address: str, adapter: str) -> BLEDevice | None:
    """Get the device by adapter and address."""
    if not IS_LINUX:
        return None
    if not (properties := await _get_properties()):
        return None
    device_path = address_to_bluez_path(address, adapter)
    if device_path in properties and (
        device_props := properties[device_path].get(defs.DEVICE_INTERFACE)
    ):
        return ble_device_from_properties(device_path, device_props)
    return None


async def get_bluez_device(
    name: str, path: str, rssi: int | None = None, _log_disappearance: bool = True
) -> BLEDevice | None:
    """Get a BLEDevice object for a BlueZ DBus path."""

    best_path = device_path = path
    rssi_to_beat: int = rssi or NO_RSSI_VALUE

    if not (properties := await _get_properties()):
        return None

    if (
        device_path not in properties
        or defs.DEVICE_INTERFACE not in properties[device_path]
    ):
        # device has disappeared so take
        # anything over the current path
        if _log_disappearance:
            _LOGGER.debug("%s - %s: Device has disappeared", name, device_path)
        rssi_to_beat = NO_RSSI_VALUE

    for path in _get_possible_paths(device_path):
        if path not in properties or not (
            device_props := properties[path].get(defs.DEVICE_INTERFACE)
        ):
            continue

        if device_props.get("Connected"):
            # device is connected so take it
            _LOGGER.debug("%s - %s: Device is already connected", name, path)
            if path == device_path:
                # device is connected to the path we were given
                # so we can just return None so it will be used
                return None
            return ble_device_from_properties(path, device_props)

        if path == device_path:
            # Device is not connected and is the original path
            # so no need to check it since returning None will
            # cause the device to be used anyways.
            continue

        alternate_device_rssi: int = device_props.get("RSSI") or NO_RSSI_VALUE
        if (
            rssi_to_beat != NO_RSSI_VALUE
            and alternate_device_rssi - RSSI_SWITCH_THRESHOLD < rssi_to_beat
        ):
            continue
        best_path = path
        _LOGGER.debug(
            "%s - %s: Found path %s with better RSSI %s > %s",
            name,
            device_path,
            path,
            alternate_device_rssi,
            rssi_to_beat,
        )
        rssi_to_beat = alternate_device_rssi

    if best_path == device_path:
        return None

    return ble_device_from_properties(
        best_path, properties[best_path][defs.DEVICE_INTERFACE]
    )


async def get_connected_devices(device: BLEDevice) -> list[BLEDevice]:
    """Check if the device is connected."""
    connected: list[BLEDevice] = []

    if not isinstance(device.details, dict) or "path" not in device.details:
        return connected
    if not (properties := await _get_properties()):
        return connected
    device_path = device.details["path"]
    for path in _get_possible_paths(device_path):
        if path not in properties or defs.DEVICE_INTERFACE not in properties[path]:
            continue
        props = properties[path][defs.DEVICE_INTERFACE]
        if props.get("Connected"):
            connected.append(ble_device_from_properties(path, props))
    return connected


async def get_device(address: str) -> BLEDevice | None:
    """Get the device."""
    if not IS_LINUX:
        return None
    return await get_bluez_device(
        address, address_to_bluez_path(address), _log_disappearance=False
    )


def address_to_bluez_path(address: str, adapter: str | None = None) -> str:
    """Convert an address to a BlueZ path."""
    return f"/org/bluez/{adapter or 'hciX'}/dev_{address.upper().replace(':', '_')}"


def _get_possible_paths(path: str) -> Generator[str, None, None]:
    """Get the possible paths."""
    # The path is deterministic so we splice up the string
    # /org/bluez/hci2/dev_FA_23_9D_AA_45_46
    for i in range(0, 9):
        yield f"{path[0:14]}{i}{path[15:]}"


def ble_device_from_properties(path: str, props: dict[str, Any]) -> BLEDevice:
    """Get a BLEDevice from a dict of properties."""
    return BLEDevice(
        props["Address"],
        props["Alias"],
        {"path": path, "props": props},
        props.get("RSSI") or NO_RSSI_VALUE,
        uuids=props.get("UUIDs", []),
        manufacturer_data={
            k: bytes(v) for k, v in props.get("ManufacturerData", {}).items()
        },
    )
