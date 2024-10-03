# -*- coding: utf-8 -*-
"""UPnP Server."""

# pylint: disable=too-many-lines

import asyncio
import logging
import socket
import sys
import time
import xml.etree.ElementTree as ET
from asyncio.transports import DatagramTransport
from datetime import datetime, timedelta, timezone
from functools import partial, wraps
from itertools import cycle
from random import randrange
from time import mktime
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)
from urllib.parse import urlparse
from uuid import uuid4
from wsgiref.handlers import format_date_time

import defusedxml.ElementTree as DET  # pylint: disable=import-error
import voluptuous as vol
from aiohttp.web import (
    Application,
    AppRunner,
    HTTPBadRequest,
    Request,
    Response,
    RouteDef,
    TCPSite,
)

from async_upnp_client import __version__ as version
from async_upnp_client.aiohttp import AiohttpRequester
from async_upnp_client.client import (
    T,
    UpnpAction,
    UpnpDevice,
    UpnpError,
    UpnpRequester,
    UpnpService,
    UpnpStateVariable,
)
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.const import (
    STATE_VARIABLE_TYPE_MAPPING,
    ActionArgumentInfo,
    ActionInfo,
    AddressTupleVXType,
    DeviceInfo,
    EventableStateVariableTypeInfo,
    HttpRequest,
    NotificationSubType,
    ServiceInfo,
    StateVariableInfo,
    StateVariableTypeInfo,
)
from async_upnp_client.exceptions import (
    UpnpActionError,
    UpnpActionErrorCode,
    UpnpValueError,
)
from async_upnp_client.ssdp import (
    _LOGGER_TRAFFIC_SSDP,
    SSDP_DISCOVER,
    SSDP_ST_ALL,
    SSDP_ST_ROOTDEVICE,
    SsdpProtocol,
    build_ssdp_packet,
    determine_source_target,
    get_ssdp_socket,
    is_ipv6_address,
)
from async_upnp_client.utils import CaseInsensitiveDict

NAMESPACES = {
    "s": "http://schemas.xmlsoap.org/soap/envelope/",
    "es": "http://schemas.xmlsoap.org/soap/encoding/",
}
HEADER_SERVER = f"async-upnp-client/{version} UPnP/2.0 Server/1.0"
HEADER_CACHE_CONTROL = "max-age=1800"
SSDP_SEARCH_RESPONDER_OPTIONS = "ssdp_search_responder_options"
SSDP_SEARCH_RESPONDER_OPTION_ALWAYS_REPLY_WITH_ROOT_DEVICE = (
    "ssdp_search_responder_always_rootdevice"
)
SSDP_SEARCH_RESPONDER_OPTION_HEADERS = "search_headers"
SSDP_ADVERTISEMENT_ANNOUNCER_OPTIONS = "ssdp_advertisement_announcer_options"
SSDP_ADVERTISEMENT_ANNOUNCER_OPTION_HEADERS = "advertisement_headers"

_LOGGER = logging.getLogger(__name__)
_LOGGER_TRAFFIC_UPNP = logging.getLogger("async_upnp_client.traffic.upnp")

# Hack: Bend INFO to DEBUG.
_LOGGER_TRAFFIC_UPNP.info = _LOGGER_TRAFFIC_UPNP.debug  # type: ignore


class NopRequester(UpnpRequester):  # pylint: disable=too-few-public-methods
    """NopRequester, does nothing."""


