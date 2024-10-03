"""Utils for Matter server (and client)."""

from __future__ import annotations

import base64
from base64 import b64decode
import binascii
from dataclasses import MISSING, asdict, fields, is_dataclass
from datetime import datetime
from enum import Enum
from functools import cache
from importlib.metadata import PackageNotFoundError, version as pkg_version
import logging
import platform
import socket
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from chip.clusters.Types import Nullable, NullValue
from chip.tlv import float32, uint

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
    from chip.clusters.ClusterObjects import (
        ClusterAttributeDescriptor,
        ClusterObjectDescriptor,
    )

    _T = TypeVar("_T", bound=DataclassInstance)

CHIP_CLUSTERS_PKG_NAME = "home-assistant-chip-clusters"
CHIP_CORE_PKG_NAME = "home-assistant-chip-core"

cached_fields = cache(fields)
cached_type_hints = cache(get_type_hints)


def create_attribute_path_from_attribute(
    endpoint_id: int, attribute: type[ClusterAttributeDescriptor]
) -> str:
    """Create path/identifier for an Attribute."""
    return create_attribute_path(
        endpoint_id, attribute.cluster_id, attribute.attribute_id
    )


def create_attribute_path(
    endpoint: int | None, cluster_id: int | None, attribute_id: int | None
) -> str:
    """
    Create path/identifier string for an Attribute.

    Returns same output as `Attribute.AttributePath` string representation.
    endpoint/cluster_id/attribute_id
    """
    return f"{endpoint}/{cluster_id}/{attribute_id}"


def parse_attribute_path(
    attribute_path: str,
) -> tuple[int | None, int | None, int | None]:
    """Parse AttributePath string into tuple of endpoint_id, cluster_id, attribute_id."""
    endpoint_id_str, cluster_id_str, attribute_id_str = attribute_path.split("/")
    endpoint_id = int(endpoint_id_str) if endpoint_id_str.isnumeric() else None
    cluster_id = int(cluster_id_str) if cluster_id_str.isnumeric() else None
    attribute_id = int(attribute_id_str) if attribute_id_str.isnumeric() else None
    return (endpoint_id, cluster_id, attribute_id)


def dataclass_to_dict(obj_in: DataclassInstance) -> dict:
    """Convert dataclass instance to dict."""

    return asdict(
        obj_in,
        dict_factory=lambda x: {
            # ensure the dict key is a string
            str(k): v
            for (k, v) in x
        },
    )


def parse_utc_timestamp(datetime_string: str) -> datetime:
    """Parse datetime from string."""
    return datetime.fromisoformat(datetime_string.replace("Z", "+00:00"))


def _get_descriptor_key(descriptor: ClusterObjectDescriptor, key: str | int) -> str:
    """Return correct Cluster attribute key for a tag id."""
    if (isinstance(key, str) and key.isnumeric()) or isinstance(key, int):
        if field := descriptor.GetFieldByTag(int(key)):
            return cast(str, field.Label)
    return cast(str, key)


def parse_value(
    name: str,
    value: Any,
    value_type: Any,
    default: Any = MISSING,
    allow_none: bool = False,
    allow_sdk_types: bool = False,
) -> Any:
    """
    Try to parse a value from raw (json) data and type annotations.

    If allow_sdk_types is False, any SDK specific custom data types will be converted.
    """
    # pylint: disable=too-many-return-statements,too-many-branches

    if isinstance(value_type, str):
        # this shouldn't happen, but just in case
        value_type = get_type_hints(value_type, globals(), locals())

    # handle value is None/missing but a default value is set
    if value is None and not isinstance(default, type(MISSING)):
        return default
    # handle value is None and sdk type is Nullable
    if value is None and value_type is Nullable:
        return Nullable() if allow_sdk_types else None
    # handle value is None (but that is allowed according to the annotations)
    if value is None and value_type is NoneType:
        return None

    if isinstance(value, dict):
        if descriptor := getattr(value_type, "descriptor", None):
            # handle matter TLV dicts where the keys are just tag identifiers
            value = {_get_descriptor_key(descriptor, x): y for x, y in value.items()}
        # handle a parse error in the sdk which is returned as:
        # {'TLVValue': None, 'Reason': None} or {'TLVValue': None}
        if value.get("TLVValue", MISSING) is None:
            if value_type in (None, Nullable, Any):
                return None
            value = None

    if is_dataclass(value_type) and isinstance(value, dict):
        return dataclass_from_dict(value_type, value)
    # get origin value type and inspect one-by-one
    origin: Any = get_origin(value_type)
    if origin in (list, tuple, set) and isinstance(value, (list, tuple, set)):
        return origin(
            parse_value(name, subvalue, get_args(value_type)[0])
            for subvalue in value
            if subvalue is not None
        )
    # handle dictionary where we should inspect all values
    if origin is dict:
        subkey_type = get_args(value_type)[0]
        subvalue_type = get_args(value_type)[1]
        return {
            parse_value(subkey, subkey, subkey_type): parse_value(
                f"{subkey}.value",
                subvalue,
                subvalue_type,
                allow_none=allow_none,
                allow_sdk_types=allow_sdk_types,
            )
            for subkey, subvalue in value.items()
        }
    # handle Union type
    if origin is Union or origin is UnionType:
        sub_value_types = get_args(value_type)
        # return early if value is None and None or Nullable allowed
        if value is None and Nullable in sub_value_types and allow_sdk_types:
            return NullValue
        if value is None and NoneType in sub_value_types:
            return None
        # try all possible types
        for sub_arg_type in sub_value_types:
            # try them all until one succeeds
            try:
                return parse_value(
                    name,
                    value,
                    sub_arg_type,
                    allow_none=allow_none,
                    allow_sdk_types=allow_sdk_types,
                )
            except (KeyError, TypeError, ValueError):
                pass
        # if we get to this point, all possibilities failed
        # find out if we should raise or log this
        err = (
            f"Value {value} of type {type(value)} is invalid for {name}, "
            f"expected value of type {value_type}"
        )
        if NoneType not in sub_value_types:
            # raise exception, we have no idea how to handle this value
            raise TypeError(err)
        # failed to parse the (sub) value but None allowed, log only
        logging.getLogger(__name__).warning(err)
        return None
    if origin is type:
        return get_type_hints(value, globals(), locals())
    # handle Any as value type (which is basically unprocessable)
    if value_type is Any:
        return value
    # handle value is None (but that is allowed)
    if value is None and allow_none:
        return None
    # raise if value is None and the value is required according to annotations
    if value is None:
        raise KeyError(f"`{name}` of type `{value_type}` is required.")

    try:
        if issubclass(value_type, Enum):
            # handle enums from the SDK that have a value that does not exist in the enum (sigh)
            # pylint: disable=protected-access
            if value not in value_type._value2member_map_:
                # we do not want to crash so we return the raw value
                return value
            return value_type(value)
        if issubclass(value_type, datetime):
            return parse_utc_timestamp(value)
    except TypeError:
        # happens if value_type is not a class
        pass

    # common type conversions (e.g. int as string)
    if value_type is float and isinstance(value, int):
        return float(value)
    if value_type is int and isinstance(value, str) and value.isnumeric():
        return int(value)
    # handle bytes values (sent over the wire as base64 encoded strings)
    if value_type is bytes and isinstance(value, str):
        try:
            return b64decode(value.encode("utf-8"))
        except binascii.Error:
            # unfortunately sometimes the data is malformed
            # as it is not super important we ignore it (for now)
            return b""

    # handle NOCStruct.noc which is typed/specified as bytes but parsed
    # as integer in the tlv parser somehow.
    # https://github.com/home-assistant/core/issues/113279
    # https://github.com/home-assistant/core/issues/116304
    if name == "NOCStruct.noc" and not isinstance(value, bytes):
        return b""

    # Matter SDK specific types
    if value_type is uint and (
        isinstance(value, int) or (isinstance(value, str) and value.isnumeric())
    ):
        return uint(value) if allow_sdk_types else int(value)
    if value_type is float32 and (
        isinstance(value, (float, int))
        or (isinstance(value, str) and value.isnumeric())
    ):
        return float32(value) if allow_sdk_types else float(value)

    # If we reach this point, we could not match the value with the type and we raise
    if not isinstance(value, value_type):
        raise TypeError(
            f"Value {value} of type {type(value)} is invalid for {name}, "
            f"expected value of type {value_type}"
        )
    return value


