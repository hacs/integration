# -*- coding: utf-8 -*-
# Copyright (C) 2010, 2011 Sebastian Wiesner <lunaryorn@gmail.com>

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
    pyudev.core
    ===========

    Core types and functions of :mod:`pyudev`.

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: LOCAL
from pyudev._ctypeslib.libudev import ERROR_CHECKERS, SIGNATURES
from pyudev._ctypeslib.utils import load_ctypes_library
from pyudev._errors import DeviceNotFoundAtPathError
from pyudev._util import (
    ensure_byte_string,
    ensure_unicode_string,
    property_value_to_bytes,
    udev_list_iterate,
)
from pyudev.device import Devices


class Context(object):
    """
    A device database connection.

    This class represents a connection to the udev device database, and is
    really *the* central object to access udev.  You need an instance of this
    class for almost anything else in pyudev.

    This class itself gives access to various udev configuration data (e.g.
    :attr:`sys_path`, :attr:`device_path`), and provides device enumeration
    (:meth:`list_devices()`).

    Instances of this class can directly be given as ``udev *`` to functions
    wrapped through :mod:`ctypes`.
    """

    def __init__(self):
        """
        Create a new context.
        """
        self._libudev = load_ctypes_library("udev", SIGNATURES, ERROR_CHECKERS)
        self._as_parameter_ = self._libudev.udev_new()

    def __del__(self):
        if hasattr(self, "_libudev"):
            self._libudev.udev_unref(self)

    @property
    def sys_path(self):
        """
        The ``sysfs`` mount point defaulting to ``/sys'`` as unicode string.
        """
        if hasattr(self._libudev, "udev_get_sys_path"):
            return ensure_unicode_string(self._libudev.udev_get_sys_path(self))
        return "/sys"  # Fixed path since udev 183

    @property
    def device_path(self):
        """
        The device directory path defaulting to ``/dev`` as unicode string.
        """
        if hasattr(self._libudev, "udev_get_dev_path"):
            return ensure_unicode_string(self._libudev.udev_get_dev_path(self))
        return "/dev"  # Fixed path since udev 183

    @property
    def run_path(self):
        """
        The run runtime directory path defaulting to ``/run`` as unicode
        string.

        .. udevversion:: 167

        .. versionadded:: 0.10
        """
        if hasattr(self._libudev, "udev_get_run_path"):
            return ensure_unicode_string(self._libudev.udev_get_run_path(self))
        return "/run/udev"

    @property
    def log_priority(self):
        """
        The logging priority of the interal logging facitility of udev as
        integer with a standard :mod:`syslog` priority.  Assign to this
        property to change the logging priority.

        UDev uses the standard :mod:`syslog` priorities.  Constants for these
        priorities are defined in the :mod:`syslog` module in the standard
        library:

        >>> import syslog
        >>> context = pyudev.Context()
        >>> context.log_priority = syslog.LOG_DEBUG

        .. versionadded:: 0.9
        """
        return self._libudev.udev_get_log_priority(self)

    @log_priority.setter
    def log_priority(self, value):
        """
        Set the log priority.

        :param int value: the log priority.
        """
        self._libudev.udev_set_log_priority(self, value)

    def list_devices(self, **kwargs):
        """
        List all available devices.

        The arguments of this method are the same as for
        :meth:`Enumerator.match()`.  In fact, the arguments are simply passed
        straight to method :meth:`~Enumerator.match()`.

        This function creates and returns an :class:`Enumerator` object,
        that can be used to filter the list of devices, and eventually
        retrieve :class:`Device` objects representing matching devices.

        .. versionchanged:: 0.8
           Accept keyword arguments now for easy matching.
        """
        return Enumerator(self).match(**kwargs)


