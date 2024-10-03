# -*- coding: utf-8 -*-
"""async_upnp_client.exceptions module."""

import asyncio
from enum import IntEnum
from typing import Any, Optional
from xml.etree import ElementTree as ET

import aiohttp

# pylint: disable=too-many-ancestors


class UpnpError(Exception):
    """Base class for all errors raised by this library."""

    def __init__(
        self, *args: Any, message: Optional[str] = None, **_kwargs: Any
    ) -> None:
        """Initialize base UpnpError."""
        super().__init__(*args, message)


class UpnpContentError(UpnpError):
    """Content of UPnP response is invalid."""


class UpnpActionErrorCode(IntEnum):
    """Error codes for UPnP Action errors."""

    INVALID_ACTION = 401
    INVALID_ARGS = 402
    # (DO_NOT_USE) = 403
    ACTION_FAILED = 501
    ARGUMENT_VALUE_INVALID = 600
    ARGUMENT_VALUE_OUT_OF_RANGE = 601
    OPTIONAL_ACTION_NOT_IMPLEMENTED = 602
    OUT_OF_MEMORY = 603
    HUMAN_INTERVENTION_REQUIRED = 604
    STRING_ARGUMENT_TOO_LONG = 605


class UpnpActionError(UpnpError):
    """Server returned a SOAP Fault in response to an Action."""

    def __init__(
        self,
        *args: Any,
        error_code: Optional[int] = None,
        error_desc: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize from response body."""
        if not message:
            message = f"Received UPnP error {error_code} ({error_desc})"
        super().__init__(*args, message=message, **kwargs)
        self.error_code = error_code
        self.error_desc = error_desc


class UpnpXmlParseError(UpnpContentError, ET.ParseError):
    """UPnP response is not valid XML."""

    def __init__(self, orig_err: ET.ParseError) -> None:
        """Initialize from original ParseError, to match it."""
        super().__init__(message=str(orig_err))
        self.code = orig_err.code
        self.position = orig_err.position


class UpnpValueError(UpnpContentError):
    """Invalid value error."""

    def __init__(self, name: str, value: Any) -> None:
        """Initialize."""
        super().__init__(message=f"Invalid value for {name}: '{value}'")
        self.name = name
        self.value = value


class UpnpSIDError(UpnpContentError):
    """Missing Subscription Identifier from response."""


class UpnpXmlContentError(UpnpContentError):
    """XML document does not have expected content."""


class UpnpCommunicationError(UpnpError, aiohttp.ClientError):
    """Error occurred while communicating with the UPnP device ."""


class UpnpResponseError(UpnpCommunicationError):
    """HTTP error code returned by the UPnP device."""

    def __init__(
        self,
        *args: Any,
        status: int,
        headers: Optional[aiohttp.typedefs.LooseHeaders] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize."""
        if not message:
            message = f"Did not receive HTTP 200 but {status}"
        super().__init__(*args, message=message, **kwargs)
        self.status = status
        self.headers = headers


class UpnpActionResponseError(UpnpActionError, UpnpResponseError):
    """HTTP error code and UPnP error code.

    UPnP errors are usually indicated with HTTP 500 (Internal Server Error) and
    actual details in the response body as a SOAP Fault.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: Any,
        status: int,
        headers: Optional[aiohttp.typedefs.LooseHeaders] = None,
        error_code: Optional[int] = None,
        error_desc: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize."""
        if not message:
            message = (
                f"Received HTTP error code {status}, UPnP error code"
                f" {error_code} ({error_desc})"
            )
        super().__init__(
            *args,
            status=status,
            headers=headers,
            error_code=error_code,
            error_desc=error_desc,
            message=message,
            **kwargs,
        )


class UpnpClientResponseError(aiohttp.ClientResponseError, UpnpResponseError):
    """HTTP response error with more details from aiohttp."""


class UpnpConnectionError(UpnpCommunicationError, aiohttp.ClientConnectionError):
    """Error in the underlying connection to the UPnP device.

    This could indicate that the device is offline.
    """


class UpnpConnectionTimeoutError(
    UpnpConnectionError, aiohttp.ServerTimeoutError, asyncio.TimeoutError
):
    """Timeout while communicating with the device."""


class UpnpServerError(UpnpError):
    """Error with a local server."""


class UpnpServerOSError(UpnpServerError, OSError):
    """System-related error when starting a local server."""

    def __init___(self, errno: int, strerror: str) -> None:
        """Initialize simplified version of OSError."""
        OSError.__init__(self, errno, strerror)