def dataclass_from_dict(
    cls: type[_T], dict_obj: dict, strict: bool = False, allow_sdk_types: bool = False
) -> _T:
    """
    Create (instance of) a dataclass by providing a dict with values.

    Including support for nested structures and common type conversions.
    If strict mode enabled, any additional keys in the provided dict will result in a KeyError.
    """
    dc_fields = cached_fields(cls)
    if strict:
        extra_keys = dict_obj.keys() - {f.name for f in dc_fields}
        if extra_keys:
            raise KeyError(
                f'Extra key(s) {",".join(extra_keys)} not allowed for {str(cls)}'
            )
    type_hints = cached_type_hints(cls)
    return cls(
        **{
            field.name: parse_value(
                f"{cls.__name__}.{field.name}",
                dict_obj.get(field.name),
                type_hints[field.name],
                field.default,
                allow_none=not strict,
                allow_sdk_types=allow_sdk_types,
            )
            for field in dc_fields
            if field.init
        }
    )


def package_version(pkg_name: str) -> str:
    """
    Return the version of an installed package.

    Will return `0.0.0` if the package is not found.
    """
    try:
        installed_version = pkg_version(pkg_name)
        if installed_version is None:
            return "0.0.0"  # type: ignore[unreachable]
        return installed_version
    except PackageNotFoundError:
        return "0.0.0"


@cache
def chip_clusters_version() -> str:
    """Return the version of the CHIP SDK (clusters package) that is installed."""
    return package_version(CHIP_CLUSTERS_PKG_NAME)


@cache
def chip_core_version() -> str:
    """Return the version of the CHIP SDK (core package) that is installed."""
    if platform.system() == "Darwin":
        # TODO: Fix this once we can install our own wheels on macos.
        return chip_clusters_version()
    return package_version(CHIP_CORE_PKG_NAME)


def convert_hex_string(hex_str: str | bytes) -> str:
    """Convert (Base64 encoded) byte array received from the sdk to a regular (unicode) string."""
    if isinstance(hex_str, str):
        # note that the bytes string can be optionally base64 encoded
        # when we send it back and forth over our api
        hex_str = base64.b64decode(hex_str)

    return "".join(f"{byte:02x}" for byte in hex_str)


def convert_mac_address(hex_mac: str | bytes) -> str:
    """Convert (Base64 encoded) byte array MAC received from the sdk to a regular mac-address."""
    if isinstance(hex_mac, str):
        # note that the bytes string can be optionally base64 encoded
        hex_mac = base64.b64decode(hex_mac)

    return ":".join("{:02x}".format(byte) for byte in hex_mac)  # pylint: disable=C0209


def convert_ip_address(hex_ip: str | bytes, ipv6: bool = False) -> str:
    """Convert (Base64 encoded) byte array IP received from the Matter SDK to a regular IP."""
    if isinstance(hex_ip, str):
        # note that the bytes string can be optionally base64 encoded
        hex_ip = base64.b64decode(hex_ip)
    return socket.inet_ntop(socket.AF_INET6 if ipv6 else socket.AF_INET, hex_ip)
