"""Exceptions for IPP."""


class IPPError(Exception):
    """Generic IPP exception."""


class IPPConnectionError(IPPError):
    """IPP connection exception."""


class IPPConnectionUpgradeRequired(IPPError):  # noqa: N818
    """IPP connection upgrade requested."""


class IPPParseError(IPPError):
    """IPP parse exception."""


class IPPResponseError(IPPError):
    """IPP response exception."""


class IPPVersionNotSupportedError(IPPError):
    """IPP version not supported."""
