from __future__ import annotations

__version__ = "3.5.0"


import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakDBusError, BleakDeviceNotFoundError, BleakError

from .bluez import (  # noqa: F401
    BleakSlotManager,
    _get_properties,
    clear_cache,
    device_source,
    get_connected_devices,
    get_device,
    get_device_by_adapter,
    wait_for_device_to_reappear,
    wait_for_disconnect,
)
from .const import IS_LINUX, NO_RSSI_VALUE, RSSI_SWITCH_THRESHOLD
from .util import asyncio_timeout

DISCONNECT_TIMEOUT = 5

DEFAULT_ATTEMPTS = 2

if IS_LINUX:
    from bluetooth_adapters import load_history_from_managed_objects

    from .dbus import disconnect_devices
else:
    load_history_from_managed_objects = None
    disconnect_devices = None  # type: ignore[assignment]


# Make sure bleak and dbus-fast have time
# to run their cleanup callbacks or the
# retry call will just fail in the same way.
BLEAK_TRANSIENT_BACKOFF_TIME = 0.25
BLEAK_TRANSIENT_MEDIUM_BACKOFF_TIME = 0.50
BLEAK_TRANSIENT_LONG_BACKOFF_TIME = 1.0
BLEAK_DBUS_BACKOFF_TIME = 0.25
BLEAK_OUT_OF_SLOTS_BACKOFF_TIME = 4.00
BLEAK_BACKOFF_TIME = 0.1
# Expected disconnect or ran out of slots
# after checking, don't backoff since we
# want to retry immediately.
BLEAK_DISCONNECTED_BACKOFF_TIME = 0.0


__all__ = [
    "BleakSlotManager",  # Currently only possible for BlueZ, for MacOS we have no of knowing
    "ble_device_description",
    "establish_connection",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "clear_cache",
    "get_device",
    "get_device_by_adapter",
    "device_source",
    "restore_discoveries",
    "retry_bluetooth_connection_error",
    "BleakClientWithServiceCache",
    "BleakAbortedError",
    "BleakNotFoundError",
    "BLEAK_RETRY_EXCEPTIONS",
    "RSSI_SWITCH_THRESHOLD",
    "NO_RSSI_VALUE",
]


BLEAK_EXCEPTIONS = (AttributeError, BleakError)
BLEAK_RETRY_EXCEPTIONS = (
    *BLEAK_EXCEPTIONS,
    EOFError,
    BrokenPipeError,
    asyncio.TimeoutError,
)

_LOGGER = logging.getLogger(__name__)

MAX_TRANSIENT_ERRORS = 9

# Shorter time outs and more attempts
# seems to be better for dbus, and corebluetooth
# is happy either way. Ideally we want everything
# to finish in < 60s or declare we cannot connect

MAX_CONNECT_ATTEMPTS = 4
BLEAK_TIMEOUT = 20.0

# Bleak may not always timeout
# since the dbus connection can stall
# so we have an additional timeout to
# be sure we do not block forever
# This is likely fixed in https://github.com/hbldh/bleak/pull/1092
#
# This also accounts for the time it
# takes for the esp32s to disconnect
#
BLEAK_SAFETY_TIMEOUT = 60.0

TRANSIENT_ERRORS_LONG_BACKOFF = {
    "ESP_GATT_ERROR",
}

TRANSIENT_ERRORS_MEDIUM_BACKOFF = {
    "ESP_GATT_CONN_TIMEOUT",
    "ESP_GATT_CONN_FAIL_ESTABLISH",
}

DEVICE_MISSING_ERRORS = {"org.freedesktop.DBus.Error.UnknownObject"}

OUT_OF_SLOTS_ERRORS = {"available connection", "connection slot"}

TRANSIENT_ERRORS = {
    "le-connection-abort-by-local",
    "br-connection-canceled",
    "ESP_GATT_CONN_FAIL_ESTABLISH",
    "ESP_GATT_CONN_TERMINATE_PEER_USER",
    "ESP_GATT_CONN_TERMINATE_LOCAL_HOST",
    "ESP_GATT_CONN_CONN_CANCEL",
} | OUT_OF_SLOTS_ERRORS

# Currently the same as transient error
ABORT_ERRORS = (
    TRANSIENT_ERRORS | TRANSIENT_ERRORS_MEDIUM_BACKOFF | TRANSIENT_ERRORS_LONG_BACKOFF
)


ABORT_ADVICE = (
    "Interference/range; "
    "External Bluetooth adapter w/extension may help; "
    "Extension cables reduce USB 3 port interference"
)

