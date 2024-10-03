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
    pyudev.discover
    ===============

    Tools to discover a device given limited information.

    .. moduleauthor::  mulhern <amulhern@redhat.com>
"""

# isort: STDLIB
import abc
import functools
import os
import re

# isort: LOCAL
from pyudev._errors import DeviceNotFoundError
from pyudev.device import Devices


def wrap_exception(func):
    """
    Allow Device discovery methods to return None instead of raising an
    exception.
    """

    @functools.wraps(func)
    def the_func(*args, **kwargs):
        """
        Returns result of calling ``func`` on ``args``, ``kwargs``.
        Returns None if ``func`` raises :exc:`DeviceNotFoundError`.
        """
        try:
            return func(*args, **kwargs)
        except DeviceNotFoundError:
            return None

    return the_func


class Hypothesis(object):
    """
    Represents a hypothesis about the meaning of the device identifier.
    """

    __metaclass__ = abc.ABCMeta

    @classmethod
    @abc.abstractmethod
    def match(cls, value):  # pragma: no cover
        """
        Match the given string according to the hypothesis.

        The purpose of this method is to obtain a value corresponding to
        ``value`` if that is possible. It may use a regular expression, but
        in general it should just return ``value`` and let the lookup method
        sort out the rest.

        :param str value: the string to inspect
        :returns: the matched thing or None if unmatched
        :rtype: the type of lookup's key parameter or NoneType
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def lookup(cls, context, key):  # pragma: no cover
        """
        Lookup the given string according to the hypothesis.

        :param Context context: the pyudev context
        :param key: a key with which to lookup the device
        :type key: the type of match's return value if not None
        :returns: a list of Devices obtained
        :rtype: frozenset of :class:`Device`
        """
        raise NotImplementedError()

    @classmethod
    def setup(cls, context):
        """
        A potentially expensive method that may allow an :class:`Hypothesis`
        to find devices more rapidly or to find a device that it would
        otherwise miss.

        :param Context context: the pyudev context
        """
        pass

    @classmethod
    def get_devices(cls, context, value):
        """
        Get any devices that may correspond to the given string.

        :param Context context: the pyudev context
        :param str value: the value to look for
        :returns: a list of devices obtained
        :rtype: set of :class:`Device`
        """
        key = cls.match(value)
        return cls.lookup(context, key) if key is not None else frozenset()


class DeviceNumberHypothesis(Hypothesis):
    """
    Represents the hypothesis that the device is a device number.

    The device may be separated into major/minor number or a composite number.
    """

    @classmethod
    def _match_major_minor(cls, value):
        """
        Match the number under the assumption that it is a major,minor pair.

        :param str value: value to match
        :returns: the device number or None
        :rtype: int or NoneType
        """
        major_minor_re = re.compile(r"^(?P<major>\d+)(\D+)(?P<minor>\d+)$")
        match = major_minor_re.match(value)
        return match and os.makedev(
            int(match.group("major")), int(match.group("minor"))
        )

    @classmethod
    def _match_number(cls, value):
        """
        Match the number under the assumption that it is a single number.

        :param str value: value to match
        :returns: the device number or None
        :rtype: int or NoneType
        """
        number_re = re.compile(r"^(?P<number>\d+)$")
        match = number_re.match(value)
        return match and int(match.group("number"))

    @classmethod
    def match(cls, value):
        """
        Match the number under the assumption that it is a device number.

        :returns: the device number or None
        :rtype: int or NoneType
        """
        return cls._match_major_minor(value) or cls._match_number(value)

    @classmethod
    def find_subsystems(cls, context):
        """
        Find subsystems in /sys/dev.

        :param Context context: the context
        :returns: a lis of available subsystems
        :rtype: list of str
        """
        sys_path = context.sys_path
        return os.listdir(os.path.join(sys_path, "dev"))

    @classmethod
    def lookup(cls, context, key):
        """
        Lookup by the device number.

        :param Context context: the context
        :param int key: the device number
        :returns: a list of matching devices
        :rtype: frozenset of :class:`Device`
        """
        func = wrap_exception(Devices.from_device_number)
        res = (func(context, s, key) for s in cls.find_subsystems(context))
        return frozenset(r for r in res if r is not None)


