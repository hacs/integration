# -*- coding: utf-8 -*-
"""async_upnp_client.client module."""

# pylint: disable=too-many-lines

import io
import logging
import urllib.parse
from abc import ABC
from datetime import datetime, timezone
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
)
from xml.etree import ElementTree as ET
from xml.parsers import expat
from xml.sax.saxutils import escape

import defusedxml.ElementTree as DET
import voluptuous as vol

from async_upnp_client.const import (
    NS,
    ActionArgumentInfo,
    ActionInfo,
    DeviceIcon,
    DeviceInfo,
    HttpRequest,
    HttpResponse,
    ServiceInfo,
    StateVariableInfo,
)
from async_upnp_client.exceptions import (
    UpnpActionError,
    UpnpActionResponseError,
    UpnpError,
    UpnpResponseError,
    UpnpValueError,
    UpnpXmlParseError,
)
from async_upnp_client.utils import CaseInsensitiveDict

_LOGGER = logging.getLogger(__name__)


EventCallbackType = Callable[["UpnpService", Sequence["UpnpStateVariable"]], None]


def default_on_pre_receive_device_spec(request: HttpRequest) -> HttpRequest:
    """Pre-receive device specification hook."""
    # pylint: disable=unused-argument
    return request


def default_on_post_receive_device_spec(response: HttpResponse) -> HttpResponse:
    """Post-receive device specification hook."""
    # pylint: disable=unused-argument
    fixed_body = (response.body or "").rstrip(" \t\r\n\0")
    return HttpResponse(response.status_code, response.headers, fixed_body)


def default_on_pre_receive_service_spec(request: HttpRequest) -> HttpRequest:
    """Pre-receive service specification hook."""
    # pylint: disable=unused-argument
    return request


def default_on_post_receive_service_spec(response: HttpResponse) -> HttpResponse:
    """Post-receive service specification hook."""
    # pylint: disable=unused-argument
    fixed_body = (response.body or "").rstrip(" \t\r\n\0")
    return HttpResponse(response.status_code, response.headers, fixed_body)


def default_on_pre_call_action(
    action: "UpnpAction", args: Mapping[str, Any], request: HttpRequest
) -> HttpRequest:
    """Pre-action call hook."""
    # pylint: disable=unused-argument
    return request


def default_on_post_call_action(
    action: "UpnpAction", response: HttpResponse
) -> HttpResponse:
    """Post-action call hook."""
    # pylint: disable=unused-argument
    fixed_body = (response.body or "").rstrip(" \t\r\n\0")
    return HttpResponse(response.status_code, response.headers, fixed_body)


