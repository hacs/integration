from __future__ import annotations

import contextlib

from bleak.backends.bluezdbus import defs
from bleak.backends.device import BLEDevice
from dbus_fast.message import Message

from .bleak_manager import get_global_bluez_manager_with_timeout
from .const import DISCONNECT_TIMEOUT
from .util import asyncio_timeout


async def disconnect_devices(devices: list[BLEDevice]) -> None:
    """Disconnect a list of devices."""
    valid_devices = [
        device
        for device in devices
        if isinstance(device.details, dict) and "path" in device.details
    ]
    if not valid_devices:
        return
    if not (bluez_manager := await get_global_bluez_manager_with_timeout()):
        return
    bus = bluez_manager._bus
    for device in valid_devices:
        # https://bleak.readthedocs.io/en/latest/troubleshooting.html#id4
        # Try to remove the device as well in the hope that it will
        # clear the disk cache of the device.
        with contextlib.suppress(Exception):
            async with asyncio_timeout(DISCONNECT_TIMEOUT):
                await bus.call(
                    Message(
                        destination=defs.BLUEZ_SERVICE,
                        path=device.details["path"],
                        interface=defs.DEVICE_INTERFACE,
                        member="Disconnect",
                    )
                )
