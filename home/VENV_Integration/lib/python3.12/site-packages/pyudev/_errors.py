# -*- coding: utf-8 -*-
# Copyright (C) 2015 mulhern <amulhern@redhat.com>

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
    pyudev.device._errors
    =====================

    Errors raised by Device methods.

    .. moduleauthor:: Sebastian Wiesner <lunaryorn@gmail.com>
"""

# isort: STDLIB
import abc


class DeviceError(Exception):
    """
    Any error raised when messing around w/ or trying to discover devices.
    """

    __metaclass__ = abc.ABCMeta


class DeviceNotFoundError(DeviceError):
    """
    An exception indicating that no :class:`Device` was found.

    .. versionchanged:: 0.5
       Rename from ``NoSuchDeviceError`` to its current name.
    """

    __metaclass__ = abc.ABCMeta


class DeviceNotFoundAtPathError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating that no :class:`Device` was
    found at a given path.
    """

    def __init__(self, sys_path):
        DeviceNotFoundError.__init__(self, sys_path)

    @property
    def sys_path(self):
        """
        The path that caused this error as string.
        """
        return self.args[0]

    def __str__(self):
        return "No device at {0!r}".format(self.sys_path)


class DeviceNotFoundByFileError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating that no :class:`Device` was
    found from the given filename.
    """


class DeviceNotFoundByInterfaceIndexError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating that no :class:`Device` was found
    from the given interface index.
    """


class DeviceNotFoundByKernelDeviceError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating that no :class:`Device` was found
    from the given kernel device string.

    The format of the kernel device string is defined in the
    systemd.journal-fields man pages.
    """


class DeviceNotFoundByNameError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating that no :class:`Device` was
    found with a given name.
    """

    def __init__(self, subsystem, sys_name):
        DeviceNotFoundError.__init__(self, subsystem, sys_name)

    @property
    def subsystem(self):
        """
        The subsystem that caused this error as string.
        """
        return self.args[0]

    @property
    def sys_name(self):
        """
        The sys name that caused this error as string.
        """
        return self.args[1]

    def __str__(self):
        return "No device {0.sys_name!r} in {0.subsystem!r}".format(self)


class DeviceNotFoundByNumberError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating, that no :class:`Device` was found
    for a given device number.
    """

    def __init__(self, typ, number):
        DeviceNotFoundError.__init__(self, typ, number)

    @property
    def device_type(self):
        """
        The device type causing this error as string.  Either ``'char'`` or
        ``'block'``.
        """
        return self.args[0]

    @property
    def device_number(self):
        """
        The device number causing this error as integer.
        """
        return self.args[1]

    def __str__(self):
        return "No {0.device_type} device with number " "{0.device_number}".format(self)


class DeviceNotFoundInEnvironmentError(DeviceNotFoundError):
    """
    A :exc:`DeviceNotFoundError` indicating, that no :class:`Device` could
    be constructed from the process environment.
    """

    def __str__(self):
        return "No device found in environment"


class DeviceValueError(DeviceError):
    """
    Raised when a parameter has an unacceptable value.

    May also be raised when the parameter has an unacceptable type.
    """

    _FMT_STR = "value '%s' for parameter %s is unacceptable"

    def __init__(self, value, param, msg=None):
        """
        Initializer.

        :param object value: the value
        :param str param: the parameter
        :param str msg: an explanatory message
        """
        # pylint: disable=super-init-not-called
        self._value = value
        self._param = param
        self._msg = msg

    def __str__(self):
        if self._msg:
            fmt_str = self._FMT_STR + ": %s"
            return fmt_str % (self._value, self._param, self._msg)
        return self._FMT_STR % (self._value, self._param)
