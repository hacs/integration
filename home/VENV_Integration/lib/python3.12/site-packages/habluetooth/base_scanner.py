"""Base classes for HA Bluetooth scanners for bluetooth."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Final, Iterable, final

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bluetooth_adapters import DiscoveredDeviceAdvertisementData, adapter_human_name
from bluetooth_data_tools import monotonic_time_coarse

from .central_manager import get_manager
from .const import (
    CALLBACK_TYPE,
    CONNECTABLE_FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
    SCANNER_WATCHDOG_INTERVAL,
    SCANNER_WATCHDOG_TIMEOUT,
)
from .models import BluetoothServiceInfoBleak, HaBluetoothConnector

SCANNER_WATCHDOG_INTERVAL_SECONDS: Final = SCANNER_WATCHDOG_INTERVAL.total_seconds()
_LOGGER = logging.getLogger(__name__)


_float = float
_int = int
_str = str


class BaseHaScanner:
    """Base class for high availability BLE scanners."""

    __slots__ = (
        "adapter",
        "connectable",
        "source",
        "connector",
        "_connecting",
        "name",
        "scanning",
        "_last_detection",
        "_start_time",
        "_cancel_watchdog",
        "_loop",
        "_manager",
    )

    def __init__(
        self,
        source: str,
        adapter: str,
        connector: HaBluetoothConnector | None = None,
    ) -> None:
        """Initialize the scanner."""
        self.connectable = False
        self.source = source
        self.connector = connector
        self._connecting = 0
        self.adapter = adapter
        self.name = adapter_human_name(adapter, source) if adapter != source else source
        self.scanning = True
        self._last_detection = 0.0
        self._start_time = 0.0
        self._cancel_watchdog: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._manager = get_manager()

    def async_setup(self) -> CALLBACK_TYPE:
        """Set up the scanner."""
        self._loop = asyncio.get_running_loop()
        return self._unsetup

    def _async_stop_scanner_watchdog(self) -> None:
        """Stop the scanner watchdog."""
        if self._cancel_watchdog:
            self._cancel_watchdog.cancel()
            self._cancel_watchdog = None

    def _async_setup_scanner_watchdog(self) -> None:
        """If something has restarted or updated, we need to restart the scanner."""
        self._start_time = self._last_detection = monotonic_time_coarse()
        if not self._cancel_watchdog:
            self._schedule_watchdog()

    def _schedule_watchdog(self) -> None:
        """Schedule the watchdog."""
        loop = self._loop
        if TYPE_CHECKING:
            assert loop is not None
        self._cancel_watchdog = loop.call_at(
            loop.time() + SCANNER_WATCHDOG_INTERVAL_SECONDS,
            self._async_call_scanner_watchdog,
        )

    @final
    def _async_call_scanner_watchdog(self) -> None:
        """Call the scanner watchdog and schedule the next one."""
        self._async_scanner_watchdog()
        self._schedule_watchdog()

    def _async_watchdog_triggered(self) -> bool:
        """Check if the watchdog has been triggered."""
        time_since_last_detection = monotonic_time_coarse() - self._last_detection
        _LOGGER.debug(
            "%s: Scanner watchdog time_since_last_detection: %s",
            self.name,
            time_since_last_detection,
        )
        return time_since_last_detection > SCANNER_WATCHDOG_TIMEOUT

    def _async_scanner_watchdog(self) -> None:
        """
        Check if the scanner is running.

        Override this method if you need to do something else when the watchdog
        is triggered.
        """
        if self._async_watchdog_triggered():
            _LOGGER.info(
                (
                    "%s: Bluetooth scanner has gone quiet for %ss, check logs on the"
                    " scanner device for more information"
                ),
                self.name,
                SCANNER_WATCHDOG_TIMEOUT,
            )
            self.scanning = False
            return
        self.scanning = not self._connecting

    def _unsetup(self) -> None:
        """Unset up the scanner."""

    @contextmanager
    def connecting(self) -> Generator[None, None, None]:
        """Context manager to track connecting state."""
        self._connecting += 1
        self.scanning = not self._connecting
        try:
            yield
        finally:
            self._connecting -= 1
            self.scanning = not self._connecting

    @property
    def discovered_devices(self) -> list[BLEDevice]:
        """Return a list of discovered devices."""
        raise NotImplementedError

    @property
    def discovered_devices_and_advertisement_data(
        self,
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """Return a list of discovered devices and their advertisement data."""
        raise NotImplementedError

    @property
    def discovered_addresses(self) -> Iterable[str]:
        """Return an iterable of discovered devices."""
        raise NotImplementedError

    def get_discovered_device_advertisement_data(
        self, address: str
    ) -> tuple[BLEDevice, AdvertisementData] | None:
        """Return the advertisement data for a discovered device."""
        raise NotImplementedError

    async def async_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic information about the scanner."""
        device_adv_datas = self.discovered_devices_and_advertisement_data.values()
        return {
            "name": self.name,
            "start_time": self._start_time,
            "source": self.source,
            "scanning": self.scanning,
            "type": self.__class__.__name__,
            "last_detection": self._last_detection,
            "monotonic_time": monotonic_time_coarse(),
            "discovered_devices_and_advertisement_data": [
                {
                    "name": device.name,
                    "address": device.address,
                    "rssi": advertisement_data.rssi,
                    "advertisement_data": advertisement_data,
                    "details": device.details,
                }
                for device, advertisement_data in device_adv_datas
            ],
        }


