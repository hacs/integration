import datetime
import ipaddress
from dataclasses import MISSING, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from typing_extensions import TypeAlias

from mashumaro.config import BaseConfig
from mashumaro.helper import pass_through
from mashumaro.jsonschema.dialects import DRAFT_2020_12, JSONSchemaDialect

try:
    from mashumaro.mixins.orjson import (
        DataClassORJSONMixin as DataClassJSONMixin,
    )
except ImportError:  # pragma: no cover
    from mashumaro.mixins.json import DataClassJSONMixin  # type: ignore


# https://github.com/python/mypy/issues/3186
Number: TypeAlias = Union[int, float]

Null = object()


class JSONSchemaInstanceType(Enum):
    NULL = "null"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NUMBER = "number"
    STRING = "string"
    INTEGER = "integer"


class JSONSchemaInstanceFormat(Enum):
    pass


class JSONSchemaStringFormat(JSONSchemaInstanceFormat):
    DATETIME = "date-time"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    EMAIL = "email"
    IDN_EMAIL = "idn-email"
    HOSTNAME = "hostname"
    IDN_HOSTNAME = "idn-hostname"
    IPV4ADDRESS = "ipv4"
    IPV6ADDRESS = "ipv6"
    URI = "uri"
    URI_REFERENCE = "uri-reference"
    IRI = "iri"
    IRI_REFERENCE = "iri-reference"
    UUID = "uuid"
    URI_TEMPLATE = "uri-template"
    JSON_POINTER = "json-pointer"
    RELATIVE_JSON_POINTER = "relative-json-pointer"
    REGEX = "regex"


class JSONSchemaInstanceFormatExtension(JSONSchemaInstanceFormat):
    TIMEDELTA = "time-delta"
    TIME_ZONE = "time-zone"
    IPV4NETWORK = "ipv4network"
    IPV6NETWORK = "ipv6network"
    IPV4INTERFACE = "ipv4interface"
    IPV6INTERFACE = "ipv6interface"
    DECIMAL = "decimal"
    FRACTION = "fraction"
    BASE64 = "base64"
    PATH = "path"


DATETIME_FORMATS = {
    datetime.datetime: JSONSchemaStringFormat.DATETIME,
    datetime.date: JSONSchemaStringFormat.DATE,
    datetime.time: JSONSchemaStringFormat.TIME,
}


IPADDRESS_FORMATS = {
    ipaddress.IPv4Address: JSONSchemaStringFormat.IPV4ADDRESS,
    ipaddress.IPv6Address: JSONSchemaStringFormat.IPV6ADDRESS,
    ipaddress.IPv4Network: JSONSchemaInstanceFormatExtension.IPV4NETWORK,
    ipaddress.IPv6Network: JSONSchemaInstanceFormatExtension.IPV6NETWORK,
    ipaddress.IPv4Interface: JSONSchemaInstanceFormatExtension.IPV4INTERFACE,
    ipaddress.IPv6Interface: JSONSchemaInstanceFormatExtension.IPV6INTERFACE,
}


@dataclass(unsafe_hash=True)
class JSONSchema(DataClassJSONMixin):
    # Common keywords
    schema: Optional[str] = None
    type: Optional[JSONSchemaInstanceType] = None
    enum: Optional[List[Any]] = None
    const: Optional[Any] = field(default_factory=lambda: MISSING)
    format: Optional[
        Union[JSONSchemaStringFormat, JSONSchemaInstanceFormatExtension]
    ] = None
    title: Optional[str] = None
    description: Optional[str] = None
    anyOf: Optional[List["JSONSchema"]] = None
    reference: Optional[str] = None
    definitions: Optional[Dict[str, "JSONSchema"]] = None
    default: Optional[Any] = field(default_factory=lambda: MISSING)
    deprecated: Optional[bool] = None
    examples: Optional[List[Any]] = None
    # Keywords for Objects
    properties: Optional[Dict[str, "JSONSchema"]] = None
    patternProperties: Optional[Dict[str, "JSONSchema"]] = None
    additionalProperties: Union["JSONSchema", bool, None] = None
    propertyNames: Optional["JSONSchema"] = None
    # Keywords for Arrays
    prefixItems: Optional[List["JSONSchema"]] = None
    items: Optional["JSONSchema"] = None
    contains: Optional["JSONSchema"] = None
    # Validation keywords for numeric instances
    multipleOf: Optional[Number] = None
    maximum: Optional[Number] = None
    exclusiveMaximum: Optional[Number] = None
    minimum: Optional[Number] = None
    exclusiveMinimum: Optional[Number] = None
    # Validation keywords for Strings
    maxLength: Optional[int] = None
    minLength: Optional[int] = None
    pattern: Optional[str] = None
    # Validation keywords for Arrays
    maxItems: Optional[int] = None
    minItems: Optional[int] = None
    uniqueItems: Optional[bool] = None
    maxContains: Optional[int] = None
    minContains: Optional[int] = None
    # Validation keywords for Objects
    maxProperties: Optional[int] = None
    minProperties: Optional[int] = None
    required: Optional[List[str]] = None
    dependentRequired: Optional[Dict[str, Set[str]]] = None

    class Config(BaseConfig):
        omit_none = True
        serialize_by_alias = True
        aliases = {
            "schema": "$schema",
            "reference": "$ref",
            "definitions": "$defs",
        }
        serialization_strategy = {
            int: pass_through,
            float: pass_through,
            Null: pass_through,
        }

    def __pre_serialize__(self) -> "JSONSchema":
        if self.const is None:
            self.const = Null
        if self.default is None:
            self.default = Null
        return self

    def __post_serialize__(self, d: Dict[Any, Any]) -> Dict[Any, Any]:
        const = d.get("const")
        if const is MISSING:
            d.pop("const")
        elif const is Null:
            d["const"] = None
        default = d.get("default")
        if default is MISSING:
            d.pop("default")
        elif default is Null:
            d["default"] = None
        return d


@dataclass
class JSONObjectSchema(JSONSchema):
    type: JSONSchemaInstanceType = JSONSchemaInstanceType.OBJECT


@dataclass
class JSONArraySchema(JSONSchema):
    type: JSONSchemaInstanceType = JSONSchemaInstanceType.ARRAY


@dataclass
class Context:
    dialect: JSONSchemaDialect = DRAFT_2020_12
    definitions: Dict[str, JSONSchema] = field(default_factory=dict)
    all_refs: Optional[bool] = None
    ref_prefix: Optional[str] = None