class DisableXmlNamespaces:
    """Context manager to disable XML namespace handling."""

    def __enter__(self) -> None:
        """Enter context manager."""
        # pylint: disable=attribute-defined-outside-init
        self._old_parser_create = expat.ParserCreate

        def expat_parser_create(
            encoding: Optional[str] = None,
            namespace_separator: Optional[str] = None,
            intern: Optional[Dict[str, Any]] = None,
        ) -> expat.XMLParserType:
            # pylint: disable=unused-argument
            return self._old_parser_create(encoding, None, intern)

        expat.ParserCreate = expat_parser_create

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Exit context manager."""
        expat.ParserCreate = self._old_parser_create


class UpnpRequester(ABC):
    """
    Abstract base class used for performing async HTTP requests.

    Implement method async_do_http_request() in your concrete class.
    """

    # pylint: disable=too-few-public-methods

    async def async_http_request(
        self,
        http_request: HttpRequest,
    ) -> HttpResponse:
        """Do a HTTP request."""
        raise NotImplementedError()


class UpnpDevice:
    """UPnP Device representation."""

    # pylint: disable=too-many-public-methods,too-many-instance-attributes

    def __init__(
        self,
        requester: UpnpRequester,
        device_info: DeviceInfo,
        services: Sequence["UpnpService"],
        embedded_devices: Sequence["UpnpDevice"],
        on_pre_receive_device_spec: Callable[
            [HttpRequest], HttpRequest
        ] = default_on_pre_receive_device_spec,
        on_post_receive_device_spec: Callable[
            [HttpResponse], HttpResponse
        ] = default_on_post_receive_device_spec,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        self.requester = requester
        self.device_info = device_info
        self.services = {service.service_type: service for service in services}
        self.embedded_devices = {
            embedded_device.device_type: embedded_device
            for embedded_device in embedded_devices
        }
        self.on_pre_receive_device_spec = on_pre_receive_device_spec
        self.on_post_receive_device_spec = on_post_receive_device_spec

        self._parent_device: Optional["UpnpDevice"] = None

        # bind services to ourselves
        for service in services:
            service.device = self

        # bind devices to ourselves
        for embedded_device in embedded_devices:
            embedded_device.parent_device = self

        # SSDP headers.
        self.ssdp_headers: CaseInsensitiveDict = CaseInsensitiveDict()

        # Just initialized, mark available.
        self.available = True

    @property
    def parent_device(self) -> Optional["UpnpDevice"]:
        """Get parent UpnpDevice, if any."""
        return self._parent_device

    @parent_device.setter
    def parent_device(self, parent_device: "UpnpDevice") -> None:
        """Set parent UpnpDevice."""
        if self._parent_device is not None:
            raise UpnpError("UpnpDevice already bound to UpnpDevice")

        self._parent_device = parent_device

    @property
    def root_device(self) -> "UpnpDevice":
        """Get the root device, or self if self is the root device."""
        if self._parent_device is None:
            return self

        return self._parent_device.root_device

    def find_device(self, device_type: str) -> Optional["UpnpDevice"]:
        """Find a (embedded) device with the given device_type."""
        if self.device_type == device_type:
            return self

        for embedded_device in self.embedded_devices.values():
            device = embedded_device.find_device(device_type)
            if device:
                return device

        return None

    def find_service(self, service_type: str) -> Optional["UpnpService"]:
        """Find a service with the give service_type."""
        if service_type in self.services:
            return self.services[service_type]

        for embedded_device in self.embedded_devices.values():
            service = embedded_device.find_service(service_type)
            if service:
                return service

        return None

    @property
    def all_devices(self) -> List["UpnpDevice"]:
        """Get all devices, self and embedded."""
        devices = [self]

        for embedded_device in self.embedded_devices.values():
            devices += embedded_device.all_devices

        return devices

    def get_devices_matching_udn(self, udn: str) -> List["UpnpDevice"]:
        """Get all devices matching udn."""
        devices: List["UpnpDevice"] = []

        if self.udn.lower() == udn:
            devices.append(self)

        for embedded_device in self.embedded_devices.values():
            devices += embedded_device.get_devices_matching_udn(udn)

        return devices

    @property
    def all_services(self) -> List["UpnpService"]:
        """Get all services, from self and embedded devices."""
        services: List["UpnpService"] = []

        for device in self.all_devices:
            services += device.services.values()

        return services

    def reinit(self, new_device: "UpnpDevice") -> None:
        """Reinitialize self from another device."""
        if self.device_type != new_device.device_type:
            raise UpnpError(
                f"Mismatch in device_type: {self.device_type} vs {new_device.device_type}"
            )

        self.device_info = new_device.device_info

        # reinit embedded devices
        for device_type, embedded_device in self.embedded_devices.items():
            new_embedded_device = new_device.embedded_devices[device_type]
            embedded_device.reinit(new_embedded_device)

    @property
    def name(self) -> str:
        """Get the name of this device."""
        return self.device_info.friendly_name

    @property
    def friendly_name(self) -> str:
        """Get the friendly name of this device, alias for name."""
        return self.device_info.friendly_name

    @property
    def manufacturer(self) -> str:
        """Get the manufacturer of this device."""
        return self.device_info.manufacturer

    @property
    def manufacturer_url(self) -> Optional[str]:
        """Get the manufacturer URL of this device."""
        return self.device_info.manufacturer_url

    @property
    def model_description(self) -> Optional[str]:
        """Get the model description of this device."""
        return self.device_info.model_description

    @property
    def model_name(self) -> str:
        """Get the model name of this device."""
        return self.device_info.model_name

    @property
    def model_number(self) -> Optional[str]:
        """Get the model number of this device."""
        return self.device_info.model_number

    @property
    def model_url(self) -> Optional[str]:
        """Get the model URL of this device."""
        return self.device_info.model_url

    @property
    def serial_number(self) -> Optional[str]:
        """Get the serial number of this device."""
        return self.device_info.serial_number

    @property
    def udn(self) -> str:
        """Get UDN of this device."""
        return self.device_info.udn

    @property
    def upc(self) -> Optional[str]:
        """Get UPC of this device."""
        return self.device_info.upc

    @property
    def presentation_url(self) -> Optional[str]:
        """Get presentationURL of this device."""
        return self.device_info.presentation_url

    @property
    def device_url(self) -> str:
        """Get the URL of this device."""
        return self.device_info.url

    @property
    def device_type(self) -> str:
        """Get the device type of this device."""
        return self.device_info.device_type

    @property
    def icons(self) -> Sequence[DeviceIcon]:
        """Get the icons for this device."""
        return self.device_info.icons

    @property
    def xml(self) -> ET.Element:
        """Get the XML description for this device."""
        return self.device_info.xml

    def has_service(self, service_type: str) -> bool:
        """Check if service by service_type is available."""
        return service_type in self.services

    def service(self, service_type: str) -> "UpnpService":
        """Get service by service_type."""
        return self.services[service_type]

    def service_id(self, service_id: str) -> Optional["UpnpService"]:
        """Get service by service_id."""
        for service in self.services.values():
            if service.service_id == service_id:
                return service
        return None

    async def async_ping(self) -> None:
        """Ping the device."""
        bare_request = HttpRequest("GET", self.device_url, {}, None)
        request = self.on_pre_receive_device_spec(bare_request)
        await self.requester.async_http_request(request)

    def __str__(self) -> str:
        """To string."""
        return f"<UpnpDevice({self.udn})>"


class UpnpService:
    """UPnP Service representation."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        requester: UpnpRequester,
        service_info: ServiceInfo,
        state_variables: Sequence["UpnpStateVariable"],
        actions: Sequence["UpnpAction"],
        on_pre_call_action: Callable[
            ["UpnpAction", Mapping[str, Any], HttpRequest], HttpRequest
        ] = default_on_pre_call_action,
        on_post_call_action: Callable[
            ["UpnpAction", HttpResponse], HttpResponse
        ] = default_on_post_call_action,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        self.requester = requester
        self._service_info = service_info
        self.state_variables = {sv.name: sv for sv in state_variables}
        self.actions = {ac.name: ac for ac in actions}
        self.on_pre_call_action = on_pre_call_action
        self.on_post_call_action = on_post_call_action

        self.on_event: Optional[EventCallbackType] = None
        self._device: Optional[UpnpDevice] = None

        # bind state variables to ourselves
        for state_var in state_variables:
            state_var.service = self

        # bind actions to ourselves
        for action in actions:
            action.service = self

    @property
    def device(self) -> UpnpDevice:
        """Get parent UpnpDevice."""
        if not self._device:
            raise UpnpError("UpnpService not bound to UpnpDevice")

        return self._device

    @device.setter
    def device(self, device: UpnpDevice) -> None:
        """Set parent UpnpDevice."""
        self._device = device

    @property
    def service_type(self) -> str:
        """Get service type for this UpnpService."""
        return self._service_info.service_type

    @property
    def service_id(self) -> str:
        """Get service ID for this UpnpService."""
        return self._service_info.service_id

    @property
    def scpd_url(self) -> str:
        """Get full SCPD-url for this UpnpService."""
        url: str = urllib.parse.urljoin(
            self.device.device_url, self._service_info.scpd_url
        )
        return url

    @property
    def control_url(self) -> str:
        """Get full control-url for this UpnpService."""
        url: str = urllib.parse.urljoin(
            self.device.device_url, self._service_info.control_url
        )
        return url

    @property
    def event_sub_url(self) -> str:
        """Get full event sub-url for this UpnpService."""
        url: str = urllib.parse.urljoin(
            self.device.device_url, self._service_info.event_sub_url
        )
        return url

    @property
    def xml(self) -> ET.Element:
        """Get the XML description for this service."""
        return self._service_info.xml

    def has_state_variable(self, name: str) -> bool:
        """Check if self has state variable called name."""
        if name not in self.state_variables and "}" in name:
            # possibly messed up namespaces, try again without namespace
            name = name.split("}")[1]

        return name in self.state_variables

    def state_variable(self, name: str) -> "UpnpStateVariable":
        """Get UPnpStateVariable by name."""
        state_var = self.state_variables.get(name, None)

        # possibly messed up namespaces, try again without namespace
        if not state_var and "}" in name:
            name = name.split("}")[1]
            state_var = self.state_variables.get(name, None)

        if state_var is None:
            raise KeyError(name)

        return state_var

    def has_action(self, name: str) -> bool:
        """Check if self has action called name."""
        return name in self.actions

    def action(self, name: str) -> "UpnpAction":
        """Get UPnpAction by name."""
        return self.actions[name]

    async def async_call_action(
        self, action: "UpnpAction", **kwargs: Any
    ) -> Mapping[str, Any]:
        """
        Call a UpnpAction.

        Parameters are in Python-values and coerced automatically to UPnP values.
        """
        if isinstance(action, str):
            action = self.actions[action]

        result = await action.async_call(**kwargs)
        return result

    def notify_changed_state_variables(self, changes: Mapping[str, str]) -> None:
        """Do callback on UpnpStateVariable.value changes."""
        changed_state_variables = []

        for name, value in changes.items():
            if not self.has_state_variable(name):
                _LOGGER.debug("State variable %s does not exist, ignoring", name)
                continue

            state_var = self.state_variable(name)
            try:
                state_var.upnp_value = value
                changed_state_variables.append(state_var)
            except UpnpValueError:
                _LOGGER.error("Got invalid value for %s: %s", state_var, value)

        if self.on_event:
            # pylint: disable=not-callable
            self.on_event(self, changed_state_variables)

    def __str__(self) -> str:
        """To string."""
        udn = "unbound"
        if self._device:
            udn = self._device.udn
        return f"<UpnpService({self.service_id}, {udn})>"

    def __repr__(self) -> str:
        """To repr."""
        udn = "unbound"
        if self._device:
            udn = self._device.udn
        return f"<UpnpService({self.service_id}, {udn})>"