class BaseHaRemoteScanner(BaseHaScanner):
    """Base class for a high availability remote BLE scanner."""

    __slots__ = (
        "_details",
        "_expire_seconds",
        "_cancel_track",
        "_previous_service_info",
    )

    def __init__(
        self,
        scanner_id: str,
        name: str,
        connector: HaBluetoothConnector | None,
        connectable: bool,
    ) -> None:
        """Initialize the scanner."""
        super().__init__(scanner_id, name, connector)
        self.connectable = connectable
        self._details: dict[str, str | HaBluetoothConnector] = {"source": scanner_id}
        # Scanners only care about connectable devices. The manager
        # will handle taking care of availability for non-connectable devices
        self._expire_seconds = CONNECTABLE_FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS
        self._cancel_track: asyncio.TimerHandle | None = None
        self._previous_service_info: dict[str, BluetoothServiceInfoBleak] = {}

    def restore_discovered_devices(
        self, history: DiscoveredDeviceAdvertisementData
    ) -> None:
        """Restore discovered devices from a previous run."""
        discovered_device_timestamps = history.discovered_device_timestamps
        self._previous_service_info = {
            address: BluetoothServiceInfoBleak(
                device.name or address,
                address,
                adv.rssi,
                adv.manufacturer_data,
                adv.service_data,
                adv.service_uuids,
                self.source,
                device,
                adv,
                self.connectable,
                discovered_device_timestamps[address],
                adv.tx_power,
            )
            for address, (
                device,
                adv,
            ) in history.discovered_device_advertisement_datas.items()
        }
        # Expire anything that is too old
        self._async_expire_devices()

    def serialize_discovered_devices(
        self,
    ) -> DiscoveredDeviceAdvertisementData:
        """Serialize discovered devices to be stored."""
        return DiscoveredDeviceAdvertisementData(
            self.connectable,
            self._expire_seconds,
            self._discovered_device_advertisement_datas,
            self._discovered_device_timestamps,
        )

    @property
    def _discovered_device_advertisement_datas(
        self,
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """Return a list of discovered devices and advertisement data."""
        return {
            address: (
                service_info.device,
                service_info.advertisement,
            )
            for address, service_info in self._previous_service_info.items()
        }

    @property
    def _discovered_device_timestamps(self) -> dict[str, float]:
        """Return a dict of discovered device timestamps."""
        return {
            address: service_info.time
            for address, service_info in self._previous_service_info.items()
        }

    def _cancel_expire_devices(self) -> None:
        """Cancel the expiration of old devices."""
        if self._cancel_track:
            self._cancel_track.cancel()
            self._cancel_track = None

    def _unsetup(self) -> None:
        """Unset up the scanner."""
        self._async_stop_scanner_watchdog()
        self._cancel_expire_devices()

    def async_setup(self) -> CALLBACK_TYPE:
        """Set up the scanner."""
        super().async_setup()
        self._schedule_expire_devices()
        self._async_setup_scanner_watchdog()
        return self._unsetup

    def _schedule_expire_devices(self) -> None:
        """Schedule the expiration of old devices."""
        loop = self._loop
        if TYPE_CHECKING:
            assert loop is not None
        self._cancel_expire_devices()
        self._cancel_track = loop.call_at(
            loop.time() + 30, self._async_expire_devices_schedule_next
        )

    def _async_expire_devices_schedule_next(self) -> None:
        """Expire old devices and schedule the next expiration."""
        self._async_expire_devices()
        self._schedule_expire_devices()

    def _async_expire_devices(self) -> None:
        """Expire old devices."""
        now = monotonic_time_coarse()
        expired = [
            address
            for address, service_info in self._previous_service_info.items()
            if now - service_info.time > self._expire_seconds
        ]
        for address in expired:
            del self._previous_service_info[address]

    @property
    def discovered_devices(self) -> list[BLEDevice]:
        """Return a list of discovered devices."""
        service_infos = self._previous_service_info.values()
        return [
            device_advertisement_data.device
            for device_advertisement_data in service_infos
        ]

    @property
    def discovered_devices_and_advertisement_data(
        self,
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """Return a list of discovered devices and advertisement data."""
        return self._discovered_device_advertisement_datas

    @property
    def discovered_addresses(self) -> Iterable[str]:
        """Return an iterable of discovered devices."""
        return self._previous_service_info

    def get_discovered_device_advertisement_data(
        self, address: str
    ) -> tuple[BLEDevice, AdvertisementData] | None:
        """Return the advertisement data for a discovered device."""
        if (info := self._previous_service_info.get(address)) is not None:
            return info.device, info.advertisement
        return None

    def _async_on_advertisement(
        self,
        address: _str,
        rssi: _int,
        local_name: _str | None,
        service_uuids: list[str],
        service_data: dict[str, bytes],
        manufacturer_data: dict[int, bytes],
        tx_power: _int | None,
        details: dict[Any, Any],
        advertisement_monotonic_time: _float,
    ) -> None:
        """Call the registered callback."""
        self.scanning = not self._connecting
        self._last_detection = advertisement_monotonic_time
        if (prev_service_info := self._previous_service_info.get(address)) is None:
            # We expect this is the rare case and since py3.11+ has
            # near zero cost try on success, and we can avoid .get()
            # which is slower than [] we use the try/except pattern.
            device = BLEDevice(
                address,
                local_name,
                {**self._details, **details},
                rssi,  # deprecated, will be removed in newer bleak
            )
        else:
            # Merge the new data with the old data
            # to function the same as BlueZ which
            # merges the dicts on PropertiesChanged
            prev_device = prev_service_info.device
            prev_service_uuids = prev_service_info.service_uuids
            prev_service_data = prev_service_info.service_data
            prev_manufacturer_data = prev_service_info.manufacturer_data
            prev_name = prev_device.name
            prev_details = prev_device.details

            if prev_name and (not local_name or len(prev_name) > len(local_name)):
                local_name = prev_name

            has_service_uuids = bool(service_uuids)
            if has_service_uuids and service_uuids != prev_service_uuids:
                service_uuids = list({*service_uuids, *prev_service_uuids})
            elif not has_service_uuids:
                service_uuids = prev_service_uuids

            has_service_data = bool(service_data)
            if has_service_data and service_data != prev_service_data:
                service_data = {**prev_service_data, **service_data}
            elif not has_service_data:
                service_data = prev_service_data

            has_manufacturer_data = bool(manufacturer_data)
            if has_manufacturer_data and manufacturer_data != prev_manufacturer_data:
                manufacturer_data = {**prev_manufacturer_data, **manufacturer_data}
            elif not has_manufacturer_data:
                manufacturer_data = prev_manufacturer_data
            #
            # Bleak updates the BLEDevice via create_or_update_device.
            # We need to do the same to ensure integrations that already
            # have the BLEDevice object get the updated details when they
            # change.
            #
            # https://github.com/hbldh/bleak/blob/222618b7747f0467dbb32bd3679f8cfaa19b1668/bleak/backends/scanner.py#L203
            #
            device = prev_device
            device.name = local_name
            prev_details.update(details)
            # pylint: disable-next=protected-access
            device._rssi = rssi  # deprecated, will be removed in newer bleak

        service_info = BluetoothServiceInfoBleak.__new__(BluetoothServiceInfoBleak)
        service_info.name = local_name or address
        service_info.address = address
        service_info.rssi = rssi
        service_info.manufacturer_data = manufacturer_data
        service_info.service_data = service_data
        service_info.service_uuids = service_uuids
        service_info.source = self.source
        service_info.device = device
        service_info._advertisement = None
        service_info.connectable = self.connectable
        service_info.time = advertisement_monotonic_time
        service_info.tx_power = tx_power
        self._previous_service_info[address] = service_info
        self._manager.scanner_adv_received(service_info)

    async def async_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic information about the scanner."""
        now = monotonic_time_coarse()
        discovered_device_timestamps = self._discovered_device_timestamps
        return await super().async_diagnostics() | {
            "connectable": self.connectable,
            "discovered_device_timestamps": discovered_device_timestamps,
            "time_since_last_device_detection": {
                address: now - timestamp
                for address, timestamp in discovered_device_timestamps.items()
            },
        }
