"""The bluetooth integration."""

from __future__ import annotations

import asyncio
import itertools
import logging
from collections.abc import Callable, Iterable
from functools import partial
from typing import TYPE_CHECKING, Any, Final

from bleak.backends.scanner import AdvertisementDataCallback
from bleak_retry_connector import NO_RSSI_VALUE, RSSI_SWITCH_THRESHOLD, BleakSlotManager
from bluetooth_adapters import (
    ADAPTER_ADDRESS,
    ADAPTER_PASSIVE_SCAN,
    AdapterDetails,
    BluetoothAdapters,
)
from bluetooth_data_tools import monotonic_time_coarse

from .advertisement_tracker import (
    TRACKER_BUFFERING_WOBBLE_SECONDS,
    AdvertisementTracker,
)
from .const import (
    CALLBACK_TYPE,
    FAILED_ADAPTER_MAC,
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
    UNAVAILABLE_TRACK_SECONDS,
)
from .models import BluetoothServiceInfoBleak
from .scanner_device import BluetoothScannerDevice
from .usage import install_multiple_bleak_catcher, uninstall_multiple_bleak_catcher
from .util import async_reset_adapter

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData

    from .base_scanner import BaseHaScanner


FILTER_UUIDS: Final = "UUIDs"

APPLE_MFR_ID: Final = 76
APPLE_IBEACON_START_BYTE: Final = 0x02  # iBeacon (tilt_ble)
APPLE_HOMEKIT_START_BYTE: Final = 0x06  # homekit_controller
APPLE_DEVICE_ID_START_BYTE: Final = 0x10  # bluetooth_le_tracker
APPLE_HOMEKIT_NOTIFY_START_BYTE: Final = 0x11  # homekit_controller
APPLE_START_BYTES_WANTED: Final = {
    APPLE_IBEACON_START_BYTE,
    APPLE_HOMEKIT_START_BYTE,
    APPLE_HOMEKIT_NOTIFY_START_BYTE,
    APPLE_DEVICE_ID_START_BYTE,
}

_str = str

_LOGGER = logging.getLogger(__name__)


def _dispatch_bleak_callback(
    bleak_callback: BleakCallback,
    device: BLEDevice,
    advertisement_data: AdvertisementData,
) -> None:
    """Dispatch the callback."""
    if (
        uuids := bleak_callback.filters.get(FILTER_UUIDS)
    ) is not None and not uuids.intersection(advertisement_data.service_uuids):
        return

    try:
        bleak_callback.callback(device, advertisement_data)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Error in callback: %s", bleak_callback.callback)


class BleakCallback:
    """Bleak callback."""

    __slots__ = ("callback", "filters")

    def __init__(
        self, callback: AdvertisementDataCallback, filters: dict[str, set[str]]
    ) -> None:
        """Init bleak callback."""
        self.callback = callback
        self.filters = filters


