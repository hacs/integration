# -*- coding: utf-8 -*-
"""async_upnp_client.utils module."""

import asyncio
import re
import socket
from collections import defaultdict
from collections.abc import Mapping as abcMapping
from collections.abc import MutableMapping as abcMutableMapping
from datetime import datetime, timedelta, timezone
from socket import AddressFamily  # pylint: disable=no-name-in-module
from typing import Any, Callable, Dict, Generator, Optional, Tuple
from urllib.parse import urljoin, urlsplit

import defusedxml.ElementTree as DET
from voluptuous import Invalid

EXTERNAL_IP = "1.1.1.1"
EXTERNAL_PORT = 80

UTC = timezone(timedelta(hours=0))
_UNCOMPILED_MATCHERS: Dict[str, Callable] = {
    # date
    r"\d{4}-\d{2}-\d{2}$": lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
    r"\d{2}:\d{2}:\d{2}$": lambda value: datetime.strptime(value, "%H:%M:%S").time(),
    # datetime
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$": lambda value: datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%S"
    ),
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$": lambda value: datetime.strptime(
        value, "%Y-%m-%d %H:%M:%S"
    ),
    # time.tz
    r"\d{2}:\d{2}:\d{2}[+-]\d{4}$": lambda value: datetime.strptime(
        value, "%H:%M:%S%z"
    ).timetz(),
    r"\d{2}:\d{2}:\d{2} [+-]\d{4}$": lambda value: datetime.strptime(
        value, "%H:%M:%S %z"
    ).timetz(),
    # datetime.tz
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}z$": lambda value: datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%Sz"
    ).replace(tzinfo=UTC),
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$": lambda value: datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%Sz"
    ).replace(tzinfo=UTC),
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$": lambda value: datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%S%z"
    ),
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} [+-]\d{4}$": lambda value: datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%S %z"
    ),
}

COMPILED_MATCHERS: Dict[re.Pattern, Callable] = {
    re.compile(matcher): parser for matcher, parser in _UNCOMPILED_MATCHERS.items()
}

TIME_RE = re.compile(r"(?P<sign>[-+])?(?P<h>\d+):(?P<m>\d+):(?P<s>\d+)\.?(?P<ms>\d+)?")


class lowerstr(str):  # pylint: disable=invalid-name
    """A prelowered string."""