DEVICE_MISSING_ADVICE = (
    "The device disappeared; " "Try restarting the scanner or moving the device closer"
)

OUT_OF_SLOTS_ADVICE = (
    "The proxy/adapter is out of connection slots or the device is no longer reachable; "
    "Add additional proxies (https://esphome.github.io/bluetooth-proxies/) near this device"
)

NORMAL_DISCONNECT = "Disconnected"


class BleakNotFoundError(BleakError):
    """The device was not found."""


class BleakConnectionError(BleakError):
    """The device was not found."""


class BleakAbortedError(BleakError):
    """The connection was aborted."""


class BleakOutOfConnectionSlotsError(BleakError):
    """The proxy/adapter is out of connection slots."""


class BleakClientWithServiceCache(BleakClient):
    """A BleakClient that implements service caching."""

    def set_cached_services(self, services: BleakGATTServiceCollection | None) -> None:
        """Set the cached services.

        No longer used since bleak 0.17+ has service caching built-in.

        This was only kept for backwards compatibility.
        """

    async def clear_cache(self) -> bool:
        """Clear the cached services."""
        if hasattr(super(), "clear_cache"):
            return await super().clear_cache()
        _LOGGER.warning("clear_cache not implemented in bleak version")
        return False


def ble_device_has_changed(original: BLEDevice, new: BLEDevice) -> bool:
    """Check if the device has changed."""
    return bool(
        original.address != new.address
        or (
            isinstance(original.details, dict)
            and isinstance(new.details, dict)
            and "path" in original.details
            and "path" in new.details
            and original.details["path"] != new.details["path"]
        )
    )


def ble_device_description(device: BLEDevice) -> str:
    """Get the device description."""
    details = device.details
    address = device.address
    name = device.name
    if name != address:
        base_name = f"{address} - {name}"
    else:
        base_name = address
    if isinstance(details, dict):
        if path := details.get("path"):
            # /org/bluez/hci2
            return f"{base_name} -> {path[0:15]}"
        if source := details.get("source"):
            return f"{base_name} -> {source}"
    return base_name


def calculate_backoff_time(exc: Exception) -> float:
    """Calculate the backoff time based on the exception."""

    if isinstance(
        exc, (BleakDBusError, EOFError, asyncio.TimeoutError, BrokenPipeError)
    ):
        return BLEAK_DBUS_BACKOFF_TIME
    # If the adapter runs out of slots can get a BleakDeviceNotFoundError
    # since the device is no longer visible on the adapter. Almost none of
    # the adapters document how many connection slots they have so we cannot
    # know if we are out of slots or not. We can only guess based on the
    # error message and backoff.
    if isinstance(exc, (BleakDeviceNotFoundError, BleakNotFoundError)):
        return BLEAK_OUT_OF_SLOTS_BACKOFF_TIME
    if isinstance(exc, BleakError):
        bleak_error = str(exc)
        if any(error in bleak_error for error in OUT_OF_SLOTS_ERRORS):
            return BLEAK_OUT_OF_SLOTS_BACKOFF_TIME
        if any(error in bleak_error for error in TRANSIENT_ERRORS_MEDIUM_BACKOFF):
            return BLEAK_TRANSIENT_MEDIUM_BACKOFF_TIME
        if any(error in bleak_error for error in TRANSIENT_ERRORS_LONG_BACKOFF):
            return BLEAK_TRANSIENT_LONG_BACKOFF_TIME
        if any(error in bleak_error for error in TRANSIENT_ERRORS):
            return BLEAK_TRANSIENT_BACKOFF_TIME
        if NORMAL_DISCONNECT in bleak_error:
            return BLEAK_DISCONNECTED_BACKOFF_TIME
    return BLEAK_BACKOFF_TIME


async def _disconnect_devices(devices: list[BLEDevice]) -> None:
    """Disconnect the devices."""
    if IS_LINUX:
        await disconnect_devices(devices)


async def close_stale_connections_by_address(
    address: str, only_other_adapters: bool = False
) -> None:
    """Close stale connections by address."""
    if not IS_LINUX or not (device := await get_device(address)):
        return
    await close_stale_connections(device, only_other_adapters)


