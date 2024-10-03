"""Response Parser for IPP."""
from __future__ import annotations

import logging
import struct
from datetime import datetime, timedelta, timezone
from typing import Any

from .enums import ATTRIBUTE_ENUM_MAP, IppTag
from .exceptions import IPPParseError

_LOGGER = logging.getLogger(__name__)


def parse_ieee1284_device_id(device_id: str) -> dict[str, str]:
    """Parse IEEE 1284 device id for common device info."""
    if not device_id:
        return {}

    device_id = device_id.strip(";")
    device_info: dict[str, str] = {}

    for pair in device_id.split(";"):
        key, value = pair.split(":", 2)
        device_info[key.strip()] = value.strip()

    if not device_info.get("MANUFACTURER") and device_info.get("MFG"):
        device_info["MANUFACTURER"] = device_info["MFG"]

    if not device_info.get("MODEL") and device_info.get("MDL"):
        device_info["MODEL"] = device_info["MDL"]

    if not device_info.get("COMMAND SET") and device_info.get("CMD"):
        device_info["COMMAND SET"] = device_info["CMD"]

    return device_info


# pylint: disable=R0912,R0915
def parse_attribute(  # noqa: PLR0912, PLR0915
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    """Parse attribute from IPP data.

    1 byte: Tag - b
    2 byte: Name Length - h
    N bytes: Name - direct access
    2 byte: Value Length -h
    N bytes: Value - direct access
    """
    _LOGGER.debug("Parsing Attribute at offset %s", offset)

    attribute = {"tag": struct.unpack_from(">b", data, offset)[0]}
    offset += 1

    attribute["name-length"] = struct.unpack_from(">h", data, offset)[0]
    offset += 2

    offset_length = offset + attribute["name-length"]
    attribute["name"] = data[offset:offset_length].decode("utf-8")
    offset += attribute["name-length"]

    attribute["value-length"] = struct.unpack_from(">h", data, offset)[0]
    offset += 2

    _LOGGER.debug("Attribute Name: %s", attribute["name"])
    _LOGGER.debug("Attribute Value Offset: %s", offset)
    _LOGGER.debug("Attribute Value Length: %s", attribute["value-length"])

    if attribute["tag"] in (IppTag.ENUM.value, IppTag.INTEGER.value):
        attribute["value"] = struct.unpack_from(">i", data, offset)[0]

        if (
            attribute["tag"] == IppTag.ENUM.value
            and attribute["name"] in ATTRIBUTE_ENUM_MAP
        ):
            enum_class = ATTRIBUTE_ENUM_MAP[attribute["name"]]
            attribute["value"] = enum_class(attribute["value"])

        offset += 4
        _LOGGER.debug("Attribute Value: %s", attribute["value"])
    elif attribute["tag"] == IppTag.BOOLEAN.value:
        attribute["value"] = struct.unpack_from(">?", data, offset)[0]
        offset += 1
        _LOGGER.debug("Attribute Value: %s", attribute["value"])
    elif attribute["tag"] == IppTag.DATE.value:
        if attribute["value-length"] != 11:
            raise IPPParseError(
                f'Invalid DATE size {attribute["value-length"]}',  # noqa: EM102
            )

        raw_date = dict(
            zip(
                (
                    "year",
                    "month",
                    "day",
                    "hour",
                    "minute",
                    "second",
                    "decisecond",
                    "tz_dir",
                    "tz_hour",
                    "tz_minute",
                ),
                struct.unpack_from(">hbbbbbbcbb", data, offset),
            ),
        )
        raw_date["microsecond"] = raw_date.pop("decisecond") * 100_000
        raw_date["tzinfo"] = timezone(
            {b"+": 1, b"-": -1}[raw_date.pop("tz_dir")]
            * timedelta(
                hours=raw_date.pop("tz_hour"),
                minutes=raw_date.pop("tz_minute"),
            ),
        )

        attribute["value"] = datetime(**raw_date)  # noqa: DTZ001
        offset += attribute["value-length"]
        _LOGGER.debug("Attribute Value: %s", attribute["value"])
    elif attribute["tag"] == IppTag.RESERVED_STRING.value:
        if attribute["value-length"] > 0:
            offset_length = offset + attribute["value-length"]
            attribute["value"] = data[offset:offset_length].decode("utf-8")
            offset += attribute["value-length"]
        else:
            attribute["value"] = None

        _LOGGER.debug("Attribute Value: %s", attribute["value"])
    elif attribute["tag"] == IppTag.RANGE.value:
        attribute["value"] = []
        for i in range(int(attribute["value-length"] / 4)):
            attribute["value"].append(struct.unpack_from(">i", data, offset + i * 4)[0])
        offset += attribute["value-length"]
    elif attribute["tag"] == IppTag.RESOLUTION.value:
        attribute["value"] = struct.unpack_from(">iib", data, offset)
        offset += attribute["value-length"]
    elif attribute["tag"] in (IppTag.TEXT_LANG.value, IppTag.NAME_LANG.value):
        attribute["language-length"] = struct.unpack_from(">h", data, offset)[0]
        offset += 2

        offset_length = offset + attribute["language-length"]
        attribute["language"] = data[offset:offset_length].decode("utf-8")
        offset += attribute["language-length"]
        _LOGGER.debug("Attribute Language: %s", attribute["language"])

        attribute["text-length"] = struct.unpack_from(">h", data, offset)[0]
        offset += 2
        _LOGGER.debug("Attribute Text Length: %s", attribute["text-length"])

        offset_length = offset + attribute["text-length"]
        attribute["value"] = data[offset:offset_length].decode("utf-8")
        offset += attribute["text-length"]
        _LOGGER.debug("Attribute Value: %s", attribute["value"])
    else:
        offset_length = offset + attribute["value-length"]
        attribute["value"] = data[offset:offset_length]
        _LOGGER.debug("Attribute Bytes: %s", attribute["value"])

        attribute["value"] = attribute["value"].decode("utf-8", "ignore")
        offset += attribute["value-length"]
        _LOGGER.debug("Attribute Value: %s", attribute["value"])

    return attribute, offset


# pylint: disable=R0912,R0915
def parse(  # noqa: PLR0912, PLR0915
    raw_data: bytes,
    contains_data: bool = False,  # noqa: FBT001, FBT002
) -> dict[str, Any]:
    r"""Parse raw IPP data.

    1 byte: Protocol Major Version - b
    1 byte: Protocol Minor Version - b
    2 byte: Operation ID/Status Code - h
    4 byte: Request ID - i

    1 byte: Operation Attribute Byte (\0x01)

    N Mal: Attributes

    1 byte: Attribute End Byte (\0x03)
    """
    data: dict[str, Any] = {}
    offset = 0

    _LOGGER.debug("Parsing IPP Data")

    data["version"] = struct.unpack_from(">bb", raw_data, offset)
    offset += 2

    _LOGGER.debug("IPP Version: %s", data["version"])

    data["status-code"] = struct.unpack_from(">h", raw_data, offset)[0]
    offset += 2

    _LOGGER.debug("IPP Status Code: %s", data["status-code"])

    data["request-id"] = struct.unpack_from(">i", raw_data, offset)[0]
    offset += 4

    data["operation-attributes"] = []
    data["unsupported-attributes"] = []
    data["jobs"] = []
    data["printers"] = []
    data["data"] = b""

    attribute_key = ""
    previous_attribute_name = ""
    tmp_data: dict[str, Any] = {}

    while struct.unpack_from("b", raw_data, offset)[0] != IppTag.END.value:
        # check for operation, job or printer attribute start byte
        # if tmp data and attribute key is set, another operation was sent
        # add it and reset tmp data
        if struct.unpack_from("b", raw_data, offset)[0] == IppTag.OPERATION.value:
            if tmp_data and attribute_key:
                data[attribute_key].append(tmp_data)
                tmp_data = {}

            attribute_key = "operation-attributes"
            offset += 1
        elif struct.unpack_from("b", raw_data, offset)[0] == IppTag.JOB.value:
            if tmp_data and attribute_key:
                data[attribute_key].append(tmp_data)
                tmp_data = {}

            attribute_key = "jobs"
            offset += 1
        elif struct.unpack_from("b", raw_data, offset)[0] == IppTag.PRINTER.value:
            if tmp_data and attribute_key:
                data[attribute_key].append(tmp_data)
                tmp_data = {}

            attribute_key = "printers"
            offset += 1
        elif (
            struct.unpack_from("b", raw_data, offset)[0]
            == IppTag.UNSUPPORTED_GROUP.value
        ):
            if tmp_data and attribute_key:
                data[attribute_key].append(tmp_data)
                tmp_data = {}

            attribute_key = "unsupported-attributes"
            offset += 1

        attribute, new_offset = parse_attribute(raw_data, offset)

        # if attribute has a name -> add it
        # if attribute doesn't have a name -> it is part of an array
        if attribute["name"]:
            tmp_data[attribute["name"]] = attribute["value"]
            previous_attribute_name = attribute["name"]
        elif previous_attribute_name:
            # check if attribute is already an array
            # else convert it to an array
            if isinstance(tmp_data[previous_attribute_name], list):
                tmp_data[previous_attribute_name].append(attribute["value"])
            else:
                tmp_value = tmp_data[previous_attribute_name]
                tmp_data[previous_attribute_name] = [tmp_value, attribute["value"]]

        offset = new_offset

    if isinstance(data[attribute_key], list):
        data[attribute_key].append(tmp_data)

    if isinstance(data["operation-attributes"], list):
        data["operation-attributes"] = data["operation-attributes"][0]

    if contains_data:
        offset_start = offset + 1
        data["data"] = raw_data[offset_start:]

    return data


def parse_make_and_model(make_and_model: str) -> tuple[str, str]:
    """Parse make and model for separate device make and model."""
    if not (make_and_model := make_and_model.strip()):
        return ("Unknown", "Unknown")

    make = "Unknown"
    model = "Unknown"
    found_make = False
    known_makes = [
        "brother",
        "canon",
        "epson",
        "kyocera",
        "hp",
        "xerox",
    ]

    test_against = make_and_model.lower()
    for known_make in known_makes:
        if test_against.startswith(known_make):
            found_make = True
            mlen = len(known_make)
            make = make_and_model[:mlen]
            model = make_and_model[mlen:].strip()
            break

    if not found_make:
        split = make_and_model.split(None, 1)
        make = split[0]

        if len(split) == 2:
            model = split[1].strip()

    return (make, model)