class DevicePathHypothesis(Hypothesis):
    """
    Discover the device assuming the identifier is a device path.
    """

    @classmethod
    def match(cls, value):
        """
        Match ``value`` under the assumption that it is a device path.

        :returns: the device path or None
        :rtype: str or NoneType
        """
        return value

    @classmethod
    def lookup(cls, context, key):
        """
        Lookup by the path.

        :param Context context: the context
        :param str key: the device path
        :returns: a list of matching devices
        :rtype: frozenset of :class:`Device`
        """
        res = wrap_exception(Devices.from_path)(context, key)
        return frozenset((res,)) if res is not None else frozenset()


class DeviceNameHypothesis(Hypothesis):
    """
    Discover the device assuming the input is a device name.

    Try every available subsystem.
    """

    @classmethod
    def find_subsystems(cls, context):
        """
        Find all subsystems in sysfs.

        :param Context context: the context
        :rtype: frozenset
        :returns: subsystems in sysfs
        """
        sys_path = context.sys_path
        dirnames = ("bus", "class", "subsystem")
        absnames = (os.path.join(sys_path, name) for name in dirnames)
        realnames = (d for d in absnames if os.path.isdir(d))
        return frozenset(n for d in realnames for n in os.listdir(d))

    @classmethod
    def match(cls, value):
        """
        Match ``value`` under the assumption that it is a device name.

        :returns: the device path or None
        :rtype: str or NoneType
        """
        return value

    @classmethod
    def lookup(cls, context, key):
        """
        Lookup by the path.

        :param Context context: the context
        :param str key: the device path
        :returns: a list of matching devices
        :rtype: frozenset of :class:`Device`
        """
        func = wrap_exception(Devices.from_name)
        res = (func(context, s, key) for s in cls.find_subsystems(context))
        return frozenset(r for r in res if r is not None)


class DeviceFileHypothesis(Hypothesis):
    """
    Discover the device assuming the value is some portion of a device file.

    The device file may be a link to a device node.
    """

    _LINK_DIRS = [
        "/dev",
        "/dev/disk/by-id",
        "/dev/disk/by-label",
        "/dev/disk/by-partlabel",
        "/dev/disk/by-partuuid",
        "/dev/disk/by-path",
        "/dev/disk/by-uuid",
        "/dev/input/by-path",
        "/dev/mapper",
        "/dev/md",
        "/dev/vg",
    ]

    @classmethod
    def get_link_dirs(cls, context):
        """
        Get all directories that may contain links to device nodes.

        This method checks the device links of every device, so it is very
        expensive.

        :param Context context: the context
        :returns: a sorted list of directories that contain device links
        :rtype: list
        """
        devices = context.list_devices()
        devices_with_links = (d for d in devices if list(d.device_links))
        links = (l for d in devices_with_links for l in d.device_links)
        return sorted(set(os.path.dirname(l) for l in links))

    @classmethod
    def setup(cls, context):
        """
        Set the link directories to be used when discovering by file.

        Uses `get_link_dirs`, so is as expensive as it is.

        :param Context context: the context
        """
        cls._LINK_DIRS = cls.get_link_dirs(context)

    @classmethod
    def match(cls, value):
        return value

    @classmethod
    def lookup(cls, context, key):
        """
        Lookup the device under the assumption that the key is part of
        the name of a device file.

        :param Context context: the context
        :param str key: a portion of the device file name

        It is assumed that either it is the whole name of the device file
        or it is the basename.

        A device file may be a device node or a device link.
        """
        func = wrap_exception(Devices.from_device_file)
        if "/" in key:
            device = func(context, key)
            return frozenset((device,)) if device is not None else frozenset()

        files = (os.path.join(ld, key) for ld in cls._LINK_DIRS)
        devices = (func(context, f) for f in files)
        return frozenset(d for d in devices if d is not None)


class Discovery(object):
    # pylint: disable=too-few-public-methods
    """
    Provides discovery methods for devices.
    """

    _HYPOTHESES = [
        DeviceFileHypothesis,
        DeviceNameHypothesis,
        DeviceNumberHypothesis,
        DevicePathHypothesis,
    ]

    def __init__(self):
        self._hypotheses = self._HYPOTHESES

    def setup(self, context):
        """
        Set up individual hypotheses.

        May be an expensive call.

        :param Context context: the context
        """
        for hyp in self._hypotheses:
            hyp.setup(context)

    def get_devices(self, context, value):
        """
        Get the devices corresponding to value.

        :param Context context: the context
        :param str value: some identifier of the device
        :returns: a list of corresponding devices
        :rtype: frozenset of :class:`Device`
        """
        return frozenset(
            d for h in self._hypotheses for d in h.get_devices(context, value)
        )