class EventSubscriber:
    """Represent a service subscriber."""

    DEFAULT_TIMEOUT = 3600

    def __init__(self, callback_url: str, timeout: Optional[int]) -> None:
        """Initialize."""
        self._url = callback_url
        self._uuid = str(uuid4())
        self._event_key = 0
        self._expires = datetime.now()
        self.timeout = timeout

    @property
    def url(self) -> str:
        """Return callback URL."""
        return self._url

    @property
    def uuid(self) -> str:
        """Return subscriber uuid."""
        return self._uuid

    @property
    def timeout(self) -> Optional[int]:
        """Return timeout in seconds."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: Optional[int]) -> None:
        """Set timeout before unsubscribe."""
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        self._timeout = timeout
        self._expires = datetime.now() + timedelta(seconds=timeout)

    @property
    def expiration(self) -> datetime:
        """Return expiration time of subscription."""
        return self._expires

    def get_next_seq(self) -> int:
        """Return the next sequence number for an event."""
        res = self._event_key
        self._event_key += 1
        if self._event_key > 0xFFFF_FFFF:
            self._event_key = 1
        return res


class UpnpEventableStateVariable(UpnpStateVariable):
    """Representation of an eventable State Variable."""

    def __init__(
        self, state_variable_info: StateVariableInfo, schema: vol.Schema
    ) -> None:
        """Initialize."""
        super().__init__(state_variable_info, schema)
        self._last_sent = datetime.fromtimestamp(0, timezone.utc)
        self._defered_event: Optional[asyncio.TimerHandle] = None
        self._sent_event = asyncio.Event()

    @property
    def event_triggered(self) -> asyncio.Event:
        """Return event object for trigger completion."""
        return self._sent_event

    @property
    def max_rate(self) -> float:
        """Return max event rate."""
        type_info = cast(
            EventableStateVariableTypeInfo, self._state_variable_info.type_info
        )
        return type_info.max_rate or 0.0

    @property
    def value(self) -> Optional[T]:
        """Get Python value for this argument."""
        return super().value

    @value.setter
    def value(self, value: Any) -> None:
        """Set value, python typed."""
        if self._value == value:
            return
        super(UpnpEventableStateVariable, self.__class__).value.__set__(self, value)  # type: ignore
        if not self.service or self._defered_event:
            return
        assert self._updated_at
        next_update = self._last_sent + timedelta(seconds=self.max_rate)
        if self._updated_at >= next_update:
            asyncio.create_task(self.trigger_event())
        else:
            loop = asyncio.get_running_loop()
            self._defered_event = loop.call_at(
                next_update.timestamp(), self.trigger_event
            )

    async def trigger_event(self) -> None:
        """Update any waiting subscribers."""
        self._last_sent = datetime.now(timezone.utc)
        service = self.service
        assert isinstance(service, UpnpServerService)
        self._sent_event.set()
        asyncio.create_task(service.async_send_events())  # pylint: disable=no-member


class UpnpServerAction(UpnpAction):
    """Representation of an Action."""

    async def async_handle(self, **kwargs: Any) -> Any:
        """Handle action."""
        self.validate_arguments(**kwargs)
        raise NotImplementedError()


class UpnpServerService(UpnpService):
    """UPnP Service representation."""

    SERVICE_DEFINITION: ServiceInfo
    STATE_VARIABLE_DEFINITIONS: Mapping[str, StateVariableTypeInfo]

    def __init__(self, requester: UpnpRequester) -> None:
        """Initialize."""
        super().__init__(requester, self.SERVICE_DEFINITION, [], [])

        self._init_state_variables()
        self._init_actions()
        self._subscribers: List[EventSubscriber] = []

    def _init_state_variables(self) -> None:
        """Initialize state variables from STATE_VARIABLE_DEFINITIONS."""
        for name, type_info in self.STATE_VARIABLE_DEFINITIONS.items():
            self.create_state_var(name, type_info)

    def create_state_var(
        self, name: str, type_info: StateVariableTypeInfo
    ) -> UpnpStateVariable:
        """Create UpnpStateVariable."""
        existing = self.state_variables.get(name, None)
        if existing is not None:
            raise UpnpError(f"StateVariable with the same name exists: {name}")

        state_var_info = StateVariableInfo(
            name,
            send_events=False,
            type_info=type_info,
            xml=ET.Element("stateVariable"),
        )

        # pylint: disable=protected-access
        state_var: UpnpStateVariable
        if isinstance(type_info, EventableStateVariableTypeInfo):
            state_var = UpnpEventableStateVariable(
                state_var_info,
                UpnpFactory(self.requester)._state_variable_create_schema(type_info),
            )
        else:
            state_var = UpnpStateVariable(
                state_var_info,
                UpnpFactory(self.requester)._state_variable_create_schema(type_info),
            )
        state_var.service = self
        if type_info.default_value is not None:
            state_var.upnp_value = type_info.default_value

        self.state_variables[state_var.name] = state_var
        return state_var

    def _init_actions(self) -> None:
        """Initialize actions from annotated methods."""
        for item in dir(self):
            if item in ("control_url", "event_sub_url", "scpd_url", "device"):
                continue

            thing = getattr(self, item, None)
            if not thing or not hasattr(thing, "__upnp_action__"):
                continue

            self._init_action(thing)

    def _init_action(self, func: Callable) -> UpnpAction:
        """Initialize action for method."""
        name, in_args, out_args = cast(
            Tuple[str, Mapping[str, str], Mapping[str, str]],
            getattr(func, "__upnp_action__"),
        )

        arg_infos: List[ActionArgumentInfo] = []
        args: List[UpnpAction.Argument] = []
        for arg_name, state_var_name in in_args.items():
            # Validate function has parameter.
            assert arg_name in func.__annotations__

            # Validate parameter type.
            annotation = func.__annotations__.get(arg_name, None)
            state_var = self.state_variable(state_var_name)
            assert state_var.data_type_mapping["type"] == annotation

            # Build in-argument.
            arg_info = ActionArgumentInfo(
                arg_name,
                direction="in",
                state_variable_name=state_var.name,
                xml=ET.Element("server_argument"),
            )
            arg_infos.append(arg_info)

            arg = UpnpAction.Argument(arg_info, state_var)
            args.append(arg)

        for arg_name, state_var_name in out_args.items():
            # Build out-argument.
            state_var = self.state_variable(state_var_name)
            arg_info = ActionArgumentInfo(
                arg_name,
                direction="out",
                state_variable_name=state_var.name,
                xml=ET.Element("server_argument"),
            )
            arg_infos.append(arg_info)

            arg = UpnpAction.Argument(arg_info, state_var)
            args.append(arg)

        action_info = ActionInfo(
            name=name,
            arguments=arg_infos,
            xml=ET.Element("server_action"),
        )
        action = UpnpServerAction(action_info, args)
        action.async_handle = func  # type: ignore
        action.service = self
        self.actions[name] = action
        return action

    async def async_handle_action(self, action_name: str, **kwargs: Any) -> Any:
        """Handle action."""
        action = cast(UpnpServerAction, self.actions[action_name])
        action.validate_arguments(**kwargs)
        return await action.async_handle(**kwargs)

    def add_subscriber(self, subscriber: EventSubscriber) -> None:
        """Add or update a subscriber."""
        self._subscribers.append(subscriber)

    def del_subscriber(self, sid: str) -> bool:
        """Delete a subscriber."""
        subscriber = self.get_subscriber(sid)
        if subscriber:
            self._subscribers.remove(subscriber)
            return True
        return False

    def get_subscriber(self, sid: str) -> Optional[EventSubscriber]:
        """Get matching subscriber (if any)."""
        for subscriber in self._subscribers:
            if subscriber.uuid == sid:
                return subscriber
        return None

    async def async_send_events(
        self, subscriber: Optional[EventSubscriber] = None
    ) -> None:
        """Send event updates to any subscribers."""
        if not subscriber:
            now = datetime.now()
            self._subscribers = [
                _sub for _sub in self._subscribers if now < _sub.expiration
            ]
            subscribers = self._subscribers
            if not self._subscribers:
                return
        else:
            subscribers = [subscriber]
        event_el = ET.Element("e:propertyset")
        event_el.set("xmlns:e", "urn:schemas-upnp-org:event-1-0")
        for state_var in self.state_variables.values():
            if not isinstance(state_var, UpnpEventableStateVariable):
                continue
            prop_el = ET.SubElement(event_el, "e:property")
            ET.SubElement(prop_el, state_var.name).text = str(state_var.value)
        message = (
            '<?xml version="1.0"?>\n' + ET.tostring(event_el, encoding="utf-8").decode()
        )

        headers = {
            "CONTENT-TYPE": 'text/xml; charset="utf-8"',
            "NT": "upnp:event",
            "NTS": "upnp:propchange",
        }
        tasks = []
        for sub in subscribers:
            hdr = headers.copy()
            hdr["SID"] = sub.uuid
            hdr["SEQ"] = str(sub.get_next_seq())
            tasks.append(
                self.requester.async_http_request(
                    HttpRequest("NOTIFY", sub.url, headers=hdr, body=message)
                )
            )
        await asyncio.gather(*tasks)


class UpnpServerDevice(UpnpDevice):
    """UPnP Device representation."""

    DEVICE_DEFINITION: DeviceInfo
    EMBEDDED_DEVICES: Sequence[Type["UpnpServerDevice"]]
    SERVICES: Sequence[Type[UpnpServerService]]
    ROUTES: Optional[Sequence[RouteDef]] = None

    def __init__(
        self,
        requester: UpnpRequester,
        base_uri: str,
        boot_id: int = 1,
        config_id: int = 1,
    ) -> None:
        """Initialize."""
        services = [service_type(requester=requester) for service_type in self.SERVICES]
        embedded_devices = [
            device_type(
                requester=requester,
                base_uri=base_uri,
                boot_id=boot_id,
                config_id=config_id,
            )
            for device_type in self.EMBEDDED_DEVICES
        ]
        super().__init__(
            requester=requester,
            device_info=self.DEVICE_DEFINITION,
            services=services,
            embedded_devices=embedded_devices,
        )
        self.base_uri = base_uri
        self.host = urlparse(base_uri).hostname
        self.boot_id = boot_id
        self.config_id = config_id


class SsdpSearchResponder:
    """SSDP SEARCH responder."""

    def __init__(
        self,
        device: UpnpServerDevice,
        source: Optional[AddressTupleVXType] = None,
        target: Optional[AddressTupleVXType] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Init the ssdp search responder class."""
        self.device = device
        self.source, self.target = determine_source_target(source, target)
        self.options = options or {}

        self._transport: Optional[DatagramTransport] = None
        self._response_socket: Optional[socket.socket] = None
        self._loop = asyncio.get_running_loop()

    def _on_connect(self, transport: DatagramTransport) -> None:
        """Handle on connect."""
        self._transport = transport

    def _on_data(
        self,
        request_line: str,
        headers: CaseInsensitiveDict,
    ) -> None:
        """Handle data."""
        # pylint: disable=too-many-branches
        assert self._transport

        if (
            request_line != "M-SEARCH * HTTP/1.1"
            or headers.get_lower("man") != SSDP_DISCOVER
        ):
            return

        remote_addr = headers.get_lower("_remote_addr")
        debug = _LOGGER.isEnabledFor(logging.DEBUG)
        if debug:  # pragma: no branch
            _LOGGER.debug(
                "Received M-SEARCH from: %s, headers: %s", remote_addr, headers
            )

        mx_header = headers.get_lower("mx")
        delay = 0
        if mx_header is not None:
            try:
                delay = min(5, int(mx_header))
                if debug:  # pragma: no branch
                    _LOGGER.debug("Deferring response for %d seconds", delay)
            except ValueError:
                pass

        if not (responses := self._build_responses(headers)):
            return

        remote_addr = headers.get_lower("_remote_addr")
        if delay:
            # The delay should be random between 0 and MX.
            # We use between 0.100 and MX-0.250 seconds to avoid
            # flooding the network with simultaneous responses.
            #
            # We do not set the upper limit to exactly MX seconds
            # because it might take up to 0.250 seconds to send the
            # response, and we want to avoid sending the response
            # after the MX timeout.
            self._loop.call_at(
                self._loop.time() + randrange(100, (delay * 1000) - 250) / 1000,
                self._send_responses,
                remote_addr,
                responses,
            )
        self._send_responses(remote_addr, responses)

    def _build_responses(self, headers: CaseInsensitiveDict) -> List[bytes]:
        # Determine how we should respond, page 1.3.2 of UPnP-arch-DeviceArchitecture-v2.0.
        st_header: str = headers.get_lower("st", "")
        search_target = st_header.lower()
        responses: List[bytes] = []

        if search_target == SSDP_ST_ALL:
            # 3 + 2d + k (d: embedded device, k: service)
            # global:      ST: upnp:rootdevice
            #              USN: uuid:device-UUID::upnp:rootdevice
            # per device : ST: uuid:device-UUID
            #              USN: uuid:device-UUID
            # per device : ST: urn:schemas-upnp-org:device:deviceType:ver
            #              USN: uuid:device-UUID::urn:schemas-upnp-org:device:deviceType:ver
            # per service: ST: urn:schemas-upnp-org:service:serviceType:ver
            #              USN: uuid:device-UUID::urn:schemas-upnp-org:service:serviceType:ver
            all_devices = self.device.all_devices
            all_services = self.device.all_services
            responses.append(self._build_response_rootdevice())
            responses.extend(
                self._build_responses_device_udn(device) for device in all_devices
            )
            responses.extend(
                self._build_responses_device_type(device) for device in all_devices
            )
            responses.extend(
                self._build_responses_service(service) for service in all_services
            )
        elif search_target == SSDP_ST_ROOTDEVICE:
            responses.append(self._build_response_rootdevice())
        elif matched_devices := self.device.get_devices_matching_udn(search_target):
            responses.extend(
                self._build_responses_device_udn(device) for device in matched_devices
            )
        elif matched_devices := self._matched_devices_by_type(search_target):
            responses.extend(
                self._build_responses_device_type(device, search_target)
                for device in matched_devices
            )
        elif matched_services := self._matched_services_by_type(search_target):
            responses.extend(
                self._build_responses_service(service, search_target)
                for service in matched_services
            )

        if self.options.get(SSDP_SEARCH_RESPONDER_OPTION_ALWAYS_REPLY_WITH_ROOT_DEVICE):
            responses.append(self._build_response_rootdevice())

        return responses

    @staticmethod
    def _match_type_versions(type_ver: str, search_target: str) -> bool:
        """Determine if any service/device type up to the max version matches search_target."""
        # As per 1.3.2 of the UPnP Device Architecture spec, all device service types
        # must respond to and be backwards-compatible with older versions of the same type
        type_ver_lower: str = type_ver.lower()
        try:
            base, max_ver = type_ver_lower.rsplit(":", 1)
            max_ver_i = int(max_ver)
            for ver in range(max_ver_i + 1):
                if f"{base}:{ver}" == search_target:
                    return True
        except ValueError:
            if type_ver_lower == search_target:
                return True
        return False

    def _matched_devices_by_type(self, search_target: str) -> List[UpnpDevice]:
        """Get matched devices by device type."""
        return [
            device
            for device in self.device.all_devices
            if self._match_type_versions(device.device_type, search_target)
        ]

    def _matched_services_by_type(self, search_target: str) -> List[UpnpService]:
        """Get matched services by service type."""
        return [
            service
            for service in self.device.all_services
            if self._match_type_versions(service.service_type, search_target)
        ]

    async def async_start(self) -> None:
        """Start."""
        _LOGGER.debug("Start listening for search requests")

        # Create response socket.
        self._response_socket, _source, _target = get_ssdp_socket(
            self.source, self.target
        )

        # Construct a socket for use with this pair of endpoints.
        sock, _source, _target = get_ssdp_socket(self.source, self.target)

        # Bind to address.
        address = ("", self.target[1])
        _LOGGER.debug("Binding socket, socket: %s, address: %s", sock, address)
        sock.bind(address)

        # Create protocol and send discovery packet.
        loop = asyncio.get_event_loop()
        await loop.create_datagram_endpoint(
            lambda: SsdpProtocol(
                loop,
                on_connect=self._on_connect,
                on_data=self._on_data,
            ),
            sock=sock,
        )

    async def async_stop(self) -> None:
        """Stop listening for advertisements."""
        assert self._transport

        _LOGGER.debug("Stop listening for SEARCH requests")
        self._transport.close()

    def _build_response_rootdevice(self) -> bytes:
        """Send root device response."""
        return self._build_response(
            "upnp:rootdevice", f"{self.device.udn}::upnp:rootdevice"
        )

    def _build_responses_device_udn(self, device: UpnpDevice) -> bytes:
        """Send device responses for UDN."""
        return self._build_response(device.udn, f"{self.device.udn}")

    def _build_responses_device_type(
        self, device: UpnpDevice, device_type: Optional[str] = None
    ) -> bytes:
        """Send device responses for device type."""
        return self._build_response(
            device_type or device.device_type,
            f"{self.device.udn}::{device.device_type}",
        )

    def _build_responses_service(
        self, service: UpnpService, service_type: Optional[str] = None
    ) -> bytes:
        """Send service responses."""
        return self._build_response(
            service_type or service.service_type,
            f"{self.device.udn}::{service.service_type}",
        )

    def _build_response(
        self,
        service_type: str,
        unique_service_name: str,
    ) -> bytes:
        """Send a response."""
        return build_ssdp_packet(
            "HTTP/1.1 200 OK",
            {
                "CACHE-CONTROL": HEADER_CACHE_CONTROL,
                "DATE": format_date_time(time.time()),
                "SERVER": HEADER_SERVER,
                "ST": service_type,
                "USN": unique_service_name,
                "EXT": "",
                "LOCATION": f"{self.device.base_uri}{self.device.device_url}",
                "BOOTID.UPNP.ORG": str(self.device.boot_id),
                "CONFIGID.UPNP.ORG": str(self.device.config_id),
            },
        )

    def _send_responses(self, remote_addr: str, responses: List[bytes]) -> None:
        """Send responses."""
        if _LOGGER.isEnabledFor(logging.DEBUG):  # pragma: no branch
            _LOGGER.debug(
                "Sending SSDP packet, transport: %s, socket: %s, target: %s",
                None,
                self._response_socket,
                remote_addr,
            )
        _LOGGER_TRAFFIC_SSDP.debug(
            "Sending SSDP packets, target: %s, data: %s", remote_addr, responses
        )
        assert self._response_socket, "Socket not initialized"
        for response in responses:
            self._response_socket.sendto(response, remote_addr)


