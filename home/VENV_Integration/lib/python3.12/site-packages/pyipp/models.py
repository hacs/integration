"""Models for IPP."""
# pylint: disable=R0912,R0915
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from yarl import URL

from .parser import parse_ieee1284_device_id, parse_make_and_model

PRINTER_STATES = {3: "idle", 4: "printing", 5: "stopped"}


@dataclass
class Info:
    """Object holding information from IPP."""

    name: str
    printer_name: str
    printer_uri_supported: list[str]
    uptime: int
    command_set: str | None = None
    location: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    printer_info: str | None = None
    serial: str | None = None
    uuid: str | None = None
    version: str | None = None
    more_info: str | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Info:
        """Return Info object from IPP response."""
        cmd = None
        name = "IPP Printer"
        name_parts = []
        serial = None
        _printer_name = printer_name = data.get("printer-name", "")
        make_model = data.get("printer-make-and-model", "")
        device_id = data.get("printer-device-id", "")
        uri_supported = data.get("printer-uri-supported", [])
        uuid = data.get("printer-uuid")

        if not isinstance(uri_supported, list):
            uri_supported = [str(uri_supported)]

        for uri in uri_supported:
            if (URL(uri).path.lstrip("/")) == _printer_name.lstrip("/"):
                _printer_name = ""
                break

        make, model = parse_make_and_model(make_model)
        parsed_device_id = parse_ieee1284_device_id(device_id)

        if parsed_device_id.get("MFG") is not None and len(parsed_device_id["MFG"]) > 0:
            make = parsed_device_id["MFG"]
            name_parts.append(make)

        if parsed_device_id.get("MDL") is not None and len(parsed_device_id["MDL"]) > 0:
            model = parsed_device_id["MDL"]
            name_parts.append(model)

        if parsed_device_id.get("CMD") is not None and len(parsed_device_id["CMD"]) > 0:
            cmd = parsed_device_id["CMD"]

        if parsed_device_id.get("SN") is not None and len(parsed_device_id["SN"]) > 0:
            serial = parsed_device_id["SN"]

        if len(make_model) > 0:
            name = make_model
        elif len(name_parts) == 2:
            name = " ".join(name_parts)
        elif len(_printer_name) > 0:
            name = _printer_name

        return Info(
            command_set=cmd,
            location=data.get("printer-location", ""),
            name=name,
            manufacturer=make,
            model=model,
            printer_name=printer_name,
            printer_info=data.get("printer-info"),
            printer_uri_supported=uri_supported,
            serial=serial,
            uptime=data.get("printer-up-time", 0),
            uuid=uuid[9:] if uuid else None,  # strip urn:uuid: from uuid
            version=data.get("printer-firmware-string-version"),
            more_info=data.get("printer-more-info"),
        )


@dataclass
class Marker:
    """Object holding marker (ink) info from IPP."""

    marker_id: int
    marker_type: str
    name: str
    color: str
    level: int
    low_level: int
    high_level: int


@dataclass
class Uri:
    """Object holding URI info from IPP."""

    uri: str
    authentication: str | None
    security: str | None


@dataclass
class State:
    """Object holding the IPP printer state."""

    printer_state: str
    reasons: str | None
    message: str | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> State:
        """Return State object from IPP response."""
        state = data.get("printer-state", 0)

        if (reasons := data.get("printer-state-reasons")) == "none":
            reasons = None

        return State(
            printer_state=PRINTER_STATES.get(state, state),
            reasons=reasons,
            message=data.get("printer-state-message"),
        )


