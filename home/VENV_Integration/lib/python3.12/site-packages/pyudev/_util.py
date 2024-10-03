# -*- coding: utf-8 -*-
# Copyright (C) 2010, 2011, 2012 Sebastian Wiesner <lunaryorn@gmail.com>

# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.

# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
"""
    pyudev._util
    ============

    Internal utilities

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: STDLIB
import errno
import os
import stat
import sys
from subprocess import check_output


def ensure_byte_string(value):
    """
    Return the given ``value`` as bytestring.

    If the given ``value`` is not a byte string, but a real unicode string, it
    is encoded with the filesystem encoding (as in
    :func:`sys.getfilesystemencoding()`).
    """
    if not isinstance(value, bytes):
        value = value.encode(sys.getfilesystemencoding())
    return value


def ensure_unicode_string(value):
    """
    Return the given ``value`` as unicode string.

    If the given ``value`` is not a unicode string, but a byte string, it is
    decoded with the filesystem encoding (as in
    :func:`sys.getfilesystemencoding()`).
    """
    if not isinstance(value, str):
        value = value.decode(sys.getfilesystemencoding())
    return value


def property_value_to_bytes(value):
    """
    Return a byte string, which represents the given ``value`` in a way
    suitable as raw value of an udev property.

    If ``value`` is a boolean object, it is converted to ``'1'`` or ``'0'``,
    depending on whether ``value`` is ``True`` or ``False``.  If ``value`` is a
    byte string already, it is returned unchanged.  Anything else is simply
    converted to a unicode string, and then passed to
    :func:`ensure_byte_string`.
    """
    # udev represents boolean values as 1 or 0, therefore an explicit
    # conversion to int is required for boolean values
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, bytes):
        return value
    return ensure_byte_string(str(value))


def string_to_bool(value):
    """
    Convert the given unicode string ``value`` to a boolean object.

    If ``value`` is ``'1'``, ``True`` is returned.  If ``value`` is ``'0'``,
    ``False`` is returned.  Any other value raises a
    :exc:`~exceptions.ValueError`.
    """
    if value not in ("1", "0"):
        raise ValueError("Not a boolean value: {0!r}".format(value))
    return value == "1"


def udev_list_iterate(libudev, entry):
    """
    Iteration helper for udev list entry objects.

    Yield a tuple ``(name, value)``.  ``name`` and ``value`` are bytestrings
    containing the name and the value of the list entry.  The exact contents
    depend on the list iterated over.
    """
    while entry:
        name = libudev.udev_list_entry_get_name(entry)
        value = libudev.udev_list_entry_get_value(entry)
        yield (name, value)
        entry = libudev.udev_list_entry_get_next(entry)


def get_device_type(filename):
    """
    Get the device type of a device file.

    ``filename`` is a string containing the path of a device file.

    Return ``'char'`` if ``filename`` is a character device, or ``'block'`` if
    ``filename`` is a block device.  Raise :exc:`~exceptions.ValueError` if
    ``filename`` is no device file at all.  Raise
    :exc:`~exceptions.EnvironmentError` if ``filename`` does not exist or if
    its metadata was inaccessible.

    .. versionadded:: 0.15
    """
    mode = os.stat(filename).st_mode
    if stat.S_ISCHR(mode):
        return "char"
    elif stat.S_ISBLK(mode):
        return "block"
    else:
        raise ValueError("not a device file: {0!r}".format(filename))


def eintr_retry_call(func, *args, **kwargs):
    """
    Handle interruptions to an interruptible system call.

    Run an interruptible system call in a loop and retry if it raises EINTR.
    The signal calls that may raise EINTR prior to Python 3.5 are listed in
    PEP 0475.  Any calls to these functions must be wrapped in eintr_retry_call
    in order to handle EINTR returns in older versions of Python.

    This function is safe to use under Python 3.5 and newer since the wrapped
    function will simply return without raising EINTR.

    This function is based on _eintr_retry_call in python's subprocess.py.
    """

    # select.error inherits from Exception instead of OSError in Python 2
    # isort: STDLIB
    import select

    while True:
        try:
            return func(*args, **kwargs)
        except (OSError, IOError, select.error) as err:
            # If this is not an IOError or OSError, it's the old select.error
            # type, which means that the errno is only accessible via subscript
            if isinstance(err, (OSError, IOError)):
                error_code = err.errno
            else:
                error_code = err.args[0]

            if error_code == errno.EINTR:
                continue
            raise


def udev_version():
    """
    Get the version of the underlying udev library.

    udev doesn't use a standard major-minor versioning scheme, but instead
    labels releases with a single consecutive number.  Consequently, the
    version number returned by this function is a single integer, and not a
    tuple (like for instance the interpreter version in
    :data:`sys.version_info`).

    As libudev itself does not provide a function to query the version number,
    this function calls the ``udevadm`` utility, so be prepared to catch
    :exc:`~exceptions.EnvironmentError` and
    :exc:`~subprocess.CalledProcessError` if you call this function.

    Return the version number as single integer.  Raise
    :exc:`~exceptions.ValueError`, if the version number retrieved from udev
    could not be converted to an integer.  Raise
    :exc:`~exceptions.EnvironmentError`, if ``udevadm`` was not found, or could
    not be executed.  Raise :exc:`subprocess.CalledProcessError`, if
    ``udevadm`` returned a non-zero exit code.  On Python 2.7 or newer, the
    ``output`` attribute of this exception is correctly set.

    .. versionadded:: 0.8
    """
    output = ensure_unicode_string(check_output(["udevadm", "--version"]))
    return int(output.strip())
