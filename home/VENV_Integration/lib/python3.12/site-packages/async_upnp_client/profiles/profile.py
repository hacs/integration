# -*- coding: utf-8 -*-
"""async_upnp_client.profiles.profile module."""

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Union

from async_upnp_client.client import (
    EventCallbackType,
    UpnpAction,
    UpnpDevice,
    UpnpService,
    UpnpStateVariable,
    UpnpValueError,
)
from async_upnp_client.const import AddressTupleVXType
from async_upnp_client.event_handler import UpnpEventHandler
from async_upnp_client.exceptions import (
    UpnpConnectionError,
    UpnpError,
    UpnpResponseError,
)
from async_upnp_client.search import async_search
from async_upnp_client.ssdp import SSDP_MX
from async_upnp_client.utils import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)


SUBSCRIBE_TIMEOUT = timedelta(minutes=9)
RESUBSCRIBE_TOLERANCE = timedelta(minutes=1)
RESUBSCRIBE_TOLERANCE_SECS = RESUBSCRIBE_TOLERANCE.total_seconds()


def find_device_of_type(device: UpnpDevice, device_types: List[str]) -> UpnpDevice:
    """Find the (embedded) UpnpDevice of any of the device types."""
    for device_ in device.all_devices:
        if device_.device_type in device_types:
            return device_

    raise UpnpError(f"Could not find device of type: {device_types}")


