# cython: profile=True
"""A local bleak scanner."""

from __future__ import annotations

import asyncio
import logging
import platform
from typing import Any, Coroutine, Iterable, no_type_check

import async_interrupt
import bleak
from bleak import BleakError
from bleak.assigned_numbers import AdvertisementDataType
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData, AdvertisementDataCallback
from bleak_retry_connector import restore_discoveries
from bluetooth_adapters import DEFAULT_ADDRESS
from bluetooth_data_tools import monotonic_time_coarse
from dbus_fast import InvalidMessageError

from .base_scanner import BaseHaScanner
from .const import (
    CALLBACK_TYPE,
    SCANNER_WATCHDOG_INTERVAL,
    SCANNER_WATCHDOG_TIMEOUT,
    SOURCE_LOCAL,
    START_TIMEOUT,
    STOP_TIMEOUT,
)
from .models import BluetoothScanningMode, BluetoothServiceInfoBleak
from .util import async_reset_adapter, is_docker_env

SYSTEM = platform.system()
IS_LINUX = SYSTEM == "Linux"
IS_MACOS = SYSTEM == "Darwin"

if IS_LINUX:
    from bleak.backends.bluezdbus.advertisement_monitor import (
        AdvertisementMonitor,
        OrPattern,
    )
    from bleak.backends.bluezdbus.scanner import BlueZScannerArgs
    from dbus_fast.service import method

    # or_patterns is a workaround for the fact that passive scanning
    # needs at least one matcher to be set. The below matcher
    # will match all devices.
    PASSIVE_SCANNER_ARGS = BlueZScannerArgs(
        or_patterns=[
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x02"),
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x06"),
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x1a"),
        ]
    )

    class HaAdvertisementMonitor(AdvertisementMonitor):
        """Implementation of the org.bluez.AdvertisementMonitor1 D-Bus interface."""

        @method()
        @no_type_check
        def DeviceFound(self, device: "o"):  # noqa: UP037, F821
            """Device found."""

        @method()
        @no_type_check
        def DeviceLost(self, device: "o"):  # noqa: UP037, F821
            """Device lost."""

    AdvertisementMonitor.DeviceFound = HaAdvertisementMonitor.DeviceFound
    AdvertisementMonitor.DeviceLost = HaAdvertisementMonitor.DeviceLost

OriginalBleakScanner = bleak.BleakScanner

_LOGGER = logging.getLogger(__name__)


# If the adapter is in a stuck state the following errors are raised:
NEED_RESET_ERRORS = [
    "org.bluez.Error.Failed",
    "org.bluez.Error.InProgress",
    "org.bluez.Error.NotReady",
    "not found",
]

# When the adapter is still initializing, the scanner will raise an exception
# with org.freedesktop.DBus.Error.UnknownObject
WAIT_FOR_ADAPTER_TO_INIT_ERRORS = ["org.freedesktop.DBus.Error.UnknownObject"]
ADAPTER_INIT_TIME = 1.5

START_ATTEMPTS = 4

SCANNING_MODE_TO_BLEAK = {
    BluetoothScanningMode.ACTIVE: "active",
    BluetoothScanningMode.PASSIVE: "passive",
}

# The minimum number of seconds to know
# the adapter has not had advertisements
# and we already tried to restart the scanner
# without success when the first time the watch
# dog hit the failure path.
SCANNER_WATCHDOG_MULTIPLE = (
    SCANNER_WATCHDOG_TIMEOUT + SCANNER_WATCHDOG_INTERVAL.total_seconds()
)


class _AbortStartError(Exception):
    """Error to indicate that the start should be aborted."""


class ScannerStartError(Exception):
    """Error to indicate that the scanner failed to start."""


def create_bleak_scanner(
    detection_callback: AdvertisementDataCallback,
    scanning_mode: BluetoothScanningMode,
    adapter: str | None,
) -> bleak.BleakScanner:
    """Create a Bleak scanner."""
    scanner_kwargs: dict[str, Any] = {
        "detection_callback": detection_callback,
        "scanning_mode": SCANNING_MODE_TO_BLEAK[scanning_mode],
    }
    if IS_LINUX:
        # Only Linux supports multiple adapters
        if adapter:
            scanner_kwargs["adapter"] = adapter
        if scanning_mode == BluetoothScanningMode.PASSIVE:
            scanner_kwargs["bluez"] = PASSIVE_SCANNER_ARGS
    elif IS_MACOS:
        # We want mac address on macOS
        scanner_kwargs["cb"] = {"use_bdaddr": True}
    _LOGGER.debug("Initializing bluetooth scanner with %s", scanner_kwargs)

    try:
        return OriginalBleakScanner(**scanner_kwargs)
    except (FileNotFoundError, BleakError) as ex:
        raise RuntimeError(f"Failed to initialize Bluetooth: {ex}") from ex