class Enumerator(object):
    """
    A filtered iterable of devices.

    To retrieve devices, simply iterate over an instance of this class.
    This operation yields :class:`Device` objects representing the available
    devices.

    Before iteration the device list can be filtered by subsystem or by
    property values using :meth:`match_subsystem` and
    :meth:`match_property`.  Multiple subsystem (property) filters are
    combined using a logical OR, filters of different types are combined
    using a logical AND.  The following filter for instance::

        devices.match_subsystem('block').match_property(
            'ID_TYPE', 'disk').match_property('DEVTYPE', 'disk')

    means the following::

        subsystem == 'block' and (ID_TYPE == 'disk' or DEVTYPE == 'disk')

    Once added, a filter cannot be removed anymore.  Create a new object
    instead.

    Instances of this class can directly be given as given ``udev_enumerate *``
    to functions wrapped through :mod:`ctypes`.
    """

    def __init__(self, context):
        """
        Create a new enumerator with the given ``context`` (a
        :class:`Context` instance).

        While you can create objects of this class directly, this is not
        recommended.  Call :method:`Context.list_devices()` instead.
        """
        if not isinstance(context, Context):
            raise TypeError("Invalid context object")
        self.context = context
        self._as_parameter_ = context._libudev.udev_enumerate_new(context)
        self._libudev = context._libudev

    def __del__(self):
        self._libudev.udev_enumerate_unref(self)

    def match(self, **kwargs):
        """
        Include devices according to the rules defined by the keyword
        arguments.  These keyword arguments are interpreted as follows:

        - The value for the keyword argument ``subsystem`` is forwarded to
          :meth:`match_subsystem()`.
        - The value for the keyword argument ``sys_name`` is forwared to
          :meth:`match_sys_name()`.
        - The value for the keyword argument ``tag`` is forwared to
          :meth:`match_tag()`.
        - The value for the keyword argument ``parent`` is forwared to
          :meth:`match_parent()`.
        - All other keyword arguments are forwareded one by one to
          :meth:`match_property()`.  The keyword argument itself is interpreted
          as property name, the value of the keyword argument as the property
          value.

        All keyword arguments are optional, calling this method without no
        arguments at all is simply a noop.

        Return the instance again.

        .. versionadded:: 0.8

        .. versionchanged:: 0.13
           Add ``parent`` keyword.
        """
        subsystem = kwargs.pop("subsystem", None)
        if subsystem is not None:
            self.match_subsystem(subsystem)
        sys_name = kwargs.pop("sys_name", None)
        if sys_name is not None:
            self.match_sys_name(sys_name)
        tag = kwargs.pop("tag", None)
        if tag is not None:
            self.match_tag(tag)
        parent = kwargs.pop("parent", None)
        if parent is not None:
            self.match_parent(parent)
        for prop, value in kwargs.items():
            self.match_property(prop, value)
        return self

    def match_subsystem(self, subsystem, nomatch=False):
        """
        Include all devices, which are part of the given ``subsystem``.

        ``subsystem`` is either a unicode string or a byte string, containing
        the name of the subsystem.  If ``nomatch`` is ``True`` (default is
        ``False``), the match is inverted:  A device is only included if it is
        *not* part of the given ``subsystem``.

        Note that, if a device has no subsystem, it is not included either
        with value of ``nomatch`` True or with value of ``nomatch`` False.

        Return the instance again.
        """
        match = (
            self._libudev.udev_enumerate_add_nomatch_subsystem
            if nomatch
            else self._libudev.udev_enumerate_add_match_subsystem
        )
        match(self, ensure_byte_string(subsystem))
        return self

    def match_sys_name(self, sys_name):
        """
        Include all devices with the given name.

        ``sys_name`` is a byte or unicode string containing the device name.

        Return the instance again.

        .. versionadded:: 0.8
        """
        self._libudev.udev_enumerate_add_match_sysname(
            self, ensure_byte_string(sys_name)
        )
        return self

    def match_property(self, prop, value):
        """
        Include all devices, whose ``prop`` has the given ``value``.

        ``prop`` is either a unicode string or a byte string, containing
        the name of the property to match.  ``value`` is a property value,
        being one of the following types:

        - :func:`int`
        - :func:`bool`
        - A byte string
        - Anything convertable to a unicode string (including a unicode string
          itself)

        Return the instance again.
        """
        self._libudev.udev_enumerate_add_match_property(
            self, ensure_byte_string(prop), property_value_to_bytes(value)
        )
        return self

    def match_attribute(self, attribute, value, nomatch=False):
        """
        Include all devices, whose ``attribute`` has the given ``value``.

        ``attribute`` is either a unicode string or a byte string, containing
        the name of a sys attribute to match.  ``value`` is an attribute value,
        being one of the following types:

        - :func:`int`,
        - :func:`bool`
        - A byte string
        - Anything convertable to a unicode string (including a unicode string
          itself)

        If ``nomatch`` is ``True`` (default is ``False``), the match is
        inverted:  A device is include if the ``attribute`` does *not* match
        the given ``value``.

        .. note::

           If ``nomatch`` is ``True``, devices which do not have the given
           ``attribute`` at all are also included.  In other words, with
           ``nomatch=True`` the given ``attribute`` is *not* guaranteed to
           exist on all returned devices.

        Return the instance again.
        """
        match = (
            self._libudev.udev_enumerate_add_match_sysattr
            if not nomatch
            else self._libudev.udev_enumerate_add_nomatch_sysattr
        )
        match(self, ensure_byte_string(attribute), property_value_to_bytes(value))
        return self

    def match_tag(self, tag):
        """
        Include all devices, which have the given ``tag`` attached.

        ``tag`` is a byte or unicode string containing the tag name.

        Return the instance again.

        .. udevversion:: 154

        .. versionadded:: 0.6
        """
        self._libudev.udev_enumerate_add_match_tag(self, ensure_byte_string(tag))
        return self

    def match_is_initialized(self):
        """
        Include only devices, which are initialized.

        Initialized devices have properly set device node permissions and
        context, and are (in case of network devices) fully renamed.

        Currently this will not affect devices which do not have device nodes
        and are not network interfaces.

        Return the instance again.

        .. seealso:: :attr:`Device.is_initialized`

        .. udevversion:: 165

        .. versionadded:: 0.8
        """
        self._libudev.udev_enumerate_add_match_is_initialized(self)
        return self

    def match_parent(self, parent):
        """
        Include all devices on the subtree of the given ``parent`` device.

        The ``parent`` device itself is also included.

        ``parent`` is a :class:`~pyudev.Device`.

        Return the instance again.

        .. udevversion:: 172

        .. versionadded:: 0.13
        """
        self._libudev.udev_enumerate_add_match_parent(self, parent)
        return self

    def __iter__(self):
        """
        Iterate over all matching devices.

        Yield :class:`Device` objects.
        """
        self._libudev.udev_enumerate_scan_devices(self)
        entry = self._libudev.udev_enumerate_get_list_entry(self)
        for name, _ in udev_list_iterate(self._libudev, entry):
            try:
                yield Devices.from_sys_path(self.context, name)
            except DeviceNotFoundAtPathError:
                continue