class UpnpProfileDevice:
    """
    Base class for UpnpProfileDevices.

    Override _SERVICE_TYPES for aliases. Override SERVICE_IDS for required
    service_id values.
    """

    DEVICE_TYPES: List[str] = []

    SERVICE_IDS: FrozenSet[str] = frozenset()

    _SERVICE_TYPES: Dict[str, Set[str]] = {}

    @classmethod
    async def async_search(
        cls, source: Optional[AddressTupleVXType] = None, timeout: int = SSDP_MX
    ) -> Set[CaseInsensitiveDict]:
        """
        Search for this device type.

        This only returns search info, not a profile itself.

        :param source_ip Source IP to scan from
        :param timeout Timeout to use
        :return: Set of devices (dicts) found
        """
        responses = set()

        async def on_response(data: CaseInsensitiveDict) -> None:
            if "st" in data and data["st"] in cls.DEVICE_TYPES:
                responses.add(data)

        await async_search(async_callback=on_response, source=source, timeout=timeout)

        return responses

    @classmethod
    async def async_discover(cls) -> Set[CaseInsensitiveDict]:
        """Alias for async_search."""
        return await cls.async_search()

    @classmethod
    def is_profile_device(cls, device: UpnpDevice) -> bool:
        """Check for device's support of the profile defined in this (sub)class.

        The device must be (or have an embedded device) that matches the class
        device type, and it must provide all services that are defined by this
        class.
        """
        try:
            profile_device = find_device_of_type(device, cls.DEVICE_TYPES)
        except UpnpError:
            return False

        # Check that every service required by the subclass is declared by the device
        device_service_ids = {
            service.service_id for service in profile_device.all_services
        }
        if not cls.SERVICE_IDS.issubset(device_service_ids):
            return False

        return True

    def __init__(
        self, device: UpnpDevice, event_handler: Optional[UpnpEventHandler]
    ) -> None:
        """Initialize."""
        self.device = device
        self.profile_device = find_device_of_type(device, self.DEVICE_TYPES)
        self._event_handler = event_handler
        self.on_event: Optional[EventCallbackType] = None
        self._icon: Optional[str] = None
        # Map of SID to renewal timestamp (monotonic clock seconds)
        self._subscriptions: Dict[str, float] = {}
        self._resubscriber_task: Optional[asyncio.Task] = None

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self.profile_device.name

    @property
    def manufacturer(self) -> str:
        """Get the manufacturer of this device."""
        return self.profile_device.manufacturer

    @property
    def model_description(self) -> Optional[str]:
        """Get the model description of this device."""
        return self.profile_device.model_description

    @property
    def model_name(self) -> str:
        """Get the model name of this device."""
        return self.profile_device.model_name

    @property
    def model_number(self) -> Optional[str]:
        """Get the model number of this device."""
        return self.profile_device.model_number

    @property
    def serial_number(self) -> Optional[str]:
        """Get the serial number of this device."""
        return self.profile_device.serial_number

    @property
    def udn(self) -> str:
        """Get the UDN of the device."""
        return self.profile_device.udn

    @property
    def device_type(self) -> str:
        """Get the device type of this device."""
        return self.profile_device.device_type

    @property
    def icon(self) -> Optional[str]:
        """Get a URL for the biggest icon for this device."""
        if not self.profile_device.icons:
            return None

        if not self._icon:
            icon_mime_preference = {"image/png": 3, "image/jpeg": 2, "image/gif": 1}
            icons = [icon for icon in self.profile_device.icons if icon.url]
            icons = sorted(
                icons,
                # Sort by area, then colour depth, then preferred mimetype
                key=lambda icon: (
                    icon.width * icon.height,
                    icon.depth,
                    icon_mime_preference.get(icon.mimetype, 0),
                ),
                reverse=True,
            )
            self._icon = icons[0].url

        return self._icon

    def _service(self, service_type_abbreviation: str) -> Optional[UpnpService]:
        """Get UpnpService by service_type or alias."""
        if not self.profile_device:
            return None

        if service_type_abbreviation not in self._SERVICE_TYPES:
            return None

        for service_type in self._SERVICE_TYPES[service_type_abbreviation]:
            service = self.profile_device.find_service(service_type)
            if service:
                return service

        return None

    def _state_variable(
        self, service_name: str, state_variable_name: str
    ) -> Optional[UpnpStateVariable]:
        """Get state_variable from service."""
        service = self._service(service_name)
        if not service:
            return None

        if not service.has_state_variable(state_variable_name):
            return None

        return service.state_variable(state_variable_name)

    def _action(self, service_name: str, action_name: str) -> Optional[UpnpAction]:
        """Check if service has action."""
        service = self._service(service_name)
        if not service:
            return None

        if not service.has_action(action_name):
            return None

        return service.action(action_name)

    def _interesting_service(self, service: UpnpService) -> bool:
        """Check if service is a service we're interested in."""
        service_type = service.service_type
        for service_types in self._SERVICE_TYPES.values():
            if service_type in service_types:
                return True

        return False

    async def _async_resubscribe_services(
        self, now: Optional[float] = None, notify_errors: bool = False
    ) -> None:
        """Renew existing subscriptions.

        :param now: time.monotonic reference for current time
        :param notify_errors: Call on_event in case of error instead of raising
        """
        assert self._event_handler

        if now is None:
            now = time.monotonic()
        renewal_threshold = now - RESUBSCRIBE_TOLERANCE_SECS

        _LOGGER.debug("Resubscribing to services with threshold %f", renewal_threshold)

        for sid, renewal_time in list(self._subscriptions.items()):
            if renewal_time < renewal_threshold:
                _LOGGER.debug("Skipping %s with renewal_time %f", sid, renewal_time)
                continue

            _LOGGER.debug("Resubscribing to %s with renewal_time %f", sid, renewal_time)
            # Subscription is going to be changed, no matter what
            del self._subscriptions[sid]
            # Determine service for on_event call in case of failure
            service = self._event_handler.service_for_sid(sid)
            if not service:
                _LOGGER.error("Subscription for %s was lost", sid)
                continue

            try:
                new_sid, timeout = await self._event_handler.async_resubscribe(
                    sid, timeout=SUBSCRIBE_TIMEOUT
                )
            except UpnpError as err:
                if isinstance(err, UpnpConnectionError):
                    # Device has gone offline
                    self.profile_device.available = False
                _LOGGER.warning("Failed (re-)subscribing to: %s, reason: %r", sid, err)
                if notify_errors:
                    # Notify event listeners that something has changed
                    self._on_event(service, [])
                else:
                    raise
            else:
                self._subscriptions[new_sid] = now + timeout.total_seconds()

    async def _resubscribe_loop(self) -> None:
        """Periodically resubscribes to current subscriptions."""
        _LOGGER.debug("_resubscribe_loop started")
        while self._subscriptions:
            next_renewal = min(self._subscriptions.values())
            wait_time = next_renewal - time.monotonic() - RESUBSCRIBE_TOLERANCE_SECS
            _LOGGER.debug("Resubscribing in %f seconds", wait_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            await self._async_resubscribe_services(notify_errors=True)

        _LOGGER.debug("_resubscribe_loop ended because of no subscriptions")

    async def _update_resubscriber_task(self) -> None:
        """Start or stop the resubscriber task, depending on having subscriptions."""
        # Clear out done task to make later logic easier
        if self._resubscriber_task and self._resubscriber_task.cancelled():
            self._resubscriber_task = None

        if self._subscriptions and not self._resubscriber_task:
            _LOGGER.debug("Creating resubscribe_task")
            # pylint: disable=fixme
            # TODO: Use create_task instead of ensure_future with Python 3.8+
            # self._resubscriber_task = asyncio.create_task(
            # self._resubscribe_loop(),
            # name=f"UpnpProfileDevice({self.name})._resubscriber_task",
            # )
            self._resubscriber_task = asyncio.ensure_future(self._resubscribe_loop())

        if not self._subscriptions and self._resubscriber_task:
            _LOGGER.debug("Cancelling resubscribe_task")
            self._resubscriber_task.cancel()
            try:
                await self._resubscriber_task
            except asyncio.CancelledError:
                pass
            self._resubscriber_task = None

    async def async_subscribe_services(
        self, auto_resubscribe: bool = False
    ) -> Optional[timedelta]:
        """(Re-)Subscribe to services.

        :param auto_resubscribe: Automatically resubscribe to subscriptions
            before they expire. If this is enabled, failure to resubscribe will
            be indicated by on_event being called with the failed service and an
            empty state_variables list.
        :return: time until this next needs to be called, or None if manual
            resubscription is not needed.
        :raise UpnpResponseError: Device rejected subscription request.
            State variables will need to be polled.
        :raise UpnpError or subclass: Failed to subscribe to all interesting
            services.
        """
        if not self._event_handler:
            _LOGGER.info("No event_handler, event handling disabled")
            return None

        # Using time.monotonic to avoid problems with system clock changes
        now = time.monotonic()

        try:
            if self._subscriptions:
                # Resubscribe existing subscriptions
                await self._async_resubscribe_services(now)
            else:
                # Subscribe to services we are interested in
                for service in self.profile_device.all_services:
                    if not self._interesting_service(service):
                        continue

                    _LOGGER.debug("Subscribing to service: %s", service)
                    service.on_event = self._on_event
                    new_sid, timeout = await self._event_handler.async_subscribe(
                        service, timeout=SUBSCRIBE_TIMEOUT
                    )
                    self._subscriptions[new_sid] = now + timeout.total_seconds()
        except UpnpError as err:
            if isinstance(err, UpnpResponseError) and not self._subscriptions:
                _LOGGER.info("Device rejected subscription request: %r", err)
            else:
                _LOGGER.warning("Failed subscribing to service: %r", err)
            # Unsubscribe anything that was subscribed, no half-done subscriptions
            try:
                await self.async_unsubscribe_services()
            except UpnpError:
                pass
            raise

        if not self._subscriptions:
            return None

        if auto_resubscribe:
            await self._update_resubscriber_task()
            return None

        lowest_timeout_delta = min(self._subscriptions.values()) - now
        resubcription_timeout = (
            timedelta(seconds=lowest_timeout_delta) - RESUBSCRIBE_TOLERANCE
        )
        return max(resubcription_timeout, timedelta(seconds=0))

    async def _async_unsubscribe_service(self, sid: str) -> None:
        """Unsubscribe from one service, handling possible exceptions."""
        assert self._event_handler

        try:
            await self._event_handler.async_unsubscribe(sid)
        except UpnpError as err:
            _LOGGER.debug("Failed unsubscribing from: %s, reason: %r", sid, err)
        except KeyError:
            _LOGGER.warning(
                "%s was already unsubscribed. AiohttpNotifyServer was "
                "probably stopped before we could unsubscribe.",
                sid,
            )

    async def async_unsubscribe_services(self) -> None:
        """Unsubscribe from all of our subscribed services."""
        # Delete list of subscriptions and cancel renewal before unsubscribing
        # to avoid unsub-resub race.
        sids = list(self._subscriptions)
        self._subscriptions.clear()
        await self._update_resubscriber_task()

        await asyncio.gather(*(self._async_unsubscribe_service(sid) for sid in sids))

    @property
    def is_subscribed(self) -> bool:
        """Get current service subscription state."""
        return bool(self._subscriptions)

    async def _async_poll_state_variables(
        self, service_name: str, action_names: Union[str, Sequence[str]], **in_args: Any
    ) -> None:
        """Update state variables by polling actions that return their values.

        Assumes that the actions's relatedStateVariable names the correct state
        variable for updating.
        """
        service = self._service(service_name)
        if not service:
            _LOGGER.debug("Can't poll missing service %s", service_name)
            return

        if isinstance(action_names, str):
            action_names = [action_names]

        changed_state_variables: List[UpnpStateVariable] = []

        for action_name in action_names:
            try:
                action = service.action(action_name)
            except KeyError:
                _LOGGER.debug(
                    "Can't poll missing action %s:%s for state variables",
                    service_name,
                    action_name,
                )
                continue
            try:
                result = await action.async_call(**in_args)
            except UpnpResponseError as err:
                _LOGGER.debug(
                    "Failed to call action %s:%s for state variables: %r",
                    service_name,
                    action_name,
                    err,
                )
                continue

            for arg in action.arguments:
                if arg.direction != "out":
                    continue
                if arg.name not in result:
                    continue
                if arg.related_state_variable.value == arg.value:
                    continue

                try:
                    arg.related_state_variable.value = arg.value
                except UpnpValueError:
                    continue
                changed_state_variables.append(arg.related_state_variable)

        if changed_state_variables:
            self._on_event(service, changed_state_variables)

    def _on_event(
        self, service: UpnpService, state_variables: Sequence[UpnpStateVariable]
    ) -> None:
        """
        State variable(s) changed. Override to handle events.

        :param service Service which sent the event.
        :param state_variables State variables which have been changed.
        """
        if self.on_event:
            self.on_event(service, state_variables)  # pylint: disable=not-callable
