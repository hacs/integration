"""Utilities."""

import re
from typing import Optional, Tuple

NAMESPACES = {
    "didl_lite": "urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "sec": "http://www.sec.co.kr/",
    "upnp": "urn:schemas-upnp-org:metadata-1-0/upnp/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


def expand_namespace_tag(tag: str) -> str:
    """
    Expand namespace-alias to url.

    E.g.,
        _ns_tag('didl_lite:item') -> '{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}item'
    """
    if ":" not in tag:
        return tag

    namespace, tag = tag.split(":")
    namespace_uri = NAMESPACES[namespace]
    return f"{{{namespace_uri}}}{tag}"


def split_namespace_tag(namespaced_tag: str) -> Tuple[Optional[str], str]:
    """
    Extract namespace and tag from namespaced-tag.

    E.g., _namespace_tag('{urn:schemas-upnp-org:metadata-1-0/upnp/}class') ->
        'urn:schemas-upnp-org:metadata-1-0/upnp/', 'class'
    """
    if "}" not in namespaced_tag:
        return None, namespaced_tag

    idx = namespaced_tag.index("}")
    namespace = namespaced_tag[1:idx]
    tag = namespaced_tag[idx + 1 :]  # noqa: E203
    return namespace, tag


def to_camel_case(name: str) -> str:
    """Get camel case of name."""
    sub1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", sub1).lower()


def didl_property_key(didl_property_name: str) -> str:
    """Get Python property key for a DIDL property name."""
    if ":" in didl_property_name:
        # Remove the namespace from the property name
        didl_property_name = didl_property_name.partition(":")[2]

    if didl_property_name.startswith("@"):
        return to_camel_case(didl_property_name.replace("@", ""))

    return to_camel_case(didl_property_name.replace("@", "_"))


def didl_property_def_key(didl_property_def: Tuple[str, ...]) -> str:
    """Get Python property key for didl_property_def."""
    if didl_property_def[1].startswith("@"):
        return to_camel_case(didl_property_def[1].replace("@", ""))

    return to_camel_case(didl_property_def[1].replace("@", "_"))