def _error_indicates_reset_needed(error_str: str) -> bool:
    """Return if the error indicates a reset is needed."""
    return any(
        needs_reset_error in error_str for needs_reset_error in NEED_RESET_ERRORS
    )


def _error_indicates_wait_for_adapter_to_init(error_str: str) -> bool:
    """Return if the error indicates the adapter is still initializing."""
    return any(
        wait_error in error_str for wait_error in WAIT_FOR_ADAPTER_TO_INIT_ERRORS
    )


class HaScanner(BaseHaScanner):
    """
    Operate and automatically recover a BleakScanner.

    Multiple BleakScanner can be used at the same time
    if there are multiple adapters. This is only useful
    if the adapters are not located physically next to each other.

    Example use cases are usbip, a long extension cable, usb to bluetooth
    over ethernet, usb over ethernet, etc.
    """

    def __init__(
        self,
        mode: BluetoothScanningMode,
        adapter: str,
        address: str,
    ) -> None:
        """Init bluetooth discovery."""
        self.mac_address = address
        source = address if address != DEFAULT_ADDRESS else adapter or SOURCE_LOCAL
        super().__init__(source, adapter)
        self.connectable = True
        self.requested_mode = mode
        self._start_stop_lock = asyncio.Lock()
        self.scanning = False
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self.scanner: bleak.BleakScanner | None = None
        self._start_future: asyncio.Future[None] | None = None
        self.current_mode: BluetoothScanningMode | None = None

    def _create_background_task(self, coro: Coroutine[Any, Any, None]) -> None:
        """Create a background task and add it to the background tasks set."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    @property
    def discovered_devices(self) -> list[BLEDevice]:
        """Return a list of discovered devices."""
        if not self.scanner:
            return []
        return self.scanner.discovered_devices

    @property
    def discovered_devices_and_advertisement_data(
        self,
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """Return a list of discovered devices and advertisement data."""
        if not self.scanner:
            return {}
        return self.scanner.discovered_devices_and_advertisement_data

    @property
    def discovered_addresses(self) -> Iterable[str]:
        """Return an iterable of discovered devices."""
        return self.discovered_devices_and_advertisement_data

    def get_discovered_device_advertisement_data(
        self, address: str
    ) -> tuple[BLEDevice, AdvertisementData] | None:
        """Return the advertisement data for a discovered device."""
        return self.discovered_devices_and_advertisement_data.get(address)

    def async_setup(self) -> CALLBACK_TYPE:
        """Set up the scanner."""
        super().async_setup()
        return self._unsetup

    async def async_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic information about the scanner."""
        base_diag = await super().async_diagnostics()
        return base_diag | {
            "adapter": self.adapter,
            "requested_mode": self.requested_mode,
            "current_mode": self.current_mode,
        }

    def _async_detection_callback(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> None:
        """
        Call the callback when an advertisement is received.

        Currently this is used to feed the callbacks into the
        central manager.
        """
        callback_time = monotonic_time_coarse()
        address = device.address
        local_name = advertisement_data.local_name
        manufacturer_data = advertisement_data.manufacturer_data
        service_data = advertisement_data.service_data
        service_uuids = advertisement_data.service_uuids
        if local_name or manufacturer_data or service_data or service_uuids:
            # Don't count empty advertisements
            # as the adapter is in a failure
            # state if all the data is empty.
            self._last_detection = callback_time
        name = local_name or device.name or address
        if name is not None and type(name) is not str:
            name = str(name)
        tx_power = advertisement_data.tx_power
        if tx_power is not None and type(tx_power) is not int:
            tx_power = int(tx_power)
        service_info = BluetoothServiceInfoBleak.__new__(BluetoothServiceInfoBleak)
        service_info.name = name
        service_info.address = address
        service_info.rssi = advertisement_data.rssi
        service_info.manufacturer_data = manufacturer_data
        service_info.service_data = service_data
        service_info.service_uuids = service_uuids
        service_info.source = self.source
        service_info.device = device
        service_info._advertisement = advertisement_data
        service_info.connectable = True
        service_info.time = callback_time
        service_info.tx_power = tx_power
        self._manager.scanner_adv_received(service_info)

    async def async_start(self) -> None:
        """Start bluetooth scanner."""
        async with self._start_stop_lock:
            await self._async_start()

    async def _async_start(self) -> None:
        """Start bluetooth scanner under the lock."""
        for attempt in range(1, START_ATTEMPTS + 1):
            if await self._async_start_attempt(attempt):
                # Everything is fine, break out of the loop
                break
        await self._async_on_successful_start()

    async def _async_on_successful_start(self) -> None:
        """Run when the scanner has successfully started."""
        self.scanning = True
        self._async_setup_scanner_watchdog()
        await restore_discoveries(self.scanner, self.adapter)

    async def _async_start_attempt(self, attempt: int) -> bool:
        """Start the scanner and handle errors."""
        assert (  # noqa: S101
            self._loop is not None
        ), "Loop is not set, call async_setup first"

        self.current_mode = self.requested_mode
        # 1st attempt - no auto reset
        # 2nd attempt - try to reset the adapter and wait a bit
        # 3th attempt - no auto reset
        # 4th attempt - fallback to passive if available

        if (
            IS_LINUX
            and attempt == START_ATTEMPTS
            and self.requested_mode is BluetoothScanningMode.ACTIVE
        ):
            _LOGGER.debug(
                "%s: Falling back to passive scanning mode "
                "after active scanning failed (%s/%s)",
                self.name,
                attempt,
                START_ATTEMPTS,
            )
            self.current_mode = BluetoothScanningMode.PASSIVE

        self.scanner = create_bleak_scanner(
            self._async_detection_callback, self.current_mode, self.adapter
        )
        self._log_start_attempt(attempt)
        self._start_future = self._loop.create_future()
        try:
            async with asyncio.timeout(START_TIMEOUT), async_interrupt.interrupt(
                self._start_future, _AbortStartError, None
            ):
                await self.scanner.start()
        except _AbortStartError as ex:
            await self._async_stop_scanner()
            self._raise_for_abort_start(ex)
        except InvalidMessageError as ex:
            await self._async_stop_scanner()
            self._raise_for_invalid_dbus_message(ex)
        except BrokenPipeError as ex:
            await self._async_stop_scanner()
            self._raise_for_broken_pipe_error(ex)
        except FileNotFoundError as ex:
            await self._async_stop_scanner()
            self._raise_for_file_not_found_error(ex)
        except asyncio.TimeoutError as ex:
            await self._async_stop_scanner()
            if attempt == 2:
                await self._async_reset_adapter()
            if attempt < START_ATTEMPTS:
                self._log_start_timeout(attempt)
                return False
            raise ScannerStartError(
                f"{self.name}: Timed out starting Bluetooth after"
                f" {START_TIMEOUT} seconds; "
                "Try power cycling the Bluetooth hardware."
            ) from ex
        except BleakError as ex:
            await self._async_stop_scanner()
            error_str = str(ex)
            if attempt == 2 and _error_indicates_reset_needed(error_str):
                await self._async_reset_adapter()
            elif (
                attempt != START_ATTEMPTS
                and _error_indicates_wait_for_adapter_to_init(error_str)
            ):
                # If we are not out of retry attempts, and the
                # adapter is still initializing, wait a bit and try again.
                self._log_adapter_init_wait(attempt)
                await asyncio.sleep(ADAPTER_INIT_TIME)
            if attempt < START_ATTEMPTS:
                self._log_start_failed(ex, attempt)
                return False
            raise ScannerStartError(
                f"{self.name}: Failed to start Bluetooth: {ex}; "
                "Try power cycling the Bluetooth hardware."
            ) from ex
        except BaseException:
            await self._async_stop_scanner()
            raise
        finally:
            self._start_future = None

        self._log_start_success(attempt)
        return True

    def _log_adapter_init_wait(self, attempt: int) -> None:
        _LOGGER.debug(
            "%s: Waiting for adapter to initialize; attempt (%s/%s)",
            self.name,
            attempt,
            START_ATTEMPTS,
        )

    def _log_start_success(self, attempt: int) -> None:
        if self.current_mode is not self.requested_mode:
            _LOGGER.warning(
                "%s: Successful fall-back to passive scanning mode "
                "after active scanning failed (%s/%s)",
                self.name,
                attempt,
                START_ATTEMPTS,
            )
        _LOGGER.debug(
            "%s: Success while starting bluetooth; attempt: (%s/%s)",
            self.name,
            attempt,
            START_ATTEMPTS,
        )

    def _log_start_timeout(self, attempt: int) -> None:
        _LOGGER.debug(
            "%s: TimeoutError while starting bluetooth; attempt: (%s/%s)",
            self.name,
            attempt,
            START_ATTEMPTS,
        )

    def _log_start_failed(self, ex: BleakError, attempt: int) -> None:
        _LOGGER.debug(
            "%s: BleakError while starting bluetooth; attempt: (%s/%s): %s",
            self.name,
            attempt,
            START_ATTEMPTS,
            ex,
            exc_info=True,
        )

    def _log_start_attempt(self, attempt: int) -> None:
        _LOGGER.debug(
            "%s: Starting bluetooth discovery attempt: (%s/%s)",
            self.name,
            attempt,
            START_ATTEMPTS,
        )

    def _raise_for_abort_start(self, ex: _AbortStartError) -> None:
        _LOGGER.debug(
            "%s: Starting bluetooth scanner aborted: %s",
            self.name,
            ex,
            exc_info=True,
        )
        msg = f"{self.name}: Starting bluetooth scanner aborted"
        raise ScannerStartError(msg) from ex

    def _raise_for_file_not_found_error(self, ex: FileNotFoundError) -> None:
        _LOGGER.debug(
            "%s: FileNotFoundError while starting bluetooth: %s",
            self.name,
            ex,
            exc_info=True,
        )
        if is_docker_env():
            raise ScannerStartError(
                f"{self.name}: DBus service not found; docker config may "
                "be missing `-v /run/dbus:/run/dbus:ro`: {ex}"
            ) from ex
        raise ScannerStartError(
            f"{self.name}: DBus service not found; make sure the DBus socket "
            f"is available: {ex}"
        ) from ex

    def _raise_for_broken_pipe_error(self, ex: BrokenPipeError) -> None:
        """Raise a ScannerStartError for a BrokenPipeError."""
        _LOGGER.debug("%s: DBus connection broken: %s", self.name, ex, exc_info=True)
        if is_docker_env():
            msg = (
                f"{self.name}: DBus connection broken: {ex}; try restarting "
                "`bluetooth`, `dbus`, and finally the docker container"
            )
        else:
            msg = (
                f"{self.name}: DBus connection broken: {ex}; try restarting "
                "`bluetooth` and `dbus`"
            )
        raise ScannerStartError(msg) from ex

    def _raise_for_invalid_dbus_message(self, ex: InvalidMessageError) -> None:
        """Raise a ScannerStartError for an InvalidMessageError."""
        _LOGGER.debug(
            "%s: Invalid DBus message received: %s",
            self.name,
            ex,
            exc_info=True,
        )
        msg = (
            f"{self.name}: Invalid DBus message received: {ex}; "
            "try restarting `dbus`"
        )
        raise ScannerStartError(msg) from ex

    def _async_scanner_watchdog(self) -> None:
        """Check if the scanner is running."""
        if not self._async_watchdog_triggered():
            return
        if self._start_stop_lock.locked():
            _LOGGER.debug(
                "%s: Scanner is already restarting, deferring restart",
                self.name,
            )
            return
        _LOGGER.info(
            "%s: Bluetooth scanner has gone quiet for %ss, restarting",
            self.name,
            SCANNER_WATCHDOG_TIMEOUT,
        )
        # Immediately mark the scanner as not scanning
        # since the restart task will have to wait for the lock
        self.scanning = False
        self._create_background_task(self._async_restart_scanner())

    async def _async_restart_scanner(self) -> None:
        """Restart the scanner."""
        async with self._start_stop_lock:
            time_since_last_detection = monotonic_time_coarse() - self._last_detection
            # Stop the scanner but not the watchdog
            # since we want to try again later if it's still quiet
            await self._async_stop_scanner()
            # If there have not been any valid advertisements,
            # or the watchdog has hit the failure path multiple times,
            # do the reset.
            if (
                self._start_time == self._last_detection
                or time_since_last_detection > SCANNER_WATCHDOG_MULTIPLE
            ):
                await self._async_reset_adapter()
            try:
                await self._async_start()
            except ScannerStartError as ex:
                _LOGGER.exception(
                    "%s: Failed to restart Bluetooth scanner: %s",
                    self.name,
                    ex,
                )

    async def _async_reset_adapter(self) -> None:
        """Reset the adapter."""
        # There is currently nothing the user can do to fix this
        # so we log at debug level. If we later come up with a repair
        # strategy, we will change this to raise a repair issue as well.
        _LOGGER.debug("%s: adapter stopped responding; executing reset", self.name)
        result = await async_reset_adapter(self.adapter, self.mac_address)
        _LOGGER.debug("%s: adapter reset result: %s", self.name, result)

    async def async_stop(self) -> None:
        """Stop bluetooth scanner."""
        if self._start_future is not None and not self._start_future.done():
            self._start_future.set_exception(_AbortStartError())
        async with self._start_stop_lock:
            self._async_stop_scanner_watchdog()
            await self._async_stop_scanner()

    async def _async_stop_scanner(self) -> None:
        """Stop bluetooth discovery under the lock."""
        self.scanning = False
        if self.scanner is None:
            _LOGGER.debug("%s: Scanner is already stopped", self.name)
            return
        _LOGGER.debug("%s: Stopping bluetooth discovery", self.name)
        try:
            async with asyncio.timeout(STOP_TIMEOUT):
                await self.scanner.stop()
        except (asyncio.TimeoutError, BleakError) as ex:
            # This is not fatal, and they may want to reload
            # the config entry to restart the scanner if they
            # change the bluetooth dongle.
            _LOGGER.error("%s: Error stopping scanner: %s", self.name, ex)
        self.scanner = None
