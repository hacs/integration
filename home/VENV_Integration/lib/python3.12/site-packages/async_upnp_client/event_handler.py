# -*- coding: utf-8 -*-
"""async_upnp_client.event_handler module."""

import asyncio
import logging
import weakref
from abc import ABC
from datetime import timedelta
from http import HTTPStatus
from ipaddress import ip_address
from typing import Callable, Dict, Optional, Set, Tuple, Type, Union
from urllib.parse import urlparse

import defusedxml.ElementTree as DET

from async_upnp_client.client import UpnpDevice, UpnpRequester, UpnpService
from async_upnp_client.const import NS, HttpRequest, IPvXAddress, ServiceId
from async_upnp_client.exceptions import (
    UpnpConnectionError,
    UpnpError,
    UpnpResponseError,
    UpnpSIDError,
)
from async_upnp_client.utils import get_local_ip

_LOGGER = logging.getLogger(__name__)


def default_on_pre_notify(request: HttpRequest) -> HttpRequest:
    """Pre-notify hook."""
    # pylint: disable=unused-argument
    fixed_body = (request.body or "").rstrip(" \t\r\n\0")
    return HttpRequest(request.method, request.url, request.headers, fixed_body)


class UpnpNotifyServer(ABC):
    """
    Base Notify Server, which binds to a UpnpEventHandler.

    A single UpnpNotifyServer/UpnpEventHandler can be shared with multiple UpnpDevices.
    """

    @property
    def callback_url(self) -> str:
        """Return callback URL on which we are callable."""
        raise NotImplementedError()

    async def async_start_server(self) -> None:
        """Start the server."""
        raise NotImplementedError()

    async def async_stop_server(self) -> None:
        """Stop the server."""
        raise NotImplementedError()


