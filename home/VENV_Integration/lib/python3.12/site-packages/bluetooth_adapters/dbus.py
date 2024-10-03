from __future__ import annotations

import asyncio
import logging
from functools import cache
from pathlib import Path
from typing import Any

try:
    from dbus_fast import AuthError, BusType, Message, MessageType, unpack_variants
    from dbus_fast.aio import MessageBus
except (AttributeError, ImportError):
    # dbus_fast is not available on Windows
    AuthError = None  # pragma: no cover
    BusType = None  # pragma: no cover
    Message = None  # pragma: no cover
    MessageType = None  # pragma: no cover
    unpack_variants = None  # pragma: no cover
    MessageBus = None  # pragma: no cover


from .history import AdvertisementHistory, load_history_from_managed_objects
from .util import asyncio_timeout

_LOGGER = logging.getLogger(__name__)

REPLY_TIMEOUT = 8


class BlueZDBusObjects:
    """Fetch and parse BlueZObjects."""

    def __init__(self) -> None:
        """Init the manager."""
        self._packed_managed_objects: dict[str, Any] = {}
        self._unpacked_managed_objects: dict[str, Any] = {}

    async def load(self) -> None:
        """Load from the bus."""
        self._packed_managed_objects = await _get_dbus_managed_objects()
        self._unpacked_managed_objects = {}

    @property
    def adapters(self) -> list[str]:
        """Get adapters."""
        return list(self.adapter_details)

    @property
    def unpacked_managed_objects(self) -> dict[str, Any]:
        """Get unpacked managed objects."""
        if not self._unpacked_managed_objects:
            self._unpacked_managed_objects = unpack_variants(
                self._packed_managed_objects
            )
        return self._unpacked_managed_objects

    @property
    def adapter_details(self) -> dict[str, dict[str, Any]]:
        """Get adapters."""
        return _adapters_from_managed_objects(self.unpacked_managed_objects)

    @property
    def history(self) -> dict[str, AdvertisementHistory]:
        """Get history from managed objects."""
        return load_history_from_managed_objects(self.unpacked_managed_objects)


def _adapters_from_managed_objects(
    managed_objects: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    adapters: dict[str, dict[str, Any]] = {}
    for path, unpacked_data in managed_objects.items():
        path_str = str(path)
        if path_str.startswith("/org/bluez/hci"):
            split_path = path_str.split("/")
            adapter = split_path[3]
            if adapter not in adapters:
                adapters[adapter] = unpacked_data
    return adapters


async def get_bluetooth_adapters() -> list[str]:
    """Return a list of bluetooth adapters."""
    return list(await get_bluetooth_adapter_details())


async def get_bluetooth_adapter_details() -> dict[str, dict[str, Any]]:
    """Return a list of bluetooth adapter with details."""
    results = await _get_dbus_managed_objects()
    return {
        adapter: unpack_variants(packed_data)
        for adapter, packed_data in _adapters_from_managed_objects(results).items()
    }


async def get_dbus_managed_objects() -> dict[str, Any]:
    """Return a list of bluetooth adapter with details."""
    results = await _get_dbus_managed_objects()
    return {path: unpack_variants(packed_data) for path, packed_data in results.items()}


async def _get_dbus_managed_objects() -> dict[str, Any]:
    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    except AuthError as ex:
        _LOGGER.warning(
            "DBus authentication error; make sure the DBus socket "
            "is available and the user has the correct permissions: %s",
            ex,
        )
        return {}
    except FileNotFoundError as ex:
        if is_docker_env():
            _LOGGER.debug(
                "DBus service not found; docker config may "
                "be missing `-v /run/dbus:/run/dbus:ro`: %s",
                ex,
            )
        _LOGGER.debug(
            "DBus service not found; make sure the DBus socket " "is available: %s",
            ex,
        )
        return {}
    except BrokenPipeError as ex:
        if is_docker_env():
            _LOGGER.debug(
                "DBus connection broken: %s; try restarting "
                "`bluetooth`, `dbus`, and finally the docker container",
                ex,
            )
        _LOGGER.debug(
            "DBus connection broken: %s; try restarting " "`bluetooth` and `dbus`", ex
        )
        return {}
    except ConnectionRefusedError as ex:
        if is_docker_env():
            _LOGGER.debug(
                "DBus connection refused: %s; try restarting "
                "`bluetooth`, `dbus`, and finally the docker container",
                ex,
            )
        _LOGGER.debug(
            "DBus connection refused: %s; try restarting " "`bluetooth` and `dbus`", ex
        )
        return {}
    msg = Message(
        destination="org.bluez",
        path="/",
        interface="org.freedesktop.DBus.ObjectManager",
        member="GetManagedObjects",
    )
    try:
        async with asyncio_timeout(REPLY_TIMEOUT):
            reply = await bus.call(msg)
    except EOFError as ex:
        _LOGGER.debug("DBus connection closed: %s", ex)
        return {}
    except asyncio.TimeoutError:
        _LOGGER.debug(
            "Dbus timeout waiting for reply to GetManagedObjects; try restarting "
            "`bluetooth` and `dbus`"
        )
        return {}
    bus.disconnect()
    if not reply or reply.message_type != MessageType.METHOD_RETURN:
        _LOGGER.debug(
            "Received an unexpected reply from Dbus while "
            "calling GetManagedObjects on org.bluez: %s",
            reply,
        )
        return {}
    results: dict[str, Any] = reply.body[0]
    return results


@cache
def is_docker_env() -> bool:
    """Return True if we run in a docker env."""
    return Path("/.dockerenv").exists()