async def close_stale_connections(
    device: BLEDevice, only_other_adapters: bool = False
) -> None:
    """Close stale connections."""
    if not IS_LINUX or not (devices := await get_connected_devices(device)):
        return
    to_disconnect: list[BLEDevice] = []
    for connected_device in devices:
        if only_other_adapters and not ble_device_has_changed(connected_device, device):
            _LOGGER.debug(
                "%s - %s: unexpectedly connected, not disconnecting since only_other_adapters is set",
                connected_device.name,
                connected_device.address,
            )
        else:
            _LOGGER.debug(
                "%s - %s: unexpectedly connected, disconnecting",
                connected_device.name,
                connected_device.address,
            )
            to_disconnect.append(connected_device)

    if not to_disconnect:
        return
    await _disconnect_devices(to_disconnect)


AnyBleakClient = TypeVar("AnyBleakClient", bound=BleakClient)


async def establish_connection(
    client_class: type[AnyBleakClient],
    device: BLEDevice,
    name: str,
    disconnected_callback: Callable[[AnyBleakClient], None] | None = None,
    max_attempts: int = MAX_CONNECT_ATTEMPTS,
    cached_services: BleakGATTServiceCollection | None = None,
    ble_device_callback: Callable[[], BLEDevice] | None = None,
    use_services_cache: bool = True,
    **kwargs: Any,
) -> AnyBleakClient:
    """Establish a connection to the device."""
    timeouts = 0
    connect_errors = 0
    transient_errors = 0
    attempt = 0

    def _raise_if_needed(name: str, description: str, exc: Exception) -> None:
        """Raise if we reach the max attempts."""
        if (
            timeouts + connect_errors < max_attempts
            and transient_errors < MAX_TRANSIENT_ERRORS
        ):
            return
        msg = (
            f"{name} - {description}: Failed to connect after "
            f"{attempt} attempt(s): {str(exc) or type(exc).__name__}"
        )
        # Sure would be nice if bleak gave us typed exceptions
        if isinstance(exc, asyncio.TimeoutError):
            raise BleakNotFoundError(msg) from exc
        if isinstance(exc, BleakDeviceNotFoundError) or "not found" in str(exc):
            raise BleakNotFoundError(f"{msg}: {DEVICE_MISSING_ADVICE}") from exc
        if isinstance(exc, BleakError):
            if any(error in str(exc) for error in OUT_OF_SLOTS_ERRORS):
                raise BleakOutOfConnectionSlotsError(
                    f"{msg}: {OUT_OF_SLOTS_ADVICE}"
                ) from exc
            if any(error in str(exc) for error in ABORT_ERRORS):
                raise BleakAbortedError(f"{msg}: {ABORT_ADVICE}") from exc
            if any(error in str(exc) for error in DEVICE_MISSING_ERRORS):
                raise BleakNotFoundError(f"{msg}: {DEVICE_MISSING_ADVICE}") from exc
        raise BleakConnectionError(msg) from exc

    debug_enabled = _LOGGER.isEnabledFor(logging.DEBUG)
    rssi: int | None = None
    if IS_LINUX and (devices := await get_connected_devices(device)):
        # Bleak 0.17 will handle already connected devices for us so
        # if we are already connected we swap the device to the connected
        # device.
        device = devices[0]

    client = client_class(device, disconnected_callback=disconnected_callback, **kwargs)

    while True:
        attempt += 1
        if debug_enabled:
            _LOGGER.debug(
                "%s - %s: Connection attempt: %s",
                name,
                device.address,
                attempt,
            )

        try:
            async with asyncio_timeout(BLEAK_SAFETY_TIMEOUT):
                await client.connect(
                    timeout=BLEAK_TIMEOUT,
                    dangerous_use_bleak_cache=use_services_cache
                    or bool(cached_services),
                )
                if debug_enabled:
                    _LOGGER.debug(
                        "%s - %s: Connected after %s attempts",
                        name,
                        device.address,
                        attempt,
                    )
        except asyncio.TimeoutError as exc:
            timeouts += 1
            if debug_enabled:
                _LOGGER.debug(
                    "%s - %s: Timed out trying to connect (attempt: %s, last rssi: %s)",
                    name,
                    device.address,
                    attempt,
                    rssi,
                )
            backoff_time = calculate_backoff_time(exc)
            await wait_for_disconnect(device, backoff_time)
            _raise_if_needed(name, device.address, exc)
        except KeyError as exc:
            # Likely: KeyError: 'org.bluez.GattService1' from bleak
            # ideally we would get a better error from bleak, but this is
            # better than nothing.
            # self._properties[service_path][defs.GATT_SERVICE_INTERFACE]
            transient_errors += 1
            if debug_enabled:
                _LOGGER.debug(
                    "%s - %s: Failed to connect due to services changes: %s (attempt: %s, last rssi: %s)",
                    name,
                    device.address,
                    str(exc),
                    attempt,
                    rssi,
                )
            if isinstance(client, BleakClientWithServiceCache):
                await client.clear_cache()
                await client.disconnect()
                backoff_time = calculate_backoff_time(exc)
                await wait_for_disconnect(device, backoff_time)
            _raise_if_needed(name, device.address, exc)
        except BrokenPipeError as exc:
            # BrokenPipeError is raised by dbus-next when the device disconnects
            #
            # bleak.exc.BleakDBusError: [org.bluez.Error] le-connection-abort-by-local
            # During handling of the above exception, another exception occurred:
            # Traceback (most recent call last):
            # File "bleak/backends/bluezdbus/client.py", line 177, in connect
            #   reply = await self._bus.call(
            # File "dbus_next/aio/message_bus.py", line 63, in write_callback
            #   self.offset += self.sock.send(self.buf[self.offset:])
            # BrokenPipeError: [Errno 32] Broken pipe
            transient_errors += 1
            if debug_enabled:
                _LOGGER.debug(
                    "%s - %s: Failed to connect: %s (attempt: %s, last rssi: %s)",
                    name,
                    device.address,
                    str(exc),
                    attempt,
                    rssi,
                )
            _raise_if_needed(name, device.address, exc)
        except EOFError as exc:
            transient_errors += 1
            backoff_time = calculate_backoff_time(exc)
            if debug_enabled:
                _LOGGER.debug(
                    "%s - %s: Failed to connect: %s, backing off: %s (attempt: %s, last rssi: %s)",
                    name,
                    device.address,
                    str(exc),
                    backoff_time,
                    attempt,
                    rssi,
                )
            await wait_for_disconnect(device, backoff_time)
            _raise_if_needed(name, device.address, exc)
        except BLEAK_EXCEPTIONS as exc:
            bleak_error = str(exc)
            # BleakDeviceNotFoundError can mean that the adapter has run out of
            # connection slots.
            device_missing = isinstance(
                exc, (BleakNotFoundError, BleakDeviceNotFoundError)
            )
            if device_missing or any(
                error in bleak_error for error in TRANSIENT_ERRORS
            ):
                transient_errors += 1
            else:
                connect_errors += 1
            backoff_time = calculate_backoff_time(exc)
            if debug_enabled:
                _LOGGER.debug(
                    "%s - %s: Failed to connect: %s, device_missing: %s, backing off: %s (attempt: %s, last rssi: %s)",
                    name,
                    device.address,
                    bleak_error,
                    device_missing,
                    backoff_time,
                    attempt,
                    rssi,
                )
            await wait_for_disconnect(device, backoff_time)
            _raise_if_needed(name, device.address, exc)
        else:
            return client
        # Ensure the disconnect callback
        # has a chance to run before we try to reconnect
        await asyncio.sleep(0)

    raise RuntimeError("This should never happen")