class UpnpAction:
    """Representation of an Action."""

    class Argument:
        """Representation of an Argument of an Action."""

        def __init__(
            self, argument_info: ActionArgumentInfo, state_variable: "UpnpStateVariable"
        ) -> None:
            """Initialize."""
            self._argument_info = argument_info
            self._related_state_variable = state_variable
            self._value = None
            self.raw_upnp_value: Optional[str] = None

        def validate_value(self, value: Any) -> None:
            """Validate value against related UpnpStateVariable."""
            self.related_state_variable.validate_value(value)

        @property
        def name(self) -> str:
            """Get the name."""
            return self._argument_info.name

        @property
        def direction(self) -> str:
            """Get the direction."""
            return self._argument_info.direction

        @property
        def related_state_variable(self) -> "UpnpStateVariable":
            """Get the related state variable."""
            return self._related_state_variable

        @property
        def xml(self) -> ET.Element:
            """Get the XML description for this device."""
            return self._argument_info.xml

        @property
        def value(self) -> Any:
            """Get Python value for this argument."""
            return self._value

        @value.setter
        def value(self, value: Any) -> None:
            """Set Python value for this argument."""
            self.validate_value(value)
            self._value = value

        @property
        def upnp_value(self) -> str:
            """Get UPnP value for this argument."""
            return self.coerce_upnp(self.value)

        @upnp_value.setter
        def upnp_value(self, upnp_value: str) -> None:
            """Set UPnP value for this argument."""
            self._value = self.coerce_python(upnp_value)

        def coerce_python(self, upnp_value: str) -> Any:
            """Coerce UPnP value to Python."""
            return self.related_state_variable.coerce_python(upnp_value)

        def coerce_upnp(self, value: Any) -> str:
            """Coerce Python value to UPnP value."""
            return self.related_state_variable.coerce_upnp(value)

        def __repr__(self) -> str:
            """To repr."""
            return f"<UpnpAction.Argument({self.name}, {self.direction})>"

    def __init__(
        self,
        action_info: ActionInfo,
        arguments: List["UpnpAction.Argument"],
        non_strict: bool = False,
    ) -> None:
        """Initialize."""
        self._action_info = action_info
        self._arguments = arguments
        self._service: Optional[UpnpService] = None
        self._non_strict = non_strict

    @property
    def name(self) -> str:
        """Get the name."""
        return self._action_info.name

    @property
    def arguments(self) -> List["UpnpAction.Argument"]:
        """Get the arguments."""
        return self._arguments

    @property
    def xml(self) -> ET.Element:
        """Get the XML for this action."""
        return self._action_info.xml

    @property
    def service(self) -> UpnpService:
        """Get parent UpnpService."""
        if not self._service:
            raise UpnpError("UpnpAction not bound to UpnpService")

        return self._service

    @service.setter
    def service(self, service: UpnpService) -> None:
        """Set parent UpnpService."""
        self._service = service

    def __str__(self) -> str:
        """To string."""
        return f"<UpnpAction({self.name})>"

    def __repr__(self) -> str:
        """To repr."""
        return f"<UpnpAction({self.name})({self.in_arguments()}) -> {self.out_arguments()}>"

    def validate_arguments(self, **kwargs: Any) -> None:
        """
        Validate arguments against in-arguments of self.

        The python type is expected.
        """
        for arg in self.in_arguments():
            if arg.name not in kwargs:
                raise UpnpError(f"Missing argument: {arg.name}")

            value = kwargs[arg.name]
            arg.validate_value(value)

    def in_arguments(self) -> List["UpnpAction.Argument"]:
        """Get all in-arguments."""
        return [arg for arg in self.arguments if arg.direction == "in"]

    def out_arguments(self) -> List["UpnpAction.Argument"]:
        """Get all out-arguments."""
        return [arg for arg in self.arguments if arg.direction == "out"]

    def argument(
        self, name: str, direction: Optional[str] = None
    ) -> Optional["UpnpAction.Argument"]:
        """Get an UpnpAction.Argument by name (and possibliy direction)."""
        for arg in self.arguments:
            if arg.name != name:
                continue
            if direction is not None and arg.direction != direction:
                continue

            return arg
        return None

    async def async_call(self, **kwargs: Any) -> Mapping[str, Any]:
        """Call an action with arguments."""
        # do request
        _LOGGER.debug("Calling action: %s, args: %s", self.name, kwargs)
        bare_request = self.create_request(**kwargs)
        request = self.service.on_pre_call_action(self, kwargs, bare_request)
        bare_response = await self.service.requester.async_http_request(request)
        response = self.service.on_post_call_action(self, bare_response)
        if not isinstance(response.body, str):
            raise UpnpError(
                f"Did not receive a body when calling action: {self.name}, args: {kwargs}"
            )

        if response.status_code != 200:
            try:
                xml = DET.fromstring(response.body)
            except ET.ParseError:
                pass
            else:
                self._parse_fault(xml, response.status_code, response.headers)

            # Couldn't parse body for fault details, raise generic response error
            _LOGGER.debug(
                "Error calling action, no information, action: %s, args: %s",
                self.name,
                kwargs,
            )
            raise UpnpResponseError(
                status=response.status_code,
                headers=response.headers,
                message=f"Error during async_call(), "
                f"action: {self.name}, "
                f"args: {kwargs}, "
                f"status: {response.status_code}, "
                f"body: {response.body}",
            )

        # parse body
        response_args = self.parse_response(self.service.service_type, response)
        _LOGGER.debug(
            "Called action: %s, args: %s, response_args: %s",
            self.name,
            kwargs,
            response_args,
        )
        return response_args

    def create_request(self, **kwargs: Any) -> HttpRequest:
        """Create HTTP request for this to-be-called UpnpAction."""
        # build URL
        control_url = self.service.control_url

        # construct SOAP body
        service_type = self.service.service_type
        soap_args = self._format_request_args(**kwargs)
        body = (
            f'<?xml version="1.0"?>'
            f'<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"'
            f' xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f"<s:Body>"
            f'<u:{self.name} xmlns:u="{service_type}">'
            f"{soap_args}"
            f"</u:{self.name}>"
            f"</s:Body>"
            f"</s:Envelope>"
        )

        # construct SOAP header
        soap_action = f"{service_type}#{self.name}"
        headers = {
            "SOAPAction": f'"{soap_action}"',
            "Host": urllib.parse.urlparse(control_url).netloc,
            "Content-Type": 'text/xml; charset="utf-8"',
        }

        return HttpRequest("POST", control_url, headers, body)

    def _format_request_args(self, **kwargs: Any) -> str:
        self.validate_arguments(**kwargs)
        arg_strs = [
            f"<{arg.name}>{escape(arg.coerce_upnp(kwargs[arg.name]))}</{arg.name}>"
            for arg in self.in_arguments()
        ]
        return "\n".join(arg_strs)

    def parse_response(
        self, service_type: str, http_response: HttpResponse
    ) -> Mapping[str, Any]:
        """Parse response from called Action."""
        # pylint: disable=unused-argument
        stripped_response_body = http_response.body
        try:
            xml = DET.fromstring(stripped_response_body)
        except ET.ParseError as err:
            if self._non_strict:
                # Try again ignoring namespaces.
                try:
                    with DisableXmlNamespaces():
                        parser = DET.XMLParser()

                    source = io.StringIO(stripped_response_body)
                    it = DET.iterparse(source, parser=parser)
                    for _, el in it:
                        _, _, el.tag = el.tag.rpartition(":")  # Strip namespace.
                    it_root = it.root  # type: ET.Element
                    xml = it_root
                except ET.ParseError as err2:
                    _LOGGER.debug(
                        "Unable to parse XML: %s\nXML:\n%s", err2, http_response.body
                    )
                    raise UpnpXmlParseError(err2) from err2
            else:
                _LOGGER.debug(
                    "Unable to parse XML: %s\nXML:\n%s", err, http_response.body
                )
                raise UpnpXmlParseError(err) from err

        # Check if a SOAP fault occurred. It should have been caught earlier, by
        # the device sending an HTTP 500 status, but not all devices do.
        self._parse_fault(xml)

        try:
            return self._parse_response_args(service_type, xml)
        except AttributeError:
            _LOGGER.debug("Could not parse response: %s", http_response.body)
            raise

    def _parse_response_args(
        self, service_type: str, xml: ET.Element
    ) -> Mapping[str, Any]:
        """Parse response arguments."""
        args = {}
        query = f".//{{{service_type}}}{self.name}Response"
        response = xml.find(query, NS)

        # If no response was found, do a search ignoring namespaces when in non-strict mode.
        if self._non_strict:
            if response is None:
                query = f".//{{*}}{self.name}Response"
                response = xml.find(query, NS)

            # Perhaps namespaces were removed/ignored, try searching again.
            if response is None:
                query = ".//*Response"
                response = xml.find(query)

        if response is None:
            xml_str = ET.tostring(xml, encoding="unicode")
            raise UpnpError(f"Invalid response: {xml_str}")

        for arg_xml in response.findall("./"):
            name = arg_xml.tag
            arg = self.argument(name, "out")
            if not arg:
                if self._non_strict:
                    continue

                xml_str = ET.tostring(xml, encoding="unicode")
                raise UpnpError(
                    f"Invalid response, unknown argument: {name}, {xml_str}"
                )

            arg.raw_upnp_value = arg_xml.text
            arg.upnp_value = arg_xml.text or ""
            args[name] = arg.value

        return args

    def _parse_fault(
        self,
        xml: ET.Element,
        status_code: Optional[int] = None,
        response_headers: Optional[Mapping] = None,
    ) -> None:
        """Parse SOAP fault and raise appropriate exception."""
        # pylint: disable=too-many-branches
        fault = xml.find(".//soap_envelope:Body/soap_envelope:Fault", NS)
        if self._non_strict:
            if fault is None:
                fault = xml.find(".//{{*}}Body/{{*}}Fault", NS)

            if fault is None:
                fault = xml.find(".//{{*}}Body/{{*}}Fault")

        if fault is None:
            return

        error_code_str = fault.findtext(".//control:errorCode", None, NS)
        if self._non_strict:
            if not error_code_str:
                error_code_str = fault.findtext(".//{{*}}:errorCode", None, NS)

            if not error_code_str:
                error_code_str = fault.findtext(".//errorCode")

        if error_code_str:
            error_code: Optional[int] = int(error_code_str)
        else:
            error_code = None

        error_desc = fault.findtext(".//control:errorDescription", None, NS)
        if self._non_strict:
            if not error_desc:
                error_desc = fault.findtext(".//{{*}}:errorDescription", None, NS)

            if not error_desc:
                error_desc = fault.findtext(".//errorDescription")
        _LOGGER.debug(
            "Error calling action: %s, error code: %s, error desc: %s",
            self.name,
            error_code,
            error_desc,
        )

        if status_code is not None:
            raise UpnpActionResponseError(
                error_code=error_code,
                error_desc=error_desc,
                status=status_code,
                headers=response_headers,
                message=f"Error during async_call(), "
                f"action: {self.name}, "
                f"status: {status_code}, "
                f"upnp error: {error_code} ({error_desc})",
            )

        raise UpnpActionError(
            error_code=error_code,
            error_desc=error_desc,
            message=f"Error during async_call(), "
            f"action: {self.name}, "
            f"upnp error: {error_code} ({error_desc})",
        )