def _build_advertisements(
    target: AddressTupleVXType,
    root_device: UpnpServerDevice,
    nts: NotificationSubType = NotificationSubType.SSDP_ALIVE,
) -> List[CaseInsensitiveDict]:
    """Build advertisements to be sent for a UpnpDevice."""
    # 3 + 2d + k (d: embedded device, k: service)
    # global:      ST: upnp:rootdevice
    #              USN: uuid:device-UUID::upnp:rootdevice
    # per device : ST: uuid:device-UUID
    #              USN: uuid:device-UUID
    # per device : ST: urn:schemas-upnp-org:device:deviceType:ver
    #              USN: uuid:device-UUID::urn:schemas-upnp-org:device:deviceType:ver
    # per service: ST: urn:schemas-upnp-org:service:serviceType:ver
    #              USN: uuid:device-UUID::urn:schemas-upnp-org:service:serviceType:ver
    advertisements: List[CaseInsensitiveDict] = []

    host = (
        f"[{target[0]}]:{target[1]}"
        if is_ipv6_address(target)
        else f"{target[0]}:{target[1]}"
    )
    base_headers = {
        "NTS": nts.value,
        "HOST": host,
        "CACHE-CONTROL": HEADER_CACHE_CONTROL,
        "SERVER": HEADER_SERVER,
        "BOOTID.UPNP.ORG": str(root_device.boot_id),
        "CONFIGID.UPNP.ORG": str(root_device.config_id),
        "LOCATION": f"{root_device.base_uri}{root_device.device_url}",
    }

    # root device
    advertisements.append(
        CaseInsensitiveDict(
            base_headers,
            NT="upnp:rootdevice",
            USN=f"{root_device.udn}::upnp:rootdevice",
        )
    )

    for device in root_device.all_devices:
        advertisements.append(
            CaseInsensitiveDict(
                base_headers,
                NT=f"{device.udn}",
                USN=f"{device.udn}",
            )
        )
        advertisements.append(
            CaseInsensitiveDict(
                base_headers,
                NT=f"{device.device_type}",
                USN=f"{device.udn}::{device.device_type}",
            )
        )

    for service in root_device.all_services:
        advertisements.append(
            CaseInsensitiveDict(
                base_headers,
                NT=f"{service.service_type}",
                USN=f"{service.device.udn}::{service.service_type}",
            )
        )

    return advertisements