P = ParamSpec("P")
T = TypeVar("T")


def retry_bluetooth_connection_error(
    attempts: int = DEFAULT_ATTEMPTS,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Define a wrapper to retry on bluetooth connection error."""

    def _decorator_retry_bluetooth_connection_error(
        func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[T]]:
        """Define a wrapper to retry on bleak error.

        The accessory is allowed to disconnect us any time so
        we need to retry the operation.
        """

        async def _async_wrap_bluetooth_connection_error_retry(  # type: ignore[return]
            *args: P.args, **kwargs: P.kwargs
        ) -> T:
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except BLEAK_EXCEPTIONS as ex:
                    backoff_time = calculate_backoff_time(ex)
                    if attempt == attempts - 1:
                        raise
                    _LOGGER.debug(
                        "Bleak error calling %s, backing off: %s, retrying...",
                        func,
                        backoff_time,
                        exc_info=True,
                    )
                    await asyncio.sleep(backoff_time)

        return _async_wrap_bluetooth_connection_error_retry

    return _decorator_retry_bluetooth_connection_error


async def restore_discoveries(scanner: BleakScanner, adapter: str) -> None:
    """Restore discoveries from the bus."""
    if not IS_LINUX:
        # This is only supported on Linux
        return
    if not (properties := await _get_properties()):
        _LOGGER.debug("Failed to restore discoveries for %s", adapter)
        return
    backend = scanner._backend
    before = len(backend.seen_devices)
    backend.seen_devices.update(
        {
            address: (history.device, history.advertisement_data)
            for address, history in load_history_from_managed_objects(
                properties, adapter
            ).items()
        }
    )
    _LOGGER.debug(
        "Restored %s discoveries for %s", len(backend.seen_devices) - before, adapter
    )