class UpnpEventHandler:
    """
    Handles UPnP eventing.

    An incoming NOTIFY request should be pass to handle_notify().
    subscribe/resubscribe/unsubscribe handle subscriptions.

    When using a reverse proxy in combination with a event handler, you should use
    the option to override the callback url.

    A single UpnpNotifyServer/UpnpEventHandler can be shared with multiple UpnpDevices.
    """

    def __init__(
        self,
        notify_server: UpnpNotifyServer,
        requester: UpnpRequester,
        on_pre_notify: Callable[[HttpRequest], HttpRequest] = default_on_pre_notify,
    ) -> None:
        """
        Initialize.

        notify_server is the notify server which is actually listening on a socket.
        """
        self._notify_server = notify_server
        self._requester = requester
        self.on_pre_notify = on_pre_notify

        self._subscriptions: weakref.WeakValueDictionary[ServiceId, UpnpService] = (
            weakref.WeakValueDictionary()
        )
        self._backlog: Dict[ServiceId, HttpRequest] = {}

    @property
    def callback_url(self) -> str:
        """Return callback URL on which we are callable."""
        return self._notify_server.callback_url

    def sid_for_service(self, service: UpnpService) -> Optional[ServiceId]:
        """Get the service connected to SID."""
        for sid, subscribed_service in self._subscriptions.items():
            if subscribed_service == service:
                return sid

        return None

    def service_for_sid(self, sid: ServiceId) -> Optional[UpnpService]:
        """Get a UpnpService for SID."""
        return self._subscriptions.get(sid)

    def _sid_and_service(
        self, service_or_sid: Union[UpnpService, ServiceId]
    ) -> Tuple[ServiceId, UpnpService]:
        """
        Resolve a SID or service to both SID and service.

        :raise KeyError: Cannot determine SID from UpnpService, or vice versa.
        """
        sid: Optional[ServiceId]
        service: Optional[UpnpService]

        if isinstance(service_or_sid, UpnpService):
            service = service_or_sid
            sid = self.sid_for_service(service)
            if not sid:
                raise KeyError(f"Unknown UpnpService {service}")
        else:
            sid = service_or_sid
            service = self.service_for_sid(sid)
            if not service:
                raise KeyError(f"Unknown SID {sid}")

        return sid, service

    async def handle_notify(self, http_request: HttpRequest) -> HTTPStatus:
        """Handle a NOTIFY request."""
        http_request = self.on_pre_notify(http_request)

        # ensure valid request
        if "NT" not in http_request.headers or "NTS" not in http_request.headers:
            return HTTPStatus.BAD_REQUEST

        if (
            http_request.headers["NT"] != "upnp:event"
            or http_request.headers["NTS"] != "upnp:propchange"
            or "SID" not in http_request.headers
        ):
            return HTTPStatus.PRECONDITION_FAILED

        sid: ServiceId = http_request.headers["SID"]
        service = self.service_for_sid(sid)

        # SID not known yet? store it in the backlog
        # Some devices don't behave nicely and send events before the SUBSCRIBE call is done.
        if not service:
            _LOGGER.debug("Storing NOTIFY in backlog for SID: %s", sid)
            self._backlog[sid] = http_request

            return HTTPStatus.OK

        # decode event and send updates to service
        changes = {}
        el_root = DET.fromstring(http_request.body)
        for el_property in el_root.findall("./event:property", NS):
            for el_state_var in el_property:
                name = el_state_var.tag
                value = el_state_var.text or ""
                changes[name] = value

        # send changes to service
        service.notify_changed_state_variables(changes)

        return HTTPStatus.OK

    async def async_subscribe(
        self,
        service: UpnpService,
        timeout: timedelta = timedelta(seconds=1800),
    ) -> Tuple[ServiceId, timedelta]:
        """
        Subscription to a UpnpService.

        Be sure to re-subscribe before the subscription timeout passes.

        :param service: UpnpService to subscribe to self
        :param timeout: Timeout of subscription
        :return: SID (subscription ID), renewal timeout (may be different to
            supplied timeout)
        :raise UpnpResponseError: Error in response to subscription request
        :raise UpnpSIDError: No SID received for subscription
        :raise UpnpConnectionError: Device might be offline.
        :raise UpnpCommunicationError (or subclass): Error while performing
            subscription request.
        """
        _LOGGER.debug(
            "Subscribing to: %s, callback URL: %s", service, self.callback_url
        )

        # do SUBSCRIBE request
        headers = {
            "NT": "upnp:event",
            "TIMEOUT": "Second-" + str(timeout.seconds),
            "HOST": urlparse(service.event_sub_url).netloc,
            "CALLBACK": f"<{self.callback_url}>",
        }
        backlog_request = HttpRequest("SUBSCRIBE", service.event_sub_url, headers, None)
        response = await self._requester.async_http_request(backlog_request)

        # check results
        if response.status_code != 200:
            _LOGGER.debug("Did not receive 200, but %s", response.status_code)
            raise UpnpResponseError(
                status=response.status_code, headers=response.headers
            )

        if "sid" not in response.headers:
            _LOGGER.debug("No SID received, aborting subscribe")
            raise UpnpSIDError

        # Device can give a different TIMEOUT header than what we have provided.
        if (
            "timeout" in response.headers
            and response.headers["timeout"] != "Second-infinite"
            and "Second-" in response.headers["timeout"]
        ):
            response_timeout = response.headers["timeout"]
            timeout_seconds = int(response_timeout[7:])  # len("Second-") == 7
            timeout = timedelta(seconds=timeout_seconds)

        sid: ServiceId = response.headers["sid"]
        self._subscriptions[sid] = service
        _LOGGER.debug(
            "Subscribed, service: %s, SID: %s, timeout: %s", service, sid, timeout
        )

        # replay any backlog we have for this service
        if sid in self._backlog:
            _LOGGER.debug("Re-playing backlogged NOTIFY for SID: %s", sid)
            backlog_request = self._backlog[sid]
            await self.handle_notify(backlog_request)
            del self._backlog[sid]

        return sid, timeout

    async def _async_do_resubscribe(
        self,
        service: UpnpService,
        sid: ServiceId,
        timeout: timedelta = timedelta(seconds=1800),
    ) -> Tuple[ServiceId, timedelta]:
        """Perform only a resubscribe, caller can retry subscribe if this fails."""
        # do SUBSCRIBE request
        headers = {
            "HOST": urlparse(service.event_sub_url).netloc,
            "SID": sid,
            "TIMEOUT": "Second-" + str(timeout.total_seconds()),
        }
        request = HttpRequest("SUBSCRIBE", service.event_sub_url, headers, None)
        response = await self._requester.async_http_request(request)

        # check results
        if response.status_code != 200:
            _LOGGER.debug("Did not receive 200, but %s", response.status_code)
            raise UpnpResponseError(
                status=response.status_code, headers=response.headers
            )

        # Devices should return the SID when re-subscribe,
        # but in case it doesn't, use the new SID.
        if "sid" in response.headers and response.headers["sid"]:
            new_sid: ServiceId = response.headers["sid"]
            if new_sid != sid:
                del self._subscriptions[sid]
                sid = new_sid

        # Device can give a different TIMEOUT header than what we have provided.
        if (
            "timeout" in response.headers
            and response.headers["timeout"] != "Second-infinite"
            and "Second-" in response.headers["timeout"]
        ):
            response_timeout = response.headers["timeout"]
            timeout_seconds = int(response_timeout[7:])  # len("Second-") == 7
            timeout = timedelta(seconds=timeout_seconds)

        self._subscriptions[sid] = service
        _LOGGER.debug(
            "Resubscribed, service: %s, SID: %s, timeout: %s", service, sid, timeout
        )

        return sid, timeout

    async def async_resubscribe(
        self,
        service_or_sid: Union[UpnpService, ServiceId],
        timeout: timedelta = timedelta(seconds=1800),
    ) -> Tuple[ServiceId, timedelta]:
        """
        Renew subscription to a UpnpService.

        :param service_or_sid: UpnpService or existing SID to resubscribe
        :param timeout: Timeout of subscription
        :return: SID (subscription ID), renewal timeout (may be different to
            supplied timeout)
        :raise KeyError: Supplied service_or_sid is not known.
        :raise UpnpResponseError: Error in response to subscription request
        :raise UpnpSIDError: No SID received for subscription
        :raise UpnpConnectionError: Device might be offline.
        :raise UpnpCommunicationError (or subclass): Error while performing
            subscription request.
        """
        _LOGGER.debug("Resubscribing to: %s", service_or_sid)

        # Try a regular resubscribe. If that fails, delete old subscription and
        # do a full subscribe again.

        sid, service = self._sid_and_service(service_or_sid)
        try:
            return await self._async_do_resubscribe(service, sid, timeout)
        except UpnpConnectionError as err:
            _LOGGER.debug(
                "Resubscribe for %s failed: %s. Device offline, not retrying.",
                service_or_sid,
                err,
            )
            del self._subscriptions[sid]
            raise
        except UpnpError as err:
            _LOGGER.debug(
                "Resubscribe for %s failed: %s. Trying full subscribe.",
                service_or_sid,
                err,
            )
        del self._subscriptions[sid]
        return await self.async_subscribe(service, timeout)

    async def async_resubscribe_all(self) -> None:
        """Renew all current subscription."""
        await asyncio.gather(
            *(self.async_resubscribe(sid) for sid in self._subscriptions)
        )

    async def async_unsubscribe(
        self,
        service_or_sid: Union[UpnpService, ServiceId],
    ) -> ServiceId:
        """Unsubscribe from a UpnpService."""
        sid, service = self._sid_and_service(service_or_sid)

        _LOGGER.debug(
            "Unsubscribing from SID: %s, service: %s device: %s",
            sid,
            service,
            service.device,
        )

        # Remove registration before potential device errors
        del self._subscriptions[sid]

        # do UNSUBSCRIBE request
        headers = {
            "HOST": urlparse(service.event_sub_url).netloc,
            "SID": sid,
        }
        request = HttpRequest("UNSUBSCRIBE", service.event_sub_url, headers, None)
        response = await self._requester.async_http_request(request)

        # check results
        if response.status_code != 200:
            _LOGGER.debug("Did not receive 200, but %s", response.status_code)
            raise UpnpResponseError(
                status=response.status_code, headers=response.headers
            )

        return sid

    async def async_unsubscribe_all(self) -> None:
        """Unsubscribe all subscriptions."""
        sids = list(self._subscriptions)
        await asyncio.gather(
            *(self.async_unsubscribe(sid) for sid in sids),
            return_exceptions=True,
        )

    async def async_stop(self) -> None:
        """Stop event the UpnpNotifyServer."""
        # This calls async_unsubscribe_all() via the notify server.
        await self._notify_server.async_stop_server()