T = TypeVar("T")  # pylint: disable=invalid-name

_UNDEFINED = object()


class UpnpStateVariable(Generic[T]):
    """Representation of a State Variable."""

    # pylint: disable=too-many-instance-attributes

    UPNP_VALUE_ERROR = object()

    def __init__(
        self, state_variable_info: StateVariableInfo, schema: vol.Schema
    ) -> None:
        """Initialize."""
        self._state_variable_info = state_variable_info
        self._schema = schema

        self._service: Optional[UpnpService] = None
        self._value: Optional[Any] = None  # None, T or UPNP_VALUE_ERROR
        self._updated_at: Optional[datetime] = None

        # When py3.12 is the minimum version, we can switch
        # these to be @cached_property
        self._min_value: Optional[T] = _UNDEFINED  # type: ignore[assignment]
        self._max_value: Optional[T] = _UNDEFINED  # type: ignore[assignment]
        self._allowed_values: Set[T] = _UNDEFINED  # type: ignore[assignment]
        self._normalized_allowed_values: Set[str] = _UNDEFINED  # type: ignore[assignment]

    @property
    def service(self) -> UpnpService:
        """Get parent UpnpService."""
        if not self._service:
            raise UpnpError("UpnpStateVariable not bound to UpnpService")

        return self._service

    @service.setter
    def service(self, service: UpnpService) -> None:
        """Set parent UpnpService."""
        self._service = service

    @property
    def xml(self) -> ET.Element:
        """Get the XML for this State Variable."""
        return self._state_variable_info.xml

    @property
    def data_type_mapping(self) -> Mapping[str, Callable]:
        """Get the data type (coercer) for this State Variable."""
        return self._state_variable_info.type_info.data_type_mapping

    @property
    def data_type_python(self) -> Callable[[str], Any]:
        """Get the Python data type for this State Variable."""
        return self.data_type_mapping["type"]

    @property
    def min_value(self) -> Optional[T]:
        """Min value for this UpnpStateVariable, if defined."""
        if self._min_value is _UNDEFINED:
            min_ = self._state_variable_info.type_info.allowed_value_range.get("min")
            if min_ is not None:
                self._min_value = self.coerce_python(min_)
            else:
                self._min_value = None
        return self._min_value

    @property
    def max_value(self) -> Optional[T]:
        """Max value for this UpnpStateVariable, if defined."""
        if self._max_value is _UNDEFINED:
            max_ = self._state_variable_info.type_info.allowed_value_range.get("max")
            if max_ is not None:
                self._max_value = self.coerce_python(max_)
            else:
                self._max_value = None
        return self._max_value

    @property
    def allowed_values(self) -> Set[T]:
        """Set with allowed values for this UpnpStateVariable, if defined."""
        if self._allowed_values is _UNDEFINED:
            allowed_values = self._state_variable_info.type_info.allowed_values or []
            self._allowed_values = {
                self.coerce_python(allowed_value) for allowed_value in allowed_values
            }
        return self._allowed_values

    @property
    def normalized_allowed_values(self) -> Set[str]:
        """Set with normalized allowed values for this UpnpStateVariable, if defined."""
        if self._normalized_allowed_values is _UNDEFINED:
            self._normalized_allowed_values = {
                str(allowed_value).lower().strip()
                for allowed_value in self.allowed_values
            }
        return self._normalized_allowed_values

    @property
    def send_events(self) -> bool:
        """Check if this UpnpStatevariable send events."""
        return self._state_variable_info.send_events

    @property
    def name(self) -> str:
        """Name of the UpnpStatevariable."""
        return self._state_variable_info.name

    @property
    def data_type(self) -> str:
        """UPNP data type of UpnpStateVariable."""
        return self._state_variable_info.type_info.data_type

    @property
    def default_value(self) -> Optional[T]:
        """Get default value for UpnpStateVariable, if defined."""
        type_info = self._state_variable_info.type_info
        default_value = type_info.default_value
        if default_value is not None:
            value: T = self.coerce_python(default_value)
            return value

        return None

    def validate_value(self, value: T) -> None:
        """Validate value."""
        try:
            self._schema(value)
        except vol.error.MultipleInvalid as ex:
            raise UpnpValueError(self.name, value) from ex

    @property
    def value(self) -> Optional[T]:
        """
        Get the value, python typed.

        Invalid values are returned as None.
        """
        if self._value is UpnpStateVariable.UPNP_VALUE_ERROR:
            return None

        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        """Set value, python typed."""
        self.validate_value(value)
        self._value = value
        self._updated_at = datetime.now(timezone.utc)

    @property
    def value_unchecked(self) -> Optional[T]:
        """
        Get the value, python typed.

        If an event was received with an invalid value for this StateVariable
        (e.g., 'abc' for a 'ui4' StateVariable), then this will return
        UpnpStateVariable.UPNP_VALUE_ERROR instead of None.
        """
        return self._value

    @property
    def upnp_value(self) -> str:
        """Get the value, UPnP typed."""
        return self.coerce_upnp(self.value)

    @upnp_value.setter
    def upnp_value(self, upnp_value: str) -> None:
        """Set the value, UPnP typed."""
        try:
            self.value = self.coerce_python(upnp_value)
        except ValueError as err:
            _LOGGER.debug('Error setting upnp_value "%s", error: %s', upnp_value, err)
            self._value = UpnpStateVariable.UPNP_VALUE_ERROR

    def coerce_python(self, upnp_value: str) -> Any:
        """Coerce value from UPNP to python."""
        coercer = self.data_type_mapping["in"]
        return coercer(upnp_value)

    def coerce_upnp(self, value: Any) -> str:
        """Coerce value from python to UPNP."""
        coercer = self.data_type_mapping["out"]
        coerced_value: str = coercer(value)
        return coerced_value

    @property
    def updated_at(self) -> Optional[datetime]:
        """
        Get timestamp at which this UpnpStateVariable was updated.

        Return time in UTC.
        """
        return self._updated_at

    def __str__(self) -> str:
        """To string."""
        return f"<UpnpStateVariable({self.name}, {self.data_type})>"

    def __repr__(self) -> str:
        """To repr."""
        return f"<UpnpStateVariable({self.name}: {self.data_type} = {self.value!r})>"
