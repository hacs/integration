# -*- coding: utf-8 -*-
"""async_upnp_client.device_updater module."""

import logging
from typing import Optional

from async_upnp_client.advertisement import SsdpAdvertisementListener
from async_upnp_client.client import UpnpDevice
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.const import AddressTupleVXType
from async_upnp_client.utils import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)


class DeviceUpdater:
    """
    Device updater.

    Listens for SSDP advertisements and updates device inline when needed.
    Inline meaning that it keeps the original UpnpDevice instance.
    So be sure to keep only references to the UpnpDevice,
    as a device might decide to remove a service after an update!
    """

    def __init__(
        self,
        device: UpnpDevice,
        factory: UpnpFactory,
        source: Optional[AddressTupleVXType] = None,
    ) -> None:
        """Initialize."""
        self._device = device
        self._factory = factory
        self._listener = SsdpAdvertisementListener(
            async_on_alive=self._async_on_alive,
            async_on_byebye=self._async_on_byebye,
            async_on_update=self._async_on_update,
            source=source,
        )

    async def async_start(self) -> None:
        """Start listening for notifications."""
        _LOGGER.debug("Start listening for notifications.")
        await self._listener.async_start()

    async def async_stop(self) -> None:
        """Stop listening for notifications."""
        _LOGGER.debug("Stop listening for notifications.")
        await self._listener.async_stop()

    async def _async_on_alive(self, headers: CaseInsensitiveDict) -> None:
        """Handle on alive."""
        # Ensure for root devices only.
        if headers.get("nt") != "upnp:rootdevice":
            return

        # Ensure for our device.
        if headers.get("_udn") != self._device.udn:
            return

        _LOGGER.debug("Handling alive: %s", headers)
        await self._async_handle_alive_update(headers)

    async def _async_on_byebye(self, headers: CaseInsensitiveDict) -> None:
        """Handle on byebye."""
        _LOGGER.debug("Handling on_byebye: %s", headers)
        self._device.available = False

    async def _async_on_update(self, headers: CaseInsensitiveDict) -> None:
        """Handle on update."""
        # Ensure for root devices only.
        if headers.get("nt") != "upnp:rootdevice":
            return

        # Ensure for our device.
        if headers.get("_udn") != self._device.udn:
            return

        _LOGGER.debug("Handling update: %s", headers)
        await self._async_handle_alive_update(headers)

    async def _async_handle_alive_update(self, headers: CaseInsensitiveDict) -> None:
        """Handle on_alive or on_update."""
        do_reinit = False

        # Handle BOOTID.UPNP.ORG.
        boot_id = headers.get("BOOTID.UPNP.ORG")
        device_boot_id = self._device.ssdp_headers.get("BOOTID.UPNP.ORG")
        if boot_id and boot_id != device_boot_id:
            _LOGGER.debug("New boot_id: %s, old boot_id: %s", boot_id, device_boot_id)
            do_reinit = True

        # Handle CONFIGID.UPNP.ORG.
        config_id = headers.get("CONFIGID.UPNP.ORG")
        device_config_id = self._device.ssdp_headers.get("CONFIGID.UPNP.ORG")
        if config_id and config_id != device_config_id:
            _LOGGER.debug(
                "New config_id: %s, old config_id: %s",
                config_id,
                device_config_id,
            )
            do_reinit = True

        # Handle LOCATION.
        location = headers.get("LOCATION")
        if location and self._device.device_url != location:
            _LOGGER.debug(
                "New location: %s, old location: %s", location, self._device.device_url
            )
            do_reinit = True

        if location and do_reinit:
            await self._reinit_device(location, headers)

        # We heard from it, so mark it available.
        self._device.available = True

    async def _reinit_device(
        self, location: str, ssdp_headers: CaseInsensitiveDict
    ) -> None:
        """Reinitialize device."""
        # pylint: disable=protected-access
        _LOGGER.debug("Reinitializing device, location: %s", location)

        new_device = await self._factory.async_create_device(location)
        self._device.reinit(new_device)
        self._device.ssdp_headers = ssdp_headers