class CaseInsensitiveDict(abcMutableMapping):
    """Case insensitive dict."""

    __slots__ = ("_data", "_case_map")

    def __init__(self, data: Optional[abcMapping] = None, **kwargs: Any) -> None:
        """Initialize."""
        self._data: Dict[Any, Any] = {**(data or {}), **kwargs}
        self._case_map: Dict[str, Any] = {
            (
                k
                if type(k) is lowerstr  # pylint: disable=unidiomatic-typecheck
                else k.lower()
            ): k
            for k in self._data
        }

    def copy(self) -> "CaseInsensitiveDict":
        """Copy a CaseInsensitiveDict.

        Returns a copy of CaseInsensitiveDict.
        """
        # pylint: disable=protected-access
        _copy = CaseInsensitiveDict.__new__(CaseInsensitiveDict)
        _copy._data = self._data.copy()
        _copy._case_map = self._case_map.copy()
        return _copy

    def combine(self, other: "CaseInsensitiveDict") -> "CaseInsensitiveDict":
        """Combine a CaseInsensitiveDict with another CaseInsensitiveDict.

        Returns a brand new CaseInsensitiveDict that is the combination
        of the two CaseInsensitiveDicts.
        """
        # pylint: disable=protected-access
        _combined = CaseInsensitiveDict.__new__(CaseInsensitiveDict)
        _combined._data = {**self._data, **other._data}
        _combined._case_map = {**self._case_map, **other._case_map}
        return _combined

    def combine_lower_dict(
        self, lower_dict: Dict[lowerstr, Any]
    ) -> "CaseInsensitiveDict":
        """Combine a CaseInsensitiveDict with a dict where all the keys are lowerstr.

        Returns a brand new CaseInsensitiveDict that is the combination
        of the CaseInsensitiveDict and dict where all the keys are lowerstr.
        """
        # pylint: disable=protected-access
        _combined = CaseInsensitiveDict.__new__(CaseInsensitiveDict)
        _combined._data = {**self._data, **lower_dict}
        _combined._case_map = {**self._case_map, **{k: k for k in lower_dict}}
        return _combined

    def case_map(self) -> Dict[str, str]:
        """Get the case map."""
        return self._case_map

    def as_dict(self) -> Dict[str, Any]:
        """Return the underlying dict without iterating."""
        return self._data

    def as_lower_dict(self) -> Dict[str, Any]:
        """Return the underlying dict in lowercase."""
        return {k.lower(): v for k, v in self._data.items()}

    def get_lower(self, lower_key: str, default: Any = None) -> Any:
        """Get a lower case key."""
        return self._data.get(self._case_map.get(lower_key), default)

    def lower_values_true(self, lower_keys: Tuple[str, ...]) -> bool:
        """Check if all lower case keys are present and true values."""
        for lower_key in lower_keys:
            if not self._data.get(self._case_map.get(lower_key)):
                return False
        return True

    def replace(self, new_data: abcMapping) -> None:
        """Replace the underlying dict without making a copy if possible."""
        if isinstance(new_data, CaseInsensitiveDict):
            self._data = new_data.as_dict()
            self._case_map = new_data.case_map()
        else:
            self._data = {**new_data}
            self._case_map = {
                (
                    k
                    if type(k) is lowerstr  # pylint: disable=unidiomatic-typecheck
                    else k.lower()
                ): k
                for k in self._data
            }

    def del_lower(self, lower_key: str) -> None:
        """Delete a lower case key."""
        del self._data[self._case_map[lower_key]]
        del self._case_map[lower_key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item."""
        lower_key = key.lower()
        if self._case_map.get(lower_key, key) != key:
            # Case changed
            del self._data[self._case_map[lower_key]]
        self._data[key] = value
        self._case_map[lower_key] = key

    def __getitem__(self, key: str) -> Any:
        """Get item."""
        return self._data[self._case_map[key.lower()]]

    def __delitem__(self, key: str) -> None:
        """Del item."""
        lower_key = key.lower()
        del self._data[self._case_map[lower_key]]
        del self._case_map[lower_key]

    def __len__(self) -> int:
        """Get length."""
        return len(self._data)

    def __iter__(self) -> Generator[str, None, None]:
        """Get iterator."""
        return (key for key in self._data.keys())

    def __repr__(self) -> str:
        """Repr."""
        return repr(self._data)

    def __str__(self) -> str:
        """Str."""
        return str(self._data)

    def __eq__(self, other: Any) -> bool:
        """Compare for equality."""
        if isinstance(other, CaseInsensitiveDict):
            return self.as_lower_dict() == other.as_lower_dict()

        if isinstance(other, abcMapping):
            return self.as_lower_dict() == {
                key.lower(): value for key, value in other.items()
            }

        return NotImplemented

    def __hash__(self) -> int:
        """Get hash."""
        return hash(tuple(sorted(self._data.items())))


def time_to_str(time: timedelta) -> str:
    """Convert timedelta to str/units."""
    total_seconds = abs(time.total_seconds())
    target = {
        "sign": "-" if time.total_seconds() < 0 else "",
        "hours": int(total_seconds // 3600),
        "minutes": int(total_seconds % 3600 // 60),
        "seconds": int(total_seconds % 60),
    }
    return "{sign}{hours}:{minutes}:{seconds}".format(**target)


def str_to_time(string: str) -> Optional[timedelta]:
    """Convert a string to timedelta."""
    match = TIME_RE.match(string)
    if not match:
        return None

    sign = -1 if match.group("sign") == "-" else 1
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    if match.group("ms"):
        msec = int(match.group("ms"))
    else:
        msec = 0
    return sign * timedelta(
        hours=hours, minutes=minutes, seconds=seconds, milliseconds=msec
    )


def absolute_url(device_url: str, url: str) -> str:
    """
    Convert a relative URL to an absolute URL pointing at device.

    If url is already an absolute url (i.e., starts with http:/https:),
    then the url itself is returned.
    """
    if url.startswith("http:") or url.startswith("https:"):
        return url

    return urljoin(device_url, url)


def require_tzinfo(value: Any) -> Any:
    """Require tzinfo."""
    if value.tzinfo is None:
        raise Invalid("Requires tzinfo")
    return value


def parse_date_time(value: str) -> Any:
    """Parse a date/time/date_time value."""
    # fix up timezone part
    if value[-6] in ["+", "-"] and value[-3] == ":":
        value = value[:-3] + value[-2:]
    for pattern, parser in COMPILED_MATCHERS.items():
        if pattern.match(value):
            return parser(value)
    raise ValueError("Unknown date/time: " + value)


def _target_url_to_addr(target_url: Optional[str]) -> Tuple[str, int]:
    """Resolve target_url into an address usable for get_local_ip."""
    if target_url:
        if "//" not in target_url:
            # Make sure urllib can work with target_url to get the host
            target_url = "//" + target_url
        target_url_split = urlsplit(target_url)
        target_host = target_url_split.hostname or EXTERNAL_IP
        target_port = target_url_split.port or EXTERNAL_PORT
    else:
        target_host = EXTERNAL_IP
        target_port = EXTERNAL_PORT

    return target_host, target_port


def get_local_ip(target_url: Optional[str] = None) -> str:
    """Try to get the local IP of this machine, used to talk to target_url.

    Only IPv4 addresses are supported.
    """
    target_addr = _target_url_to_addr(target_url)

    try:
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_sock.connect(target_addr)
        local_ip: str = temp_sock.getsockname()[0]
        return local_ip
    finally:
        temp_sock.close()


async def async_get_local_ip(
    target_url: Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None
) -> Tuple[AddressFamily, str]:
    """Try to get the local IP of this machine, used to talk to target_url.

    IPv4 and IPv6 are supported. For IPv6 link-local addresses the local IP may
    include the scope ID (zone index).
    """
    target_addr = _target_url_to_addr(target_url)
    loop = loop or asyncio.get_event_loop()

    # Create a UDP connection to the target. This won't cause any network
    # traffic but will assign a local IP to the socket.
    transport, _ = await loop.create_datagram_endpoint(
        asyncio.protocols.DatagramProtocol, remote_addr=target_addr
    )

    try:
        sock = transport.get_extra_info("socket")
        sockname = sock.getsockname()
        host, _ = socket.getnameinfo(
            sockname, socket.NI_NUMERICHOST | socket.NI_NUMERICSERV
        )
        return sock.family, host
    finally:
        transport.close()


# Adapted from http://stackoverflow.com/a/10077069
# to follow the XML to JSON spec
# https://www.xml.com/pub/a/2006/05/31/converting-between-xml-and-json.html
def etree_to_dict(tree: DET) -> Dict[str, Optional[Dict[str, Any]]]:
    """Convert an ETree object to a dict."""
    # strip namespace
    tag_name = tree.tag[tree.tag.find("}") + 1 :]

    tree_dict: Dict[str, Optional[Dict[str, Any]]] = {
        tag_name: {} if tree.attrib else None
    }
    children = list(tree)
    if children:
        child_dict: Dict[str, list] = defaultdict(list)
        for child in map(etree_to_dict, children):
            for k, val in child.items():
                child_dict[k].append(val)
        tree_dict = {
            tag_name: {k: v[0] if len(v) == 1 else v for k, v in child_dict.items()}
        }
    dict_meta = tree_dict[tag_name]
    if tree.attrib:
        assert dict_meta is not None
        dict_meta.update(("@" + k, v) for k, v in tree.attrib.items())
    if tree.text:
        text = tree.text.strip()
        if children or tree.attrib:
            if text:
                assert dict_meta is not None
                dict_meta["#text"] = text
        else:
            tree_dict[tag_name] = text
    return tree_dict
