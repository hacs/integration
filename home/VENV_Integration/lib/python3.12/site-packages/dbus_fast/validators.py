import re
from functools import lru_cache

from .errors import (
    InvalidBusNameError,
    InvalidInterfaceNameError,
    InvalidMemberNameError,
    InvalidObjectPathError,
)

_bus_name_re = re.compile(r"^[A-Za-z_-][A-Za-z0-9_-]*$")
_path_re = re.compile(r"^[A-Za-z0-9_]+$")
_element_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_member_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


@lru_cache(maxsize=32)
def is_bus_name_valid(name: str) -> bool:
    """Whether this is a valid bus name.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names-bus

    :param name: The bus name to validate.
    :type name: str

    :returns: Whether the name is a valid bus name.
    :rtype: bool
    """
    if not isinstance(name, str):
        return False  # type: ignore[unreachable]

    if not name or len(name) > 255:
        return False

    if name.startswith(":"):
        # a unique bus name
        return True

    if name.startswith("."):
        return False

    if name.find(".") == -1:
        return False

    for element in name.split("."):
        if _bus_name_re.search(element) is None:
            return False

    return True


@lru_cache(maxsize=1024)
def is_object_path_valid(path: str) -> bool:
    """Whether this is a valid object path.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-marshaling-object-path

    :param path: The object path to validate.
    :type path: str

    :returns: Whether the object path is valid.
    :rtype: bool
    """
    if not isinstance(path, str):
        return False  # type: ignore[unreachable]

    if not path:
        return False

    if not path.startswith("/"):
        return False

    if len(path) == 1:
        return True

    for element in path[1:].split("/"):
        if _path_re.search(element) is None:
            return False

    return True


@lru_cache(maxsize=32)
def is_interface_name_valid(name: str) -> bool:
    """Whether this is a valid interface name.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names-interface

    :param name: The interface name to validate.
    :type name: str

    :returns: Whether the name is a valid interface name.
    :rtype: bool
    """
    if not isinstance(name, str):
        return False  # type: ignore[unreachable]

    if not name or len(name) > 255:
        return False

    if name.startswith("."):
        return False

    if name.find(".") == -1:
        return False

    for element in name.split("."):
        if _element_re.search(element) is None:
            return False

    return True


@lru_cache(maxsize=512)
def is_member_name_valid(member: str) -> bool:
    """Whether this is a valid member name.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names-member

    :param member: The member name to validate.
    :type member: str

    :returns: Whether the name is a valid member name.
    :rtype: bool
    """
    if not isinstance(member, str):
        return False  # type: ignore[unreachable]

    if not member or len(member) > 255:
        return False

    if _member_re.search(member) is None:
        return False

    return True


@lru_cache(maxsize=32)
def assert_bus_name_valid(name: str) -> None:
    """Raise an error if this is not a valid bus name.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names-bus

    :param name: The bus name to validate.
    :type name: str

    :raises:
        - :class:`InvalidBusNameError` - If this is not a valid bus name.
    """
    if not is_bus_name_valid(name):
        raise InvalidBusNameError(name)


@lru_cache(maxsize=1024)
def assert_object_path_valid(path: str) -> None:
    """Raise an error if this is not a valid object path.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-marshaling-object-path

    :param path: The object path to validate.
    :type path: str

    :raises:
        - :class:`InvalidObjectPathError` - If this is not a valid object path.
    """
    if not is_object_path_valid(path):
        raise InvalidObjectPathError(path)


@lru_cache(maxsize=32)
def assert_interface_name_valid(name: str) -> None:
    """Raise an error if this is not a valid interface name.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names-interface

    :param name: The interface name to validate.
    :type name: str

    :raises:
        - :class:`InvalidInterfaceNameError` - If this is not a valid object path.
    """
    if not is_interface_name_valid(name):
        raise InvalidInterfaceNameError(name)


@lru_cache(maxsize=512)
def assert_member_name_valid(member: str) -> None:
    """Raise an error if this is not a valid member name.

    .. seealso:: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names-member

    :param member: The member name to validate.
    :type member: str

    :raises:
        - :class:`InvalidMemberNameError` - If this is not a valid object path.
    """
    if not is_member_name_valid(member):
        raise InvalidMemberNameError(member)
