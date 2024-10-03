# -*- coding: utf-8 -*-
"""async_upnp_client.ssdp_listener module."""

import asyncio
import logging
import re
from asyncio.events import AbstractEventLoop
from contextlib import suppress
from datetime import datetime, timedelta
from functools import lru_cache
from ipaddress import ip_address
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    KeysView,
    Mapping,
    Optional,
    Tuple,
)
from urllib.parse import urlparse

from async_upnp_client.advertisement import SsdpAdvertisementListener
from async_upnp_client.const import (
    AddressTupleVXType,
    DeviceOrServiceType,
    NotificationSubType,
    NotificationType,
    SearchTarget,
    SsdpSource,
    UniqueDeviceName,
)
from async_upnp_client.search import SsdpSearchListener
from async_upnp_client.ssdp import SSDP_MX, determine_source_target, udn_from_usn
from async_upnp_client.utils import CaseInsensitiveDict

_SENTINEL = object()
_LOGGER = logging.getLogger(__name__)
CACHE_CONTROL_RE = re.compile(r"max-age\s*=\s*(\d+)", re.IGNORECASE)
DEFAULT_MAX_AGE = timedelta(seconds=900)
IGNORED_HEADERS = {
    "date",
    "cache-control",
    "server",
    "host",
    "location",  # Location-header is handled differently!
}


@lru_cache(maxsize=128)
def is_valid_location(location: str) -> bool:
    """Validate if this location is usable."""
    return location.startswith("http") and not (
        "://127.0.0.1" in location or "://[::1]" in location or "://169.254" in location
    )


def valid_search_headers(headers: CaseInsensitiveDict) -> bool:
    """Validate if this search is usable."""
    return headers.lower_values_true(("_udn", "st")) and is_valid_location(
        headers.get_lower("location", "")
    )


def valid_advertisement_headers(headers: CaseInsensitiveDict) -> bool:
    """Validate if this advertisement is usable for connecting to a device."""
    return headers.lower_values_true(("_udn", "nt", "nts")) and is_valid_location(
        headers.get_lower("location", "")
    )


def valid_byebye_headers(headers: CaseInsensitiveDict) -> bool:
    """Validate if this advertisement has required headers for byebye."""
    return headers.lower_values_true(("_udn", "nt", "nts"))


@lru_cache(maxsize=128)
def extract_uncache_after(cache_control: str) -> timedelta:
    """Get uncache after from cache control header."""
    if match := CACHE_CONTROL_RE.search(cache_control):
        max_age = int(match[1])
        return timedelta(seconds=max_age)
    return DEFAULT_MAX_AGE


def extract_valid_to(headers: CaseInsensitiveDict) -> datetime:
    """Extract/create valid to."""
    uncache_after = extract_uncache_after(headers.get_lower("cache-control", ""))
    timestamp: datetime = headers.get_lower("_timestamp")
    return timestamp + uncache_after