class BluetoothManager:
    """Manage Bluetooth."""

    __slots__ = (
        "_cancel_unavailable_tracking",
        "_advertisement_tracker",
        "_fallback_intervals",
        "_intervals",
        "_unavailable_callbacks",
        "_connectable_unavailable_callbacks",
        "_bleak_callbacks",
        "_all_history",
        "_connectable_history",
        "_non_connectable_scanners",
        "_connectable_scanners",
        "_adapters",
        "_sources",
        "_bluetooth_adapters",
        "slot_manager",
        "_debug",
        "shutdown",
        "_loop",
        "_adapter_refresh_future",
        "_recovery_lock",
    )

    def __init__(
        self,
        bluetooth_adapters: BluetoothAdapters,
        slot_manager: BleakSlotManager,
    ) -> None:
        """Init bluetooth manager."""
        self._cancel_unavailable_tracking: asyncio.TimerHandle | None = None

        self._advertisement_tracker = AdvertisementTracker()
        self._fallback_intervals = self._advertisement_tracker.fallback_intervals
        self._intervals = self._advertisement_tracker.intervals

        self._unavailable_callbacks: dict[
            str, set[Callable[[BluetoothServiceInfoBleak], None]]
        ] = {}
        self._connectable_unavailable_callbacks: dict[
            str, set[Callable[[BluetoothServiceInfoBleak], None]]
        ] = {}

        self._bleak_callbacks: set[BleakCallback] = set()
        self._all_history: dict[str, BluetoothServiceInfoBleak] = {}
        self._connectable_history: dict[str, BluetoothServiceInfoBleak] = {}
        self._non_connectable_scanners: set[BaseHaScanner] = set()
        self._connectable_scanners: set[BaseHaScanner] = set()
        self._adapters: dict[str, AdapterDetails] = {}
        self._sources: dict[str, BaseHaScanner] = {}
        self._bluetooth_adapters = bluetooth_adapters
        self.slot_manager = slot_manager
        self._debug = _LOGGER.isEnabledFor(logging.DEBUG)
        self.shutdown = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._adapter_refresh_future: asyncio.Future[None] | None = None
        self._recovery_lock: asyncio.Lock = asyncio.Lock()

    @property
    def supports_passive_scan(self) -> bool:
        """Return if passive scan is supported."""
        return any(adapter[ADAPTER_PASSIVE_SCAN] for adapter in self._adapters.values())

    def async_scanner_count(self, connectable: bool = True) -> int:
        """Return the number of scanners."""
        if connectable:
            return len(self._connectable_scanners)
        return len(self._connectable_scanners) + len(self._non_connectable_scanners)

    async def async_diagnostics(self) -> dict[str, Any]:
        """Diagnostics for the manager."""
        scanner_diagnostics = await asyncio.gather(
            *[
                scanner.async_diagnostics()
                for scanner in itertools.chain(
                    self._non_connectable_scanners, self._connectable_scanners
                )
            ]
        )
        return {
            "adapters": self._adapters,
            "slot_manager": self.slot_manager.diagnostics(),
            "scanners": scanner_diagnostics,
            "connectable_history": [
                service_info.as_dict()
                for service_info in self._connectable_history.values()
            ],
            "all_history": [
                service_info.as_dict() for service_info in self._all_history.values()
            ],
            "advertisement_tracker": self._advertisement_tracker.async_diagnostics(),
        }

    def _find_adapter_by_address(self, address: str) -> str | None:
        for adapter, details in self._adapters.items():
            if details[ADAPTER_ADDRESS] == address:
                return adapter
        return None

    def async_scanner_by_source(self, source: str) -> BaseHaScanner | None:
        """Return the scanner for a source."""
        return self._sources.get(source)

    async def _async_refresh_adapters(self) -> None:
        """Refresh the adapters."""
        if self._adapter_refresh_future:
            await self._adapter_refresh_future
            return
        if TYPE_CHECKING:
            assert self._loop is not None
        self._adapter_refresh_future = self._loop.create_future()
        try:
            await self._bluetooth_adapters.refresh()
            self._adapters = self._bluetooth_adapters.adapters
        finally:
            self._adapter_refresh_future.set_result(None)
            self._adapter_refresh_future = None

    async def async_get_bluetooth_adapters(
        self, cached: bool = True
    ) -> dict[str, AdapterDetails]:
        """Get bluetooth adapters."""
        if not self._adapters or not cached:
            if not cached:
                await self._async_refresh_adapters()
            self._adapters = self._bluetooth_adapters.adapters
        return self._adapters

    async def async_get_adapter_from_address(self, address: str) -> str | None:
        """Get adapter from address."""
        if adapter := self._find_adapter_by_address(address):
            return adapter
        await self._async_refresh_adapters()
        return self._find_adapter_by_address(address)

    async def async_get_adapter_from_address_or_recover(
        self, address: str
    ) -> str | None:
        """Get adapter from address or recover."""
        if adapter := self._find_adapter_by_address(address):
            return adapter
        await self._async_recover_failed_adapters()
        return self._find_adapter_by_address(address)

    async def _async_recover_failed_adapters(self) -> None:
        """Recover failed adapters."""
        if self._recovery_lock.locked():
            # Already recovering, no need to
            # start another recovery
            return
        async with self._recovery_lock:
            adapters = await self.async_get_bluetooth_adapters()
            for adapter in [
                adapter
                for adapter, details in adapters.items()
                if details[ADAPTER_ADDRESS] == FAILED_ADAPTER_MAC
            ]:
                await async_reset_adapter(adapter, FAILED_ADAPTER_MAC)
            await self._async_refresh_adapters()

    async def async_setup(self) -> None:
        """Set up the bluetooth manager."""
        self._loop = asyncio.get_running_loop()
        await self._async_refresh_adapters()
        install_multiple_bleak_catcher()
        self.async_setup_unavailable_tracking()

    def async_stop(self) -> None:
        """Stop the Bluetooth integration at shutdown."""
        _LOGGER.debug("Stopping bluetooth manager")
        self.shutdown = True
        if self._cancel_unavailable_tracking:
            self._cancel_unavailable_tracking.cancel()
            self._cancel_unavailable_tracking = None
        uninstall_multiple_bleak_catcher()

    def async_scanner_devices_by_address(
        self, address: str, connectable: bool
    ) -> list[BluetoothScannerDevice]:
        """Get BluetoothScannerDevice by address."""
        if not connectable:
            scanners: Iterable[BaseHaScanner] = itertools.chain(
                self._connectable_scanners, self._non_connectable_scanners
            )
        else:
            scanners = self._connectable_scanners
        return [
            BluetoothScannerDevice(scanner, *device_adv)
            for scanner in scanners
            if (device_adv := scanner.get_discovered_device_advertisement_data(address))
        ]

    def _async_all_discovered_addresses(self, connectable: bool) -> Iterable[str]:
        """
        Return all of discovered addresses.

        Include addresses from all the scanners including duplicates.
        """
        yield from itertools.chain.from_iterable(
            scanner.discovered_addresses for scanner in self._connectable_scanners
        )
        if not connectable:
            yield from itertools.chain.from_iterable(
                scanner.discovered_addresses
                for scanner in self._non_connectable_scanners
            )

    def async_discovered_devices(self, connectable: bool) -> list[BLEDevice]:
        """Return all of combined best path to discovered from all the scanners."""
        histories = self._connectable_history if connectable else self._all_history
        return [history.device for history in histories.values()]

    def async_setup_unavailable_tracking(self) -> None:
        """Set up the unavailable tracking."""
        self._schedule_unavailable_tracking()

    def _schedule_unavailable_tracking(self) -> None:
        """Schedule the unavailable tracking."""
        if TYPE_CHECKING:
            assert self._loop is not None
        loop = self._loop
        self._cancel_unavailable_tracking = loop.call_at(
            loop.time() + UNAVAILABLE_TRACK_SECONDS, self._async_check_unavailable
        )

    def _async_check_unavailable(self) -> None:
        """Watch for unavailable devices and cleanup state history."""
        monotonic_now = monotonic_time_coarse()
        connectable_history = self._connectable_history
        all_history = self._all_history
        tracker = self._advertisement_tracker
        intervals = tracker.intervals

        for connectable in (True, False):
            if connectable:
                unavailable_callbacks = self._connectable_unavailable_callbacks
            else:
                unavailable_callbacks = self._unavailable_callbacks
            history = connectable_history if connectable else all_history
            disappeared = set(history).difference(
                self._async_all_discovered_addresses(connectable)
            )
            for address in disappeared:
                if not connectable:
                    #
                    # For non-connectable devices we also check the device has exceeded
                    # the advertising interval before we mark it as unavailable
                    # since it may have gone to sleep and since we do not need an active
                    # connection to it we can only determine its availability
                    # by the lack of advertisements
                    if advertising_interval := (
                        intervals.get(address) or self._fallback_intervals.get(address)
                    ):
                        advertising_interval += TRACKER_BUFFERING_WOBBLE_SECONDS
                    else:
                        advertising_interval = (
                            FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS
                        )
                    time_since_seen = monotonic_now - all_history[address].time
                    if time_since_seen <= advertising_interval:
                        continue

                    # The second loop (connectable=False) is responsible for removing
                    # the device from all the interval tracking since it is no longer
                    # available for both connectable and non-connectable
                    tracker.async_remove_fallback_interval(address)
                    tracker.async_remove_address(address)
                    self._address_disappeared(address)

                service_info = history.pop(address)

                if not (callbacks := unavailable_callbacks.get(address)):
                    continue

                for callback in callbacks.copy():
                    try:
                        callback(service_info)
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.exception("Error in unavailable callback")

        self._schedule_unavailable_tracking()

    def _address_disappeared(self, address: str) -> None:
        """
        Call when an address disappears from the stack.

        This method is intended to be overridden by subclasses.
        """

    def _prefer_previous_adv_from_different_source(
        self,
        address: _str,
        old: BluetoothServiceInfoBleak,
        new: BluetoothServiceInfoBleak,
    ) -> bool:
        """Prefer previous advertisement from a different source if it is better."""
        if stale_seconds := self._intervals.get(
            address, self._fallback_intervals.get(address, 0)
        ):
            stale_seconds += TRACKER_BUFFERING_WOBBLE_SECONDS
        else:
            stale_seconds = FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS
        if new.time - old.time > stale_seconds:
            # If the old advertisement is stale, any new advertisement is preferred
            if self._debug:
                _LOGGER.debug(
                    (
                        "%s (%s): Switching from %s to %s (time elapsed:%s > stale"
                        " seconds:%s)"
                    ),
                    new.name,
                    new.address,
                    self._async_describe_source(old),
                    self._async_describe_source(new),
                    new.time - old.time,
                    stale_seconds,
                )
            return False
        if (new.rssi or NO_RSSI_VALUE) - RSSI_SWITCH_THRESHOLD > (
            old.rssi or NO_RSSI_VALUE
        ):
            # If new advertisement is RSSI_SWITCH_THRESHOLD more,
            # the new one is preferred.
            if self._debug:
                _LOGGER.debug(
                    (
                        "%s (%s): Switching from %s to %s (new rssi:%s - threshold:%s >"
                        " old rssi:%s)"
                    ),
                    new.name,
                    address,
                    self._async_describe_source(old),
                    self._async_describe_source(new),
                    new.rssi,
                    RSSI_SWITCH_THRESHOLD,
                    old.rssi,
                )
            return False
        return True

    def scanner_adv_received(self, service_info: BluetoothServiceInfoBleak) -> None:
        """
        Handle a new advertisement from any scanner.

        Callbacks from all the scanners arrive here.
        """
        # Pre-filter noisy apple devices as they can account for 20-35% of the
        # traffic on a typical network.
        if (
            len(service_info.manufacturer_data) == 1
            and not service_info.service_data
            and (apple_data := service_info.manufacturer_data.get(APPLE_MFR_ID))
            is not None
            and apple_data[0] not in APPLE_START_BYTES_WANTED
        ):
            return

        address = service_info.address
        if connectable := service_info.connectable:
            old_connectable_service_info = self._connectable_history.get(address)
        else:
            old_connectable_service_info = None
        source = service_info.source
        # This logic is complex due to the many combinations of scanners
        # that are supported.
        #
        # We need to handle multiple connectable and non-connectable scanners
        # and we need to handle the case where a device is connectable on one scanner
        # but not on another.
        #
        # The device may also be connectable only by a scanner that has worse
        # signal strength than a non-connectable scanner.
        #
        # all_history - the history of all advertisements from all scanners with the
        #               best advertisement from each scanner
        # connectable_history - the history of all connectable advertisements from all
        #                       scanners with the best advertisement from each
        #                       connectable scanner
        #
        if (
            (old_service_info := self._all_history.get(address)) is not None
            and source != (old_source := old_service_info.source)
            and (scanner := self._sources.get(old_source)) is not None
            and scanner.scanning
            and self._prefer_previous_adv_from_different_source(
                address, old_service_info, service_info
            )
        ):
            # If we are rejecting the new advertisement and the device is connectable
            # but not in the connectable history or the connectable source is the same
            # as the new source, we need to add it to the connectable history
            if connectable:
                if old_connectable_service_info is not None and (
                    # If its the same as the preferred source, we are done
                    # as we know we prefer the old advertisement
                    # from the check above
                    (old_connectable_service_info is old_service_info)
                    # If the old connectable source is different from the preferred
                    # source, we need to check it as well to see if we prefer
                    # the old connectable advertisement
                    or (
                        (old_connectable_source := old_connectable_service_info.source)
                        != source
                        and (
                            connectable_scanner := self._sources.get(
                                old_connectable_source
                            )
                        )
                        is not None
                        and connectable_scanner.scanning
                        and self._prefer_previous_adv_from_different_source(
                            address, old_connectable_service_info, service_info
                        )
                    )
                ):
                    return

                self._connectable_history[address] = service_info

            return

        if connectable:
            self._connectable_history[address] = service_info

        self._all_history[address] = service_info

        # Track advertisement intervals to determine when we need to
        # switch adapters or mark a device as unavailable
        tracker = self._advertisement_tracker
        if (
            last_source := tracker.sources.get(address)
        ) is not None and last_source != source:
            # Source changed, remove the old address from the tracker
            tracker.async_remove_address(address)
        if address not in tracker.intervals:
            tracker.async_collect(service_info)

        # If the advertisement data is the same as the last time we saw it, we
        # don't need to do anything else unless its connectable and we are missing
        # connectable history for the device so we can make it available again
        # after unavailable callbacks.
        if (
            # Ensure its not a connectable device missing from connectable history
            not (connectable and old_connectable_service_info is None)
            # Than check if advertisement data is the same
            and old_service_info is not None
            and not (
                service_info.manufacturer_data != old_service_info.manufacturer_data
                or service_info.service_data != old_service_info.service_data
                or service_info.service_uuids != old_service_info.service_uuids
                or service_info.name != old_service_info.name
            )
        ):
            return

        if not connectable and old_connectable_service_info is not None:
            # Since we have a connectable path and our BleakClient will
            # route any connection attempts to the connectable path, we
            # mark the service_info as connectable so that the callbacks
            # will be called and the device can be discovered.
            service_info = BluetoothServiceInfoBleak(
                service_info.name,
                address,
                service_info.rssi,
                service_info.manufacturer_data,
                service_info.service_data,
                service_info.service_uuids,
                source,
                service_info.device,
                service_info._advertisement,
                True,
                service_info.time,
                service_info.tx_power,
            )

        if (connectable or old_connectable_service_info is not None) and (
            bleak_callbacks := self._bleak_callbacks
        ) is not None:
            # Bleak callbacks must get a connectable device
            device = service_info.device
            advertisement_data = service_info.advertisement
            for bleak_callback in bleak_callbacks:
                _dispatch_bleak_callback(bleak_callback, device, advertisement_data)

        self._discover_service_info(service_info)

    def _discover_service_info(self, service_info: BluetoothServiceInfoBleak) -> None:
        """
        Discover a new service info.

        This method is intended to be overridden by subclasses.
        """

    def _async_describe_source(self, service_info: BluetoothServiceInfoBleak) -> str:
        """Describe a source."""
        if scanner := self._sources.get(service_info.source):
            description = scanner.name
        else:
            description = service_info.source
        if service_info.connectable:
            description += " [connectable]"
        return description

    def _async_remove_unavailable_callback_internal(
        self,
        unavailable_callbacks: dict[
            str, set[Callable[[BluetoothServiceInfoBleak], None]]
        ],
        address: str,
        callbacks: set[Callable[[BluetoothServiceInfoBleak], None]],
        callback: Callable[[BluetoothServiceInfoBleak], None],
    ) -> None:
        """Remove a callback."""
        callbacks.remove(callback)
        if not callbacks:
            del unavailable_callbacks[address]

    def async_track_unavailable(
        self,
        callback: Callable[[BluetoothServiceInfoBleak], None],
        address: str,
        connectable: bool,
    ) -> Callable[[], None]:
        """Register a callback."""
        if connectable:
            unavailable_callbacks = self._connectable_unavailable_callbacks
        else:
            unavailable_callbacks = self._unavailable_callbacks
        callbacks = unavailable_callbacks.setdefault(address, set())
        callbacks.add(callback)
        return partial(
            self._async_remove_unavailable_callback_internal,
            unavailable_callbacks,
            address,
            callbacks,
            callback,
        )

    def async_ble_device_from_address(
        self, address: str, connectable: bool
    ) -> BLEDevice | None:
        """Return the BLEDevice if present."""
        histories = self._connectable_history if connectable else self._all_history
        if history := histories.get(address):
            return history.device
        return None

    def async_address_present(self, address: str, connectable: bool) -> bool:
        """Return if the address is present."""
        histories = self._connectable_history if connectable else self._all_history
        return address in histories

    def async_discovered_service_info(
        self, connectable: bool
    ) -> Iterable[BluetoothServiceInfoBleak]:
        """Return all the discovered services info."""
        histories = self._connectable_history if connectable else self._all_history
        return histories.values()

    def async_last_service_info(
        self, address: str, connectable: bool
    ) -> BluetoothServiceInfoBleak | None:
        """Return the last service info for an address."""
        histories = self._connectable_history if connectable else self._all_history
        return histories.get(address)

    def _async_unregister_scanner_internal(
        self,
        scanners: set[BaseHaScanner],
        scanner: BaseHaScanner,
        connection_slots: int | None,
    ) -> None:
        """Unregister a scanner."""
        _LOGGER.debug("Unregistering scanner %s", scanner.name)
        self._advertisement_tracker.async_remove_source(scanner.source)
        scanners.remove(scanner)
        del self._sources[scanner.source]
        if connection_slots:
            self.slot_manager.remove_adapter(scanner.adapter)

    def async_register_scanner(
        self,
        scanner: BaseHaScanner,
        connection_slots: int | None = None,
    ) -> CALLBACK_TYPE:
        """Register a new scanner."""
        _LOGGER.debug("Registering scanner %s", scanner.name)
        if scanner.connectable:
            scanners = self._connectable_scanners
        else:
            scanners = self._non_connectable_scanners
        scanners.add(scanner)
        self._sources[scanner.source] = scanner
        if connection_slots:
            self.slot_manager.register_adapter(scanner.adapter, connection_slots)
        return partial(
            self._async_unregister_scanner_internal, scanners, scanner, connection_slots
        )

    def async_register_bleak_callback(
        self, callback: AdvertisementDataCallback, filters: dict[str, set[str]]
    ) -> CALLBACK_TYPE:
        """Register a callback."""
        callback_entry = BleakCallback(callback, filters)
        self._bleak_callbacks.add(callback_entry)
        # Replay the history since otherwise we miss devices
        # that were already discovered before the callback was registered
        # or we are in passive mode
        for history in self._connectable_history.values():
            _dispatch_bleak_callback(
                callback_entry, history.device, history.advertisement
            )

        return partial(self._bleak_callbacks.remove, callback_entry)

    def async_release_connection_slot(self, device: BLEDevice) -> None:
        """Release a connection slot."""
        self.slot_manager.release_slot(device)

    def async_allocate_connection_slot(self, device: BLEDevice) -> bool:
        """Allocate a connection slot."""
        return self.slot_manager.allocate_slot(device)

    def async_get_learned_advertising_interval(self, address: str) -> float | None:
        """Get the learned advertising interval for a MAC address."""
        return self._intervals.get(address)

    def async_get_fallback_availability_interval(self, address: str) -> float | None:
        """Get the fallback availability timeout for a MAC address."""
        return self._fallback_intervals.get(address)

    def async_set_fallback_availability_interval(
        self, address: str, interval: float
    ) -> None:
        """Override the fallback availability timeout for a MAC address."""
        self._fallback_intervals[address] = interval