class UpnpEventHandlerRegister:
    """Event handler register to handle multiple interfaces."""

    def __init__(self, requester: UpnpRequester, notify_server_type: Type) -> None:
        """Initialize."""
        self.requester = requester
        self.notify_server_type = notify_server_type
        self._event_handlers: Dict[
            IPvXAddress, Tuple[UpnpEventHandler, Set[UpnpDevice]]
        ] = {}

    def _get_event_handler_for_device(
        self, device: UpnpDevice
    ) -> Optional[UpnpEventHandler]:
        """Get the event handler for the device, if known."""
        local_ip_str = get_local_ip(device.device_url)
        local_ip = ip_address(local_ip_str)
        if local_ip not in self._event_handlers:
            return None

        event_handler, devices = self._event_handlers[local_ip]
        if device in devices:
            return event_handler

        return None

    def has_event_handler_for_device(self, device: UpnpDevice) -> bool:
        """Check if an event handler for a device is already available."""
        return self._get_event_handler_for_device(device) is not None

    async def async_add_device(self, device: UpnpDevice) -> UpnpEventHandler:
        """Add a new device, creates or gets the event handler for this device."""
        local_ip_str = get_local_ip(device.device_url)
        local_ip = ip_address(local_ip_str)
        if local_ip not in self._event_handlers:
            event_handler = await self._create_event_handler_for_device(device)
            self._event_handlers[local_ip] = (event_handler, set([device]))
            return event_handler

        event_handler, devices = self._event_handlers[local_ip]
        devices.add(device)

        return event_handler

    async def _create_event_handler_for_device(
        self, device: UpnpDevice
    ) -> UpnpEventHandler:
        """Create a new event handler for a device."""
        local_ip_str = get_local_ip(device.device_url)
        source_addr = (local_ip_str, 0)
        notify_server: UpnpNotifyServer = self.notify_server_type(
            requester=self.requester, source=source_addr
        )
        await notify_server.async_start_server()
        return UpnpEventHandler(notify_server, self.requester)

    async def async_remove_device(
        self, device: UpnpDevice
    ) -> Optional[UpnpEventHandler]:
        """Remove an existing device, destroys the event handler and returns it, if needed."""
        local_ip_str = get_local_ip(device.device_url)
        local_ip = ip_address(local_ip_str)
        assert local_ip in self._event_handlers

        event_handler, devices = self._event_handlers[local_ip]
        assert device in devices
        devices.remove(device)

        if not devices:
            await event_handler.async_stop()
            del self._event_handlers[local_ip]
            return event_handler

        return None