class SsdpDevice:
    """
    SSDP Device.

    Holds all known information about the device.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, udn: str, valid_to: datetime):
        """Initialize."""
        self.udn = udn
        self.valid_to: datetime = valid_to
        self._locations: Dict[str, datetime] = {}
        self.last_seen: Optional[datetime] = None
        self.search_headers: dict[DeviceOrServiceType, CaseInsensitiveDict] = {}
        self.advertisement_headers: dict[DeviceOrServiceType, CaseInsensitiveDict] = {}
        self.userdata: Any = None

    def add_location(self, location: str, valid_to: datetime) -> None:
        """Add a (new) location the device can be reached at."""
        self._locations[location] = valid_to

    @property
    def location(self) -> Optional[str]:
        """
        Get a location of the device.

        Kept for compatibility, use method `locations`.
        """
        # Sort such that the same location will be given each time.
        for location in sorted(self.locations):
            return location

        return None

    @property
    def locations(self) -> KeysView[str]:
        """Get all know locations of the device."""
        return self._locations.keys()

    def purge_locations(self, now: Optional[datetime] = None) -> None:
        """Purge locations which are no longer valid/timed out."""
        if not now:
            now = datetime.now()
        to_remove = [
            location for location, valid_to in self._locations.items() if now > valid_to
        ]
        for location in to_remove:
            del self._locations[location]

    def combined_headers(
        self,
        device_or_service_type: DeviceOrServiceType,
    ) -> CaseInsensitiveDict:
        """Get headers from search and advertisement for a given device- or service type.

        If there are both search and advertisement headers,
        the search headers are combined with the advertisement headers and a new
        CaseInsensitiveDict is returned.

        If there are only search headers, the search headers are returned.

        If there are only advertisement headers, the advertisement headers are returned.

        If there are no headers, an empty CaseInsensitiveDict is returned.

        Callers should be aware that the returned CaseInsensitiveDict may be a view
        into the internal data structures of this class. If the caller modifies the
        returned CaseInsensitiveDict, the internal data structures will be modified
        as well.
        """
        search_headers = self.search_headers.get(device_or_service_type, _SENTINEL)
        advertisement_headers = self.advertisement_headers.get(
            device_or_service_type, _SENTINEL
        )
        if search_headers is not _SENTINEL and advertisement_headers is not _SENTINEL:
            if TYPE_CHECKING:
                assert isinstance(search_headers, CaseInsensitiveDict)
                assert isinstance(advertisement_headers, CaseInsensitiveDict)
            header_dict = search_headers.combine(advertisement_headers)
            header_dict.del_lower("_source")
            return header_dict
        if search_headers is not _SENTINEL:
            if TYPE_CHECKING:
                assert isinstance(search_headers, CaseInsensitiveDict)
            return search_headers
        if advertisement_headers is not _SENTINEL:
            if TYPE_CHECKING:
                assert isinstance(advertisement_headers, CaseInsensitiveDict)
            return advertisement_headers
        return CaseInsensitiveDict()

    @property
    def all_combined_headers(self) -> Mapping[DeviceOrServiceType, CaseInsensitiveDict]:
        """Get all headers from search and advertisement for all known device- and service types."""
        dsts = set(self.advertisement_headers).union(set(self.search_headers))
        return {dst: self.combined_headers(dst) for dst in dsts}

    def __repr__(self) -> str:
        """Return the representation."""
        return f"<{type(self).__name__}({self.udn})>"


def same_headers_differ(
    current_headers: CaseInsensitiveDict, new_headers: CaseInsensitiveDict
) -> bool:
    """Compare headers present in both to see if anything interesting has changed."""
    current_headers_dict = current_headers.as_dict()
    new_headers_dict = new_headers.as_dict()
    new_headers_case_map = new_headers.case_map()
    current_headers_case_map = current_headers.case_map()

    for lower_header, current_header in current_headers_case_map.items():
        if (
            lower_header != "" and lower_header[0] == "_"
        ) or lower_header in IGNORED_HEADERS:
            continue
        new_header = new_headers_case_map.get(lower_header, _SENTINEL)

        if new_header is not _SENTINEL:
            current_value = current_headers_dict[current_header]
            new_value = new_headers_dict[new_header]  # type: ignore[index]
            if current_value != new_value:
                _LOGGER.debug(
                    "Header %s changed from %s to %s",
                    current_header,
                    current_value,
                    new_value,
                )
                return True

    return False


def headers_differ_from_existing_advertisement(
    ssdp_device: SsdpDevice, dst: DeviceOrServiceType, headers: CaseInsensitiveDict
) -> bool:
    """Compare against existing advertisement headers to see if anything interesting has changed."""
    headers_old = ssdp_device.advertisement_headers.get(dst, _SENTINEL)
    if headers_old is _SENTINEL:
        return False
    if TYPE_CHECKING:
        assert isinstance(headers_old, CaseInsensitiveDict)
    return same_headers_differ(headers_old, headers)


def headers_differ_from_existing_search(
    ssdp_device: SsdpDevice, dst: DeviceOrServiceType, headers: CaseInsensitiveDict
) -> bool:
    """Compare against existing search headers to see if anything interesting has changed."""
    headers_old = ssdp_device.search_headers.get(dst, _SENTINEL)
    if headers_old is _SENTINEL:
        return False
    if TYPE_CHECKING:
        assert isinstance(headers_old, CaseInsensitiveDict)
    return same_headers_differ(headers_old, headers)


def ip_version_from_location(location: str) -> Optional[int]:
    """Get the ip version for a location."""
    with suppress(ValueError):
        hostname = urlparse(location).hostname
        if not hostname:
            return None

        return ip_address(hostname).version

    return None


def location_changed(ssdp_device: SsdpDevice, headers: CaseInsensitiveDict) -> bool:
    """Test if location changed for device."""
    new_location = headers.get_lower("location", "")
    if not new_location:
        return False

    # Device did not have any location, must be new.
    locations = ssdp_device.locations
    if not locations:
        return True

    if new_location in locations:
        return False

    # Ensure the new location is parsable.
    new_ip_version = ip_version_from_location(new_location)
    if new_ip_version is None:
        return False

    # We already established the location
    # was not seen before. If we have any location
    # saved that is the same ip version, we
    # consider the location changed
    return any(
        ip_version_from_location(location) == new_ip_version for location in locations
    )


class SsdpDeviceTracker:
    """
    Device tracker.

    Tracks `SsdpDevices` seen by the `SsdpListener`. Can be shared between `SsdpListeners`.
    """

    def __init__(self) -> None:
        """Initialize."""
        self.devices: dict[UniqueDeviceName, SsdpDevice] = {}
        self.next_valid_to: Optional[datetime] = None

    def see_search(
        self, headers: CaseInsensitiveDict
    ) -> Tuple[
        bool, Optional[SsdpDevice], Optional[DeviceOrServiceType], Optional[SsdpSource]
    ]:
        """See a device through a search."""
        if not valid_search_headers(headers):
            _LOGGER.debug("Received invalid search headers: %s", headers)
            return False, None, None, None

        udn = headers.get_lower("_udn")
        is_new_device = udn not in self.devices

        ssdp_device, new_location = self._see_device(headers)
        if not ssdp_device:
            return False, None, None, None

        search_target: SearchTarget = headers.get_lower("st")
        is_new_service = (
            search_target not in ssdp_device.advertisement_headers
            and search_target not in ssdp_device.search_headers
        )
        if is_new_service:
            _LOGGER.debug("See new service: %s, type: %s", ssdp_device, search_target)

        changed = (
            is_new_device
            or is_new_service
            or new_location
            or headers_differ_from_existing_search(ssdp_device, search_target, headers)
        )
        ssdp_source = SsdpSource.SEARCH_CHANGED if changed else SsdpSource.SEARCH_ALIVE

        # Update stored headers.
        search_headers = ssdp_device.search_headers
        if search_target in ssdp_device.search_headers:
            search_headers[search_target].replace(headers)
        else:
            search_headers[search_target] = headers

        return True, ssdp_device, search_target, ssdp_source

    def see_advertisement(
        self, headers: CaseInsensitiveDict
    ) -> Tuple[bool, Optional[SsdpDevice], Optional[DeviceOrServiceType]]:
        """See a device through an advertisement."""
        if not valid_advertisement_headers(headers):
            _LOGGER.debug("Received invalid advertisement headers: %s", headers)
            return False, None, None

        udn = headers.get_lower("_udn")
        is_new_device = udn not in self.devices

        ssdp_device, new_location = self._see_device(headers)
        if not ssdp_device:
            return False, None, None

        notification_type: NotificationType = headers.get_lower("nt")
        is_new_service = (
            notification_type not in ssdp_device.advertisement_headers
            and notification_type not in ssdp_device.search_headers
        )
        if is_new_service:
            _LOGGER.debug(
                "See new service: %s, type: %s", ssdp_device, notification_type
            )

        notification_sub_type: NotificationSubType = headers.get_lower("nts")
        propagate = (
            notification_sub_type == NotificationSubType.SSDP_UPDATE
            or is_new_device
            or is_new_service
            or new_location
            or headers_differ_from_existing_advertisement(
                ssdp_device, notification_type, headers
            )
        )

        # Update stored headers.
        advertisement_headers = ssdp_device.advertisement_headers
        if notification_type in advertisement_headers:
            advertisement_headers[notification_type].replace(headers)
        else:
            advertisement_headers[notification_type] = headers

        return propagate, ssdp_device, notification_type

    def _see_device(
        self, headers: CaseInsensitiveDict
    ) -> Tuple[Optional[SsdpDevice], bool]:
        """See a device through a search or advertisement."""
        # Purge any old devices.
        now = headers.get_lower("_timestamp")
        self.purge_devices(now)
        if not (usn := headers.get_lower("usn")) or not (udn := udn_from_usn(usn)):
            # Ignore broken devices.
            return None, False

        valid_to = extract_valid_to(headers)

        if udn not in self.devices:
            # Create new device.
            ssdp_device = SsdpDevice(udn, valid_to)
            _LOGGER.debug("See new device: %s", ssdp_device)
            self.devices[udn] = ssdp_device
        else:
            ssdp_device = self.devices[udn]
            ssdp_device.valid_to = valid_to

        # Test if new location.
        new_location = location_changed(ssdp_device, headers)

        # Update device.
        ssdp_device.add_location(headers.get_lower("location"), valid_to)
        ssdp_device.last_seen = now
        if not self.next_valid_to or self.next_valid_to > ssdp_device.valid_to:
            self.next_valid_to = ssdp_device.valid_to

        return ssdp_device, new_location

    def unsee_advertisement(
        self, headers: CaseInsensitiveDict
    ) -> Tuple[bool, Optional[SsdpDevice], Optional[DeviceOrServiceType]]:
        """Remove a device through an advertisement."""
        if not valid_byebye_headers(headers):
            return False, None, None
        if (
            not (usn := headers.get_lower("usn"))
            or not (udn := udn_from_usn(usn))
            or not (ssdp_device := self.devices.get(udn))
        ):
            # Ignore broken devices and devices we don't know about.
            return False, None, None

        del self.devices[udn]
        # Update device before propagating it
        notification_type: NotificationType = headers.get_lower("nt")
        advertisement_headers = ssdp_device.advertisement_headers
        if notification_type in advertisement_headers:
            advertisement_headers[notification_type].replace(headers)
        else:
            advertisement_headers[notification_type] = CaseInsensitiveDict(headers)

        propagate = True  # Always true, if this is the 2nd unsee then device is already deleted.
        return propagate, ssdp_device, notification_type

    def get_device(self, headers: CaseInsensitiveDict) -> Optional[SsdpDevice]:
        """Get a device from headers."""
        if not (usn := headers.get_lower("usn")) or not (udn := udn_from_usn(usn)):
            return None
        return self.devices.get(udn)

    def purge_devices(self, override_now: Optional[datetime] = None) -> None:
        """Purge any devices for which the CACHE-CONTROL header is timed out."""
        now = override_now or datetime.now()
        if self.next_valid_to and self.next_valid_to > now:
            return
        self.next_valid_to = None
        to_remove = []
        for usn, device in self.devices.items():
            if now > device.valid_to:
                to_remove.append(usn)
            elif not self.next_valid_to or device.valid_to < self.next_valid_to:
                self.next_valid_to = device.valid_to
                device.purge_locations(now)
        for usn in to_remove:
            _LOGGER.debug("Purging device, USN: %s", usn)
            del self.devices[usn]


class SsdpListener:
    """SSDP Search and Advertisement listener."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        async_callback: Optional[
            Callable[
                [SsdpDevice, DeviceOrServiceType, SsdpSource], Coroutine[Any, Any, None]
            ]
        ] = None,
        callback: Optional[
            Callable[[SsdpDevice, DeviceOrServiceType, SsdpSource], None]
        ] = None,
        source: Optional[AddressTupleVXType] = None,
        target: Optional[AddressTupleVXType] = None,
        loop: Optional[AbstractEventLoop] = None,
        search_timeout: int = SSDP_MX,
        device_tracker: Optional[SsdpDeviceTracker] = None,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        assert callback or async_callback, "Provide at least one callback"

        self.async_callback = async_callback
        self.callback = callback
        self.source, self.target = determine_source_target(source, target)
        self.loop = loop or asyncio.get_event_loop()
        self.search_timeout = search_timeout
        self._device_tracker = device_tracker or SsdpDeviceTracker()
        self._advertisement_listener: Optional[SsdpAdvertisementListener] = None
        self._search_listener: Optional[SsdpSearchListener] = None

    async def async_start(self) -> None:
        """Start search listener/advertisement listener."""
        self._advertisement_listener = SsdpAdvertisementListener(
            on_alive=self._on_alive,
            on_update=self._on_update,
            on_byebye=self._on_byebye,
            source=self.source,
            target=self.target,
            loop=self.loop,
        )
        await self._advertisement_listener.async_start()

        self._search_listener = SsdpSearchListener(
            callback=self._on_search,
            loop=self.loop,
            source=self.source,
            target=self.target,
            timeout=self.search_timeout,
        )
        await self._search_listener.async_start()

    async def async_stop(self) -> None:
        """Stop scanner/listener."""
        if self._advertisement_listener:
            await self._advertisement_listener.async_stop()

        if self._search_listener:
            self._search_listener.async_stop()

    async def async_search(
        self, override_target: Optional[AddressTupleVXType] = None
    ) -> None:
        """Send a SSDP Search packet."""
        assert self._search_listener is not None, "Call async_start() first"
        self._search_listener.async_search(override_target)

    def _on_search(self, headers: CaseInsensitiveDict) -> None:
        """Search callback."""
        (
            propagate,
            ssdp_device,
            device_or_service_type,
            ssdp_source,
        ) = self._device_tracker.see_search(headers)

        if propagate and ssdp_device and device_or_service_type:
            assert ssdp_source is not None
            if self.async_callback:
                coro = self.async_callback(
                    ssdp_device, device_or_service_type, ssdp_source
                )
                self.loop.create_task(coro)
            if self.callback:
                self.callback(ssdp_device, device_or_service_type, ssdp_source)

    def _on_alive(self, headers: CaseInsensitiveDict) -> None:
        """On alive."""
        (
            propagate,
            ssdp_device,
            device_or_service_type,
        ) = self._device_tracker.see_advertisement(headers)

        if propagate and ssdp_device and device_or_service_type:
            if self.async_callback:
                coro = self.async_callback(
                    ssdp_device, device_or_service_type, SsdpSource.ADVERTISEMENT_ALIVE
                )
                self.loop.create_task(coro)
            if self.callback:
                self.callback(
                    ssdp_device, device_or_service_type, SsdpSource.ADVERTISEMENT_ALIVE
                )

    def _on_byebye(self, headers: CaseInsensitiveDict) -> None:
        """On byebye."""
        (
            propagate,
            ssdp_device,
            device_or_service_type,
        ) = self._device_tracker.unsee_advertisement(headers)

        if propagate and ssdp_device and device_or_service_type:
            if self.async_callback:
                coro = self.async_callback(
                    ssdp_device, device_or_service_type, SsdpSource.ADVERTISEMENT_BYEBYE
                )
                self.loop.create_task(coro)
            if self.callback:
                self.callback(
                    ssdp_device, device_or_service_type, SsdpSource.ADVERTISEMENT_BYEBYE
                )

    def _on_update(self, headers: CaseInsensitiveDict) -> None:
        """On update."""
        (
            propagate,
            ssdp_device,
            device_or_service_type,
        ) = self._device_tracker.see_advertisement(headers)

        if propagate and ssdp_device and device_or_service_type:
            if self.async_callback:
                coro = self.async_callback(
                    ssdp_device, device_or_service_type, SsdpSource.ADVERTISEMENT_UPDATE
                )
                self.loop.create_task(coro)
            if self.callback:
                self.callback(
                    ssdp_device, device_or_service_type, SsdpSource.ADVERTISEMENT_UPDATE
                )

    @property
    def devices(self) -> Mapping[str, SsdpDevice]:
        """Get the known devices."""
        return self._device_tracker.devices