class SsdpAdvertisementAnnouncer:
    """SSDP Advertisement announcer."""

    # pylint: disable=too-many-instance-attributes

    ANNOUNCE_INTERVAL = timedelta(seconds=30)

    def __init__(
        self,
        device: UpnpServerDevice,
        source: Optional[AddressTupleVXType] = None,
        target: Optional[AddressTupleVXType] = None,
        options: Optional[Dict[str, Any]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Init the ssdp search responder class."""
        # pylint: disable=too-many-arguments
        self.device = device
        self.source, self.target = determine_source_target(source, target)
        self.options = options or {}
        self.loop = loop or asyncio.get_event_loop()

        self._transport: Optional[DatagramTransport] = None
        advertisements = _build_advertisements(self.target, device)
        self._advertisements = cycle(advertisements)
        self._cancel_announce: Optional[asyncio.TimerHandle] = None

    def _on_connect(self, transport: DatagramTransport) -> None:
        """Handle on connect."""
        self._transport = transport

    async def async_start(self) -> None:
        """Start."""
        _LOGGER.debug("Start advertisements announcer")

        # Construct a socket for use with this pairs of endpoints.
        sock, _source, _target = get_ssdp_socket(self.source, self.target)
        if sys.platform.startswith("win32"):
            address = self.source
            _LOGGER.debug("Binding socket, socket: %s, address: %s", sock, address)
            sock.bind(address)

        # Create protocol and send discovery packet.
        loop = asyncio.get_event_loop()
        await loop.create_datagram_endpoint(
            lambda: SsdpProtocol(
                loop,
                on_connect=self._on_connect,
            ),
            sock=sock,
        )

        # Announce and reschedule self.
        self._announce_next()

    async def async_stop(self) -> None:
        """Stop listening for advertisements."""
        assert self._transport

        sock: Optional[socket.socket] = self._transport.get_extra_info("socket")
        _LOGGER.debug(
            "Stop advertisements announcer, transport: %s, socket: %s",
            self._transport,
            sock,
        )

        if self._cancel_announce is not None:
            self._cancel_announce.cancel()

        self._send_byebyes()
        self._transport.close()

    def _announce_next(self) -> None:
        """Announce next advertisement."""
        _LOGGER.debug("Announcing")
        assert self._transport

        protocol = cast(SsdpProtocol, self._transport.get_protocol())
        # Protocol can be None when it is not yet initialized.
        if protocol:
            start_line = "NOTIFY * HTTP/1.1"
            headers = next(self._advertisements)
            packet = build_ssdp_packet(start_line, headers)

            _LOGGER.debug(
                "Sending advertisement, NTS: %s, NT: %s, USN: %s",
                headers["NTS"],
                headers["NT"],
                headers["USN"],
            )
            protocol.send_ssdp_packet(packet, self.target)

        # Reschedule self.
        self._cancel_announce = self.loop.call_later(
            SsdpAdvertisementAnnouncer.ANNOUNCE_INTERVAL.total_seconds(),
            self._announce_next,
        )

    def _send_byebyes(self) -> None:
        """Send ssdp:byebye."""
        assert self._transport

        start_line = "NOTIFY * HTTP/1.1"
        advertisements = _build_advertisements(
            self.target, self.device, NotificationSubType.SSDP_BYEBYE
        )
        for headers in advertisements:
            packet = build_ssdp_packet(start_line, headers)
            protocol = cast(SsdpProtocol, self._transport.get_protocol())
            _LOGGER.debug(
                "Sending advertisement, NTS: %s, NT: %s, USN: %s",
                headers["NTS"],
                headers["NT"],
                headers["USN"],
            )
            protocol.send_ssdp_packet(packet, self.target)


class UpnpXmlSerializer:
    """Helper class to create device/service description from UpnpDevice/UpnpService."""

    # pylint: disable=too-few-public-methods

    @classmethod
    def to_xml(cls, thing: Union[UpnpDevice, UpnpService]) -> ET.Element:
        """Convert thing to XML."""
        if isinstance(thing, UpnpDevice):
            return cls._device_to_xml(thing)
        if isinstance(thing, UpnpService):
            return cls._service_to_xml(thing)

        raise NotImplementedError()

    @classmethod
    def _device_to_xml(cls, device: UpnpDevice) -> ET.Element:
        """Convert device to device description XML."""
        root_el = ET.Element("root", xmlns="urn:schemas-upnp-org:device-1-0")
        spec_version_el = ET.SubElement(root_el, "specVersion")
        ET.SubElement(spec_version_el, "major").text = "1"
        ET.SubElement(spec_version_el, "minor").text = "0"

        device_el = cls._device_to_xml_bare(device)
        root_el.append(device_el)

        return root_el

    @classmethod
    def _device_to_xml_bare(cls, device: UpnpDevice) -> ET.Element:
        """Convert device to XML, without the root-element."""
        device_el = ET.Element("device", xmlns="urn:schemas-upnp-org:device-1-0")
        ET.SubElement(device_el, "deviceType").text = device.device_type
        ET.SubElement(device_el, "friendlyName").text = device.friendly_name
        ET.SubElement(device_el, "manufacturer").text = device.manufacturer
        ET.SubElement(device_el, "manufacturerURL").text = device.manufacturer_url
        ET.SubElement(device_el, "modelDescription").text = device.model_description
        ET.SubElement(device_el, "modelName").text = device.model_name
        ET.SubElement(device_el, "modelNumber").text = device.model_number
        ET.SubElement(device_el, "modelURL").text = device.model_url
        ET.SubElement(device_el, "serialNumber").text = device.serial_number
        ET.SubElement(device_el, "UDN").text = device.udn
        ET.SubElement(device_el, "UPC").text = device.upc
        ET.SubElement(device_el, "presentationURL").text = device.presentation_url

        icon_list_el = ET.SubElement(device_el, "iconList")
        for icon in device.icons:
            icon_el = ET.SubElement(icon_list_el, "icon")
            ET.SubElement(icon_el, "mimetype").text = icon.mimetype
            ET.SubElement(icon_el, "width").text = str(icon.width)
            ET.SubElement(icon_el, "height").text = str(icon.height)
            ET.SubElement(icon_el, "depth").text = str(icon.depth)
            ET.SubElement(icon_el, "url").text = icon.url

        service_list_el = ET.SubElement(device_el, "serviceList")
        for service in device.services.values():
            service_el = ET.SubElement(service_list_el, "service")
            ET.SubElement(service_el, "serviceType").text = service.service_type
            ET.SubElement(service_el, "serviceId").text = service.service_id
            ET.SubElement(service_el, "controlURL").text = service.control_url
            ET.SubElement(service_el, "eventSubURL").text = service.event_sub_url
            ET.SubElement(service_el, "SCPDURL").text = service.scpd_url

        device_list_el = ET.SubElement(device_el, "deviceList")
        for embedded_device in device.embedded_devices.values():
            embedded_device_el = cls._device_to_xml_bare(embedded_device)
            device_list_el.append(embedded_device_el)

        return device_el

    @classmethod
    def _service_to_xml(cls, service: UpnpService) -> ET.Element:
        """Convert service to service description XML."""
        scpd_el = ET.Element("scpd", xmlns="urn:schemas-upnp-org:service-1-0")
        spec_version_el = ET.SubElement(scpd_el, "specVersion")
        ET.SubElement(spec_version_el, "major").text = "1"
        ET.SubElement(spec_version_el, "minor").text = "0"

        action_list_el = ET.SubElement(scpd_el, "actionList")
        for action in service.actions.values():
            action_el = cls._action_to_xml(action)
            action_list_el.append(action_el)

        state_table_el = ET.SubElement(scpd_el, "serviceStateTable")
        for state_var in service.state_variables.values():
            state_var_el = cls._state_variable_to_xml(state_var)
            state_table_el.append(state_var_el)

        return scpd_el

    @classmethod
    def _action_to_xml(cls, action: UpnpAction) -> ET.Element:
        """Convert action to service description XML."""
        action_el = ET.Element("action")
        ET.SubElement(action_el, "name").text = action.name

        if action.arguments:
            arg_list_el = ET.SubElement(action_el, "argumentList")
            for arg in action.in_arguments():
                arg_el = cls._action_argument_to_xml(arg)
                arg_list_el.append(arg_el)
            for arg in action.out_arguments():
                arg_el = cls._action_argument_to_xml(arg)
                arg_list_el.append(arg_el)

        return action_el

    @classmethod
    def _action_argument_to_xml(cls, argument: UpnpAction.Argument) -> ET.Element:
        """Convert action argument to service description XML."""
        arg_el = ET.Element("argument")
        ET.SubElement(arg_el, "name").text = argument.name
        ET.SubElement(arg_el, "direction").text = argument.direction
        ET.SubElement(arg_el, "relatedStateVariable").text = (
            argument.related_state_variable.name
        )
        return arg_el

    @classmethod
    def _state_variable_to_xml(cls, state_variable: UpnpStateVariable) -> ET.Element:
        """Convert state variable to service description XML."""
        state_var_el = ET.Element(
            "stateVariable", sendEvents="yes" if state_variable.send_events else "no"
        )
        ET.SubElement(state_var_el, "name").text = state_variable.name
        ET.SubElement(state_var_el, "dataType").text = state_variable.data_type

        if state_variable.allowed_values:
            value_list_el = ET.SubElement(state_var_el, "allowedValueList")
            for allowed_value in state_variable.allowed_values:
                ET.SubElement(value_list_el, "allowedValue").text = str(allowed_value)

        if None not in (state_variable.min_value, state_variable.max_value):
            value_range_el = ET.SubElement(state_var_el, "allowedValueRange")
            ET.SubElement(value_range_el, "minimum").text = str(
                state_variable.min_value
            )
            ET.SubElement(value_range_el, "maximum").text = str(
                state_variable.max_value
            )

        if state_variable.default_value is not None:
            ET.SubElement(state_var_el, "defaultValue").text = str(
                state_variable.default_value
            )

        return state_var_el


def callable_action(
    name: str, in_args: Mapping[str, str], out_args: Mapping[str, str]
) -> Callable:
    """Declare method as a callable UpnpAction."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        setattr(wrapper, "__upnp_action__", [name, in_args, out_args])

        return wrapper

    return decorator


async def _parse_action_body(
    service: UpnpServerService, request: Request
) -> Tuple[str, Dict[str, Any]]:
    """Parse action body."""
    # Parse call.
    soap_action = request.headers.get("SOAPAction", "").strip('"')
    try:
        _, action_name = soap_action.split("#")
        data = await request.text()
        root_el: ET.Element = DET.fromstring(data)
        body_el = root_el.find("s:Body", NAMESPACES)
        assert body_el
        rpc_el = body_el[0]
    except Exception as exc:
        raise HTTPBadRequest(reason="InvalidSoap") from exc

    if action_name not in service.actions:
        raise HTTPBadRequest(reason="InvalidAction")

    kwargs: Dict[str, Any] = {}
    action = service.action(action_name)
    for arg in rpc_el:
        action_arg = action.argument(arg.tag, direction="in")
        if action_arg is None:
            raise HTTPBadRequest(reason="InvalidActionArgument")
        state_var = action_arg.related_state_variable
        kwargs[arg.tag] = state_var.coerce_python(arg.text or "")

    return action_name, kwargs


def _create_action_response(
    service: UpnpServerService, action_name: str, result: Dict[str, Any]
) -> Response:
    """Create action call response."""
    envelope_el = ET.Element(
        "s:Envelope",
        attrib={
            "xmlns:s": NAMESPACES["s"],
            "s:encodingStyle": NAMESPACES["es"],
        },
    )
    body_el = ET.SubElement(envelope_el, "s:Body")

    response_el = ET.SubElement(
        body_el, f"st:{action_name}Response", attrib={"xmlns:st": service.service_type}
    )
    out_state_vars = {
        var.name: var.related_state_variable
        for var in service.actions[action_name].out_arguments()
    }
    for key, value in result.items():
        if isinstance(value, UpnpStateVariable):
            ET.SubElement(response_el, key).text = value.upnp_value
        else:
            template_var = out_state_vars[key]
            template_var.validate_value(value)
            ET.SubElement(response_el, key).text = template_var.coerce_upnp(value)
    return Response(
        content_type="text/xml",
        charset="utf-8",
        body=ET.tostring(envelope_el, encoding="utf-8"),
    )


def _create_error_action_response(
    exception: UpnpError,
) -> Response:
    """Create action call response."""
    envelope_el = ET.Element(
        "s:Envelope",
        attrib={
            "xmlns:s": NAMESPACES["s"],
            "s:encodingStyle": NAMESPACES["es"],
        },
    )
    body_el = ET.SubElement(envelope_el, "s:Body")
    fault_el = ET.SubElement(body_el, "s:Fault")
    ET.SubElement(fault_el, "faultcode").text = "s:Client"
    ET.SubElement(fault_el, "faultstring").text = "UPnPError"
    detail_el = ET.SubElement(fault_el, "detail")
    error_el = ET.SubElement(
        detail_el, "UPnPError", xmlns="urn:schemas-upnp-org:control-1-0"
    )
    error_code = (
        exception.error_code or UpnpActionErrorCode.ACTION_FAILED.value
        if isinstance(exception, UpnpActionError)
        else 402 if isinstance(exception, UpnpValueError) else 501
    )
    ET.SubElement(error_el, "errorCode").text = str(error_code)
    ET.SubElement(error_el, "errorDescription").text = "Action Failed"

    return Response(
        status=500,
        content_type="text/xml",
        charset="utf-8",
        body=ET.tostring(envelope_el, encoding="utf-8"),
    )


async def action_handler(service: UpnpServerService, request: Request) -> Response:
    """Handle action."""
    action_name, kwargs = await _parse_action_body(service, request)

    # Do call.
    try:
        call_result = await service.async_handle_action(action_name, **kwargs)
    except UpnpValueError as exc:
        return _create_error_action_response(exc)
    except UpnpActionError as exc:
        return _create_error_action_response(exc)

    return _create_action_response(service, action_name, call_result)


async def subscribe_handler(service: UpnpServerService, request: Request) -> Response:
    """SUBSCRIBE handler."""
    callback_url = request.headers.get("CALLBACK", None)
    timeout = request.headers.get("TIMEOUT", None)
    sid = request.headers.get("SID", None)

    timeout_val = None
    if timeout is not None:
        try:
            timeout_val = int(timeout.lower().replace("second-", ""))
        except ValueError:
            return Response(status=400)

    subscriber = None
    if sid:
        subscriber = service.get_subscriber(sid)
        if subscriber:
            subscriber.timeout = timeout_val
    else:
        if callback_url:
            # callback url is specified as <http://...>
            # remove the outside <>
            callback_url = callback_url[1:-1]
            subscriber = EventSubscriber(callback_url, timeout_val)

    if not subscriber:
        return Response(status=404)

    headers = {
        "DATE": format_date_time(mktime(datetime.now().timetuple())),
        "SERVER": HEADER_SERVER,
        "SID": subscriber.uuid,
        "TIMEOUT": str(subscriber.timeout),
    }
    resp = Response(status=200, headers=headers)
    if sid is None:
        # this is an initial subscription.  Need to send state-vars
        # AFTER response completion
        await resp.prepare(request)
        await resp.write_eof()
        await service.async_send_events(subscriber)
        service.add_subscriber(subscriber)
    return resp


async def unsubscribe_handler(service: UpnpServerService, request: Request) -> Response:
    """UNSUBSCRIBE handler."""
    sid = request.headers.get("SID", None)
    if sid:
        if service.del_subscriber(sid):
            return Response(status=200)
    return Response(status=412)


async def to_xml(
    thing: Union[UpnpServerDevice, UpnpServerService], _request: Request
) -> Response:
    """Construct device/service description."""
    serializer = UpnpXmlSerializer()
    thing_el = serializer.to_xml(thing)
    encoding = "utf-8"
    thing_xml = ET.tostring(thing_el, encoding=encoding)
    return Response(content_type="text/xml", charset=encoding, body=thing_xml)


def create_state_var(
    data_type: str,
    *,
    allowed: Optional[List[str]] = None,
    allowed_range: Optional[Mapping[str, Optional[str]]] = None,
    default: Optional[str] = None,
) -> StateVariableTypeInfo:
    """Create state variables."""
    return StateVariableTypeInfo(
        data_type=data_type,
        data_type_mapping=STATE_VARIABLE_TYPE_MAPPING[data_type],
        default_value=default,
        allowed_value_range=allowed_range or {},
        allowed_values=allowed,
        xml=ET.Element("server_stateVariable"),
    )


def create_event_var(
    data_type: str,
    *,
    allowed: Optional[List[str]] = None,
    allowed_range: Optional[Mapping[str, Optional[str]]] = None,
    default: Optional[str] = None,
    max_rate: Optional[float] = None,
) -> StateVariableTypeInfo:
    """Create event variables."""
    return cast(
        StateVariableTypeInfo,
        EventableStateVariableTypeInfo(
            data_type=data_type,
            data_type_mapping=STATE_VARIABLE_TYPE_MAPPING[data_type],
            default_value=default,
            allowed_value_range=allowed_range or {},
            allowed_values=allowed,
            max_rate=max_rate,
            xml=ET.Element("server_stateVariable"),
        ),
    )


class UpnpServer:
    """UPnP Server."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        server_device: Type[UpnpServerDevice],
        source: AddressTupleVXType,
        target: Optional[AddressTupleVXType] = None,
        http_port: Optional[int] = None,
        boot_id: int = 1,
        config_id: int = 1,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        self.server_device = server_device
        self.source, self.target = determine_source_target(source, target)
        self.http_port = http_port
        self.boot_id = boot_id
        self.config_id = config_id
        self.options = options or {}

        self.base_uri: Optional[str] = None
        self._device: Optional[UpnpServerDevice] = None
        self._site: Optional[TCPSite] = None
        self._search_responder: Optional[SsdpSearchResponder] = None
        self._advertisement_announcer: Optional[SsdpAdvertisementAnnouncer] = None

    async def async_start(self) -> None:
        """Start."""
        self._create_device()
        await self._async_start_http_server()
        await self._async_start_ssdp()

    def _create_device(self) -> None:
        """Create device."""
        requester = AiohttpRequester()
        is_ipv6 = ":" in self.source[0]
        self.base_uri = (
            f"http://[{self.source[0]}]:{self.http_port}"
            if is_ipv6
            else f"http://{self.source[0]}:{self.http_port}"
        )
        self._device = self.server_device(
            requester, self.base_uri, self.boot_id, self.config_id
        )

    async def _async_start_http_server(self) -> None:
        """Start http server."""
        assert self._device

        # Build app.
        app = Application()
        app.router.add_get(self._device.device_url, partial(to_xml, self._device))

        for service in self._device.all_services:
            service = cast(UpnpServerService, service)
            app.router.add_get(
                service.SERVICE_DEFINITION.scpd_url, partial(to_xml, service)
            )
            app.router.add_post(
                service.SERVICE_DEFINITION.control_url, partial(action_handler, service)
            )
            app.router.add_route(
                "SUBSCRIBE",
                service.SERVICE_DEFINITION.event_sub_url,
                partial(subscribe_handler, service),
            )
            app.router.add_route(
                "UNSUBSCRIBE",
                service.SERVICE_DEFINITION.event_sub_url,
                partial(unsubscribe_handler, service),
            )

        if self._device.ROUTES:
            app.router.add_routes(self._device.ROUTES)

        # Create AppRunner.
        runner = AppRunner(app, access_log=_LOGGER_TRAFFIC_UPNP)
        await runner.setup()

        # Launch TCP handler.
        is_ipv6 = ":" in self.source[0]
        host = f"{self.source[0]}%{self.source[3]}" if is_ipv6 else self.source[0]  # type: ignore
        self._site = TCPSite(runner, host, self.http_port, reuse_address=True)
        await self._site.start()

        assert self._device
        _LOGGER.debug(
            "Device listening at %s%s", self._site.name, self._device.device_url
        )

    async def _async_start_ssdp(self) -> None:
        """Start SSDP handling."""
        _LOGGER.debug(
            "Starting SSDP handling, source: %s, target: %s", self.source, self.target
        )
        assert self._device
        self._search_responder = SsdpSearchResponder(
            self._device,
            source=self.source,
            target=self.target,
            options=self.options.get(SSDP_SEARCH_RESPONDER_OPTIONS),
        )
        self._advertisement_announcer = SsdpAdvertisementAnnouncer(
            self._device,
            source=self.source,
            target=self.target,
            options=self.options.get(SSDP_ADVERTISEMENT_ANNOUNCER_OPTIONS),
        )

        await self._search_responder.async_start()
        await self._advertisement_announcer.async_start()

    async def async_stop(self) -> None:
        """Stop server."""
        await self._async_stop_ssdp()
        await self._async_stop_http_server()

    async def _async_stop_ssdp(self) -> None:
        """Stop SSDP handling."""
        if self._advertisement_announcer:
            await self._advertisement_announcer.async_stop()
        if self._search_responder:
            await self._search_responder.async_stop()

    async def _async_stop_http_server(self) -> None:
        """Stop HTTP server."""
        if self._site:
            await self._site.stop()