@dataclass
class Printer:
    """Object holding the IPP printer information."""

    info: Info
    markers: list[Marker]
    state: State
    uris: list[Uri]

    def as_dict(self) -> dict[str, Any]:
        """Return dictionary version of this printer."""
        return {
            "info": asdict(self.info),
            "state": asdict(self.state),
            "markers": [asdict(marker) for marker in self.markers],
            "uris": [asdict(uri) for uri in self.uris],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Printer:
        """Return Printer object from IPP response."""
        return Printer(
            info=Info.from_dict(data),
            markers=Printer.merge_marker_data(data),
            state=State.from_dict(data),
            uris=Printer.merge_uri_data(data),
        )

    @staticmethod
    def merge_marker_data(  # noqa: PLR0912, C901
        data: dict[str, Any],
    ) -> list[Marker]:
        """Return Marker data from IPP response."""
        marker_names = []
        marker_colors = []
        marker_levels = []
        marker_types = []
        marker_highs = []
        marker_lows = []

        if not data.get("marker-names"):
            return []

        if isinstance(data["marker-names"], list):
            marker_names = data["marker-names"]
        elif isinstance(data["marker-names"], str):
            marker_names = [data["marker-names"]]

        if not (mlen := len(marker_names)):
            return []

        for _ in range(mlen):
            marker_colors.append("")
            marker_levels.append(-2)
            marker_types.append("unknown")
            marker_highs.append(100)
            marker_lows.append(0)

        if isinstance(data.get("marker-colors"), list):
            for index, list_value in enumerate(data["marker-colors"]):
                if index < mlen:
                    marker_colors[index] = list_value
        elif isinstance(data.get("marker-colors"), str) and mlen == 1:
            marker_colors[0] = data["marker-colors"]

        if isinstance(data.get("marker-levels"), list):
            for index, list_value in enumerate(data["marker-levels"]):
                if index < mlen:
                    marker_levels[index] = list_value
        elif isinstance(data.get("marker-levels"), int) and mlen == 1:
            marker_levels[0] = data["marker-levels"]

        if isinstance(data.get("marker-high-levels"), list):
            for index, list_value in enumerate(data["marker-high-levels"]):
                if index < mlen:
                    marker_highs[index] = list_value
        elif isinstance(data.get("marker-high-levels"), int) and mlen == 1:
            marker_highs[0] = data["marker-high-levels"]

        if isinstance(data.get("marker-low-levels"), list):
            for index, list_value in enumerate(data["marker-low-levels"]):
                if index < mlen:
                    marker_lows[index] = list_value
        elif isinstance(data.get("marker-low-levels"), int) and mlen == 1:
            marker_lows[0] = data["marker-low-levels"]

        if isinstance(data.get("marker-types"), list):
            for index, list_value in enumerate(data["marker-types"]):
                if index < mlen:
                    marker_types[index] = list_value
        elif isinstance(data.get("marker-types"), str) and mlen == 1:
            marker_types[0] = data["marker-types"]

        markers = [
            Marker(
                marker_id=marker_id,
                marker_type=marker_types[marker_id],
                name=marker_names[marker_id],
                color=marker_colors[marker_id],
                level=marker_levels[marker_id],
                high_level=marker_highs[marker_id],
                low_level=marker_lows[marker_id],
            )
            for marker_id in range(mlen)
        ]
        markers.sort(key=lambda x: x.name)

        return markers

    @staticmethod
    def merge_uri_data(data: dict[str, Any]) -> list[Uri]:  # noqa: PLR0912
        """Return URI data from IPP response."""
        _uris: list[str] = []
        auth: list[str | None] = []
        security: list[str | None] = []

        if not data.get("printer-uri-supported"):
            return []

        if isinstance(data["printer-uri-supported"], list):
            _uris = data["printer-uri-supported"]
        elif isinstance(data["printer-uri-supported"], str):
            _uris = [data["printer-uri-supported"]]

        if not (ulen := len(_uris)):
            return []

        for _ in range(ulen):
            auth.append(None)
            security.append(None)

        if isinstance(data.get("uri-authentication-supported"), list):
            for k, list_value in enumerate(data["uri-authentication-supported"]):
                if k < ulen:
                    auth[k] = _str_or_none(list_value)
        elif isinstance(data.get("uri-authentication-supported"), str) and ulen == 1:
            auth[0] = _str_or_none(data["uri-authentication-supported"])

        if isinstance(data.get("uri-security-supported"), list):
            for k, list_value in enumerate(data["uri-security-supported"]):
                if k < ulen:
                    security[k] = _str_or_none(list_value)
        elif isinstance(data.get("uri-security-supported"), str) and ulen == 1:
            security[0] = _str_or_none(data["uri-security-supported"])

        return [
            Uri(
                uri=_uris[uri_id],
                authentication=auth[uri_id],
                security=security[uri_id],
            )
            for uri_id in range(ulen)
        ]


def _str_or_none(value: str) -> str | None:
    """Return string while handling string representations of None."""
    if value == "none":
        return None

    return value
