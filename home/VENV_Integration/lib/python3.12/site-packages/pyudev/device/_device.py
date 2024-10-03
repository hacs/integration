# -*- coding: utf-8 -*-
# Copyright (C) 2011, 2012 Sebastian Wiesner <lunaryorn@gmail.com>

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
    pyudev.device._device
    =====================

    Device class implementation of :mod:`pyudev`.

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: STDLIB
import collections
import os
import re
import sys
from datetime import timedelta

# isort: LOCAL
from pyudev._errors import (
    DeviceNotFoundAtPathError,
    DeviceNotFoundByFileError,
    DeviceNotFoundByInterfaceIndexError,
    DeviceNotFoundByKernelDeviceError,
    DeviceNotFoundByNameError,
    DeviceNotFoundByNumberError,
    DeviceNotFoundInEnvironmentError,
)
from pyudev._util import (
    ensure_byte_string,
    ensure_unicode_string,
    get_device_type,
    string_to_bool,
    udev_list_iterate,
)

# pylint: disable=too-many-lines


class Devices(object):
    """
    Class for constructing :class:`Device` objects from various kinds of data.
    """

    @classmethod
    def from_path(cls, context, path):
        """
        Create a device from a device ``path``.  The ``path`` may or may not
        start with the ``sysfs`` mount point:

        >>> from pyudev import Context, Device
        >>> context = Context()
        >>> Devices.from_path(context, '/devices/platform')
        Device(u'/sys/devices/platform')
        >>> Devices.from_path(context, '/sys/devices/platform')
        Device(u'/sys/devices/platform')

        ``context`` is the :class:`Context` in which to search the device.
        ``path`` is a device path as unicode or byte string.

        Return a :class:`Device` object for the device.  Raise
        :exc:`DeviceNotFoundAtPathError`, if no device was found for ``path``.

        .. versionadded:: 0.18
        """
        if not path.startswith(context.sys_path):
            path = os.path.join(context.sys_path, path.lstrip(os.sep))
        return cls.from_sys_path(context, path)

    @classmethod
    def from_sys_path(cls, context, sys_path):
        """
        Create a new device from a given ``sys_path``:

        >>> from pyudev import Context, Device
        >>> context = Context()
        >>> Devices.from_sys_path(context, '/sys/devices/platform')
        Device(u'/sys/devices/platform')

        ``context`` is the :class:`Context` in which to search the device.
        ``sys_path`` is a unicode or byte string containing the path of the
        device inside ``sysfs`` with the mount point included.

        Return a :class:`Device` object for the device.  Raise
        :exc:`DeviceNotFoundAtPathError`, if no device was found for
        ``sys_path``.

        .. versionadded:: 0.18
        """
        device = context._libudev.udev_device_new_from_syspath(
            context, ensure_byte_string(sys_path)
        )
        if not device:
            raise DeviceNotFoundAtPathError(sys_path)
        return Device(context, device)

    @classmethod
    def from_name(cls, context, subsystem, sys_name):
        """
        Create a new device from a given ``subsystem`` and a given
        ``sys_name``:

        >>> from pyudev import Context, Device
        >>> context = Context()
        >>> sda = Devices.from_name(context, 'block', 'sda')
        >>> sda
        Device(u'/sys/devices/pci0000:00/0000:00:1f.2/host0/target0:0:0/0:0:0:0/block/sda')
        >>> sda == Devices.from_path(context, '/block/sda')

        ``context`` is the :class:`Context` in which to search the device.
        ``subsystem`` and ``sys_name`` are byte or unicode strings, which
        denote the subsystem and the name of the device to create.

        Return a :class:`Device` object for the device.  Raise
        :exc:`DeviceNotFoundByNameError`, if no device was found with the given
        name.

        .. versionadded:: 0.18
        """
        sys_name = sys_name.replace("/", "!")
        device = context._libudev.udev_device_new_from_subsystem_sysname(
            context, ensure_byte_string(subsystem), ensure_byte_string(sys_name)
        )
        if not device:
            raise DeviceNotFoundByNameError(subsystem, sys_name)
        return Device(context, device)

    @classmethod
    def from_device_number(cls, context, typ, number):
        """
        Create a new device from a device ``number`` with the given device
        ``type``:

        >>> import os
        >>> from pyudev import Context, Device
        >>> ctx = Context()
        >>> major, minor = 8, 0
        >>> device = Devices.from_device_number(context, 'block',
        ...     os.makedev(major, minor))
        >>> device
        Device(u'/sys/devices/pci0000:00/0000:00:11.0/host0/target0:0:0/0:0:0:0/block/sda')
        >>> os.major(device.device_number), os.minor(device.device_number)
        (8, 0)

        Use :func:`os.makedev` to construct a device number from a major and a
        minor device number, as shown in the example above.

        .. warning::

           Device numbers are not unique across different device types.
           Passing a correct number with a wrong type may silently yield a
           wrong device object, so make sure to pass the correct device type.

        ``context`` is the :class:`Context`, in which to search the device.
        ``type`` is either ``'char'`` or ``'block'``, according to whether the
        device is a character or block device.  ``number`` is the device number
        as integer.

        Return a :class:`Device` object for the device with the given device
        ``number``.  Raise :exc:`DeviceNotFoundByNumberError`, if no device was
        found with the given device type and number.

        .. versionadded:: 0.18
        """
        device = context._libudev.udev_device_new_from_devnum(
            context, ensure_byte_string(typ[0]), number
        )
        if not device:
            raise DeviceNotFoundByNumberError(typ, number)
        return Device(context, device)

    @classmethod
    def from_device_file(cls, context, filename):
        """
        Create a new device from the given device file:

        >>> from pyudev import Context, Device
        >>> context = Context()
        >>> device = Devices.from_device_file(context, '/dev/sda')
        >>> device
        Device(u'/sys/devices/pci0000:00/0000:00:0d.0/host2/target2:0:0/2:0:0:0/block/sda')
        >>> device.device_node
        u'/dev/sda'

        .. warning::

           Though the example seems to suggest that ``device.device_node ==
           filename`` holds with ``device = Devices.from_device_file(context,
           filename)``, this is only true in a majority of cases.  There *can*
           be devices, for which this relation is actually false!  Thus, do
           *not* expect :attr:`~Device.device_node` to be equal to the given
           ``filename`` for the returned :class:`Device`.  Especially, use
           :attr:`~Device.device_node` if you need the device file of a
           :class:`Device` created with this method afterwards.

        ``context`` is the :class:`Context` in which to search the device.
        ``filename`` is a string containing the path of a device file.

        Return a :class:`Device` representing the given device file.  Raise
        :exc:`DeviceNotFoundByFileError` if ``filename`` is no device file
        at all or if ``filename`` does not exist or if its metadata was
        inaccessible.

        .. versionadded:: 0.18
        """
        try:
            device_type = get_device_type(filename)
            device_number = os.stat(filename).st_rdev
        except (EnvironmentError, ValueError) as err:
            raise DeviceNotFoundByFileError(err)

        return cls.from_device_number(context, device_type, device_number)

    @classmethod
    def from_interface_index(cls, context, ifindex):
        """
        Locate a device based on the interface index.

        :param `Context` context: the libudev context
        :param int ifindex: the interface index
        :returns: the device corresponding to the interface index
        :rtype: `Device`

        This method is only appropriate for network devices.
        """
        network_devices = context.list_devices(subsystem="net")
        dev = next(
            (d for d in network_devices if d.attributes.get("ifindex") == ifindex), None
        )
        if dev is not None:
            return dev
        else:
            raise DeviceNotFoundByInterfaceIndexError(ifindex)

    @classmethod
    def from_kernel_device(cls, context, kernel_device):
        """
        Locate a device based on the kernel device.

        :param `Context` context: the libudev context
        :param str kernel_device: the kernel device
        :returns: the device corresponding to ``kernel_device``
        :rtype: `Device`
        """
        switch_char = kernel_device[0]
        rest = kernel_device[1:]
        if switch_char in ("b", "c"):
            number_re = re.compile(r"^(?P<major>\d+):(?P<minor>\d+)$")
            match = number_re.match(rest)
            if match:
                number = os.makedev(
                    int(match.group("major")), int(match.group("minor"))
                )
                return cls.from_device_number(context, switch_char, number)
            else:
                raise DeviceNotFoundByKernelDeviceError(kernel_device)
        elif switch_char == "n":
            return cls.from_interface_index(context, rest)
        elif switch_char == "+":
            (subsystem, _, kernel_device_name) = rest.partition(":")
            if kernel_device_name and subsystem:
                return cls.from_name(context, subsystem, kernel_device_name)
            else:
                raise DeviceNotFoundByKernelDeviceError(kernel_device)
        else:
            raise DeviceNotFoundByKernelDeviceError(kernel_device)

    @classmethod
    def from_environment(cls, context):
        """
        Create a new device from the process environment (as in
        :data:`os.environ`).

        This only works reliable, if the current process is called from an
        udev rule, and is usually used for tools executed from ``IMPORT=``
        rules.  Use this method to create device objects in Python scripts
        called from udev rules.

        ``context`` is the library :class:`Context`.

        Return a :class:`Device` object constructed from the environment.
        Raise :exc:`DeviceNotFoundInEnvironmentError`, if no device could be
        created from the environment.

        .. udevversion:: 152

        .. versionadded:: 0.18
        """
        device = context._libudev.udev_device_new_from_environment(context)
        if not device:
            raise DeviceNotFoundInEnvironmentError()
        return Device(context, device)

    @classmethod
    def METHODS(cls):  # pylint: disable=invalid-name
        """
        Return methods that obtain a :class:`Device` from a variety of
        different data.

        :return: a list of from_* methods.
        :rtype: list of class methods

        .. versionadded:: 0.18
        """
        return [  # pragma: no cover
            cls.from_device_file,
            cls.from_device_number,
            cls.from_name,
            cls.from_path,
            cls.from_sys_path,
        ]


class Device(collections.abc.Mapping):
    # pylint: disable=too-many-public-methods
    """
    A single device with attached attributes and properties.

    A device also has a set of udev-specific attributes like the path
    inside ``sysfs``.

    :class:`Device` objects compare equal and unequal to other devices and
    to strings (based on :attr:`device_path`).  However, there is no
    ordering on :class:`Device` objects, and the corresponding operators
    ``>``, ``<``, ``<=`` and ``>=`` raise :exc:`~exceptions.TypeError`.

    .. warning::

       Currently, Device extends Mapping. The mapping that it stores is that
       of udev property names to udev property values. This use is deprecated
       and Device will no longer extend Mapping in 1.0. To look up udev
       properties, use the Device.properties property.

    .. warning::

       **Never** use object identity (``is`` operator) to compare
       :class:`Device` objects.  :mod:`pyudev` may create multiple
       :class:`Device` objects for the same device.  Instead compare
       devices by value using ``==`` or ``!=``.

    :class:`Device` objects are hashable and can therefore be used as keys
    in dictionaries and sets.

    They can also be given directly as ``udev_device *`` to functions wrapped
    through :mod:`ctypes`.
    """

    @classmethod
    def from_path(cls, context, path):  # pragma: no cover
        """
        .. versionadded:: 0.4
        .. deprecated:: 0.18
           Use :class:`Devices.from_path` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use equivalent Devices method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Devices.from_path(context, path)

    @classmethod
    def from_sys_path(cls, context, sys_path):  # pragma: no cover
        """
        .. versionchanged:: 0.4
           Raise :exc:`NoSuchDeviceError` instead of returning ``None``, if
           no device was found for ``sys_path``.
        .. versionchanged:: 0.5
           Raise :exc:`DeviceNotFoundAtPathError` instead of
           :exc:`NoSuchDeviceError`.
        .. deprecated:: 0.18
           Use :class:`Devices.from_sys_path` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use equivalent Devices method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Devices.from_sys_path(context, sys_path)

    @classmethod
    def from_name(cls, context, subsystem, sys_name):  # pragma: no cover
        """
        .. versionadded:: 0.5
        .. deprecated:: 0.18
           Use :class:`Devices.from_name` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use equivalent Devices method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Devices.from_name(context, subsystem, sys_name)

    @classmethod
    def from_device_number(cls, context, typ, number):  # pragma: no cover
        """
        .. versionadded:: 0.11
        .. deprecated:: 0.18
           Use :class:`Devices.from_device_number` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use equivalent Devices method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Devices.from_device_number(context, typ, number)

    @classmethod
    def from_device_file(cls, context, filename):  # pragma: no cover
        """
        .. versionadded:: 0.15
        .. deprecated:: 0.18
           Use :class:`Devices.from_device_file` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use equivalent Devices method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Devices.from_device_file(context, filename)

    @classmethod
    def from_environment(cls, context):  # pragma: no cover
        """
        .. versionadded:: 0.6
        .. deprecated:: 0.18
           Use :class:`Devices.from_environment` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use equivalent Devices method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Devices.from_environment(context)

    def __init__(self, context, _device):
        collections.abc.Mapping.__init__(self)
        self.context = context
        self._as_parameter_ = _device
        self._libudev = context._libudev

    def __del__(self):
        self._libudev.udev_device_unref(self)

    def __repr__(self):
        return "Device({0.sys_path!r})".format(self)

    @property
    def parent(self):
        """
        The parent :class:`Device` or ``None``, if there is no parent
        device.
        """
        parent = self._libudev.udev_device_get_parent(self)
        if not parent:
            return None
        # the parent device is not referenced, thus forcibly acquire a
        # reference
        return Device(self.context, self._libudev.udev_device_ref(parent))

    @property
    def children(self):
        """
        Yield all direct children of this device.

        .. note::

           In udev, parent-child relationships are generally ambiguous, i.e.
           a parent can have multiple children, *and* a child can have multiple
           parents. Hence, `child.parent == parent` does generally *not* hold
           for all `child` objects in `parent.children`. In other words,
           the :attr:`parent` of a device in this property can be different
           from this device!

        .. note::

           As the underlying library does not provide any means to directly
           query the children of a device, this property performs a linear
           search through all devices.

        Return an iterable yielding a :class:`Device` object for each direct
        child of this device.

        .. udevversion:: 172

        .. versionchanged:: 0.13
           Requires udev version 172 now.
        """
        for device in self.context.list_devices().match_parent(self):
            if device != self:
                yield device

    @property
    def ancestors(self):
        """
        Yield all ancestors of this device from bottom to top.

        Return an iterator yielding a :class:`Device` object for each
        ancestor of this device from bottom to top.

        .. versionadded:: 0.16
        """
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    def find_parent(self, subsystem, device_type=None):
        """
        Find the parent device with the given ``subsystem`` and
        ``device_type``.

        ``subsystem`` is a byte or unicode string containing the name of the
        subsystem, in which to search for the parent.  ``device_type`` is a
        byte or unicode string holding the expected device type of the parent.
        It can be ``None`` (the default), which means, that no specific device
        type is expected.

        Return a parent :class:`Device` within the given ``subsystem`` and, if
        ``device_type`` is not ``None``, with the given ``device_type``, or
        ``None``, if this device has no parent device matching these
        constraints.

        .. versionadded:: 0.9
        """
        subsystem = ensure_byte_string(subsystem)
        if device_type is not None:
            device_type = ensure_byte_string(device_type)
        parent = self._libudev.udev_device_get_parent_with_subsystem_devtype(
            self, subsystem, device_type
        )
        if not parent:
            return None
        # parent device is not referenced, thus forcibly acquire a reference
        return Device(self.context, self._libudev.udev_device_ref(parent))

    def traverse(self):
        """
        Traverse all parent devices of this device from bottom to top.

        Return an iterable yielding all parent devices as :class:`Device`
        objects, *not* including the current device.  The last yielded
        :class:`Device` is the top of the device hierarchy.

        .. deprecated:: 0.16
           Will be removed in 1.0. Use :attr:`ancestors` instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use Device.ancestors instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.ancestors

    @property
    def sys_path(self):
        """
        Absolute path of this device in ``sysfs`` including the ``sysfs``
        mount point as unicode string.
        """
        return ensure_unicode_string(self._libudev.udev_device_get_syspath(self))

    @property
    def device_path(self):
        """
        Kernel device path as unicode string.  This path uniquely identifies
        a single device.

        Unlike :attr:`sys_path`, this path does not contain the ``sysfs``
        mount point.  However, the path is absolute and starts with a slash
        ``'/'``.
        """
        return ensure_unicode_string(self._libudev.udev_device_get_devpath(self))

    @property
    def subsystem(self):
        """
        Name of the subsystem this device is part of as unicode string.

        :returns: name of subsystem if found, else None
        :rtype: unicode string or NoneType
        """
        subsys = self._libudev.udev_device_get_subsystem(self)
        return None if subsys is None else ensure_unicode_string(subsys)

    @property
    def sys_name(self):
        """
        Device file name inside ``sysfs`` as unicode string.
        """
        return ensure_unicode_string(self._libudev.udev_device_get_sysname(self))

    @property
    def sys_number(self):
        """
        The trailing number of the :attr:`sys_name` as unicode string, or
        ``None``, if the device has no trailing number in its name.

        .. note::

           The number is returned as unicode string to preserve the exact
           format of the number, especially any leading zeros:

           >>> from pyudev import Context, Device
           >>> context = Context()
           >>> device = Devices.from_path(context, '/sys/devices/LNXSYSTM:00')
           >>> device.sys_number
           u'00'

           To work with numbers, explicitly convert them to ints:

           >>> int(device.sys_number)
           0

        .. versionadded:: 0.11
        """
        number = self._libudev.udev_device_get_sysnum(self)
        return ensure_unicode_string(number) if number is not None else None

    @property
    def device_type(self):
        """
        Device type as unicode string, or ``None``, if the device type is
        unknown.

        >>> from pyudev import Context
        >>> context = Context()
        >>> for device in context.list_devices(subsystem='net'):
        ...     '{0} - {1}'.format(device.sys_name, device.device_type or 'ethernet')
        ...
        u'eth0 - ethernet'
        u'wlan0 - wlan'
        u'lo - ethernet'
        u'vboxnet0 - ethernet'

        .. versionadded:: 0.10
        """
        device_type = self._libudev.udev_device_get_devtype(self)
        if device_type is None:
            return None
        return ensure_unicode_string(device_type)

    @property
    def driver(self):
        """
        The driver name as unicode string, or ``None``, if there is no
        driver for this device.

        .. versionadded:: 0.5
        """
        driver = self._libudev.udev_device_get_driver(self)
        return ensure_unicode_string(driver) if driver is not None else None

    @property
    def device_node(self):
        """
        Absolute path to the device node of this device as unicode string or
        ``None``, if this device doesn't have a device node.  The path
        includes the device directory (see :attr:`Context.device_path`).

        This path always points to the actual device node associated with
        this device, and never to any symbolic links to this device node.
        See :attr:`device_links` to get a list of symbolic links to this
        device node.

        .. warning::

           For devices created with :meth:`from_device_file()`, the value of
           this property is not necessary equal to the ``filename`` given to
           :meth:`from_device_file()`.
        """
        node = self._libudev.udev_device_get_devnode(self)
        return ensure_unicode_string(node) if node is not None else None

    @property
    def device_number(self):
        """
        The device number of the associated device as integer, or ``0``, if no
        device number is associated.

        Use :func:`os.major` and :func:`os.minor` to decompose the device
        number into its major and minor number:

        >>> import os
        >>> from pyudev import Context, Device
        >>> context = Context()
        >>> sda = Devices.from_name(context, 'block', 'sda')
        >>> sda.device_number
        2048L
        >>> (os.major(sda.device_number), os.minor(sda.device_number))
        (8, 0)

        For devices with an associated :attr:`device_node`, this is the same as
        the ``st_rdev`` field of the stat result of the :attr:`device_node`:

        >>> os.stat(sda.device_node).st_rdev
        2048

        .. versionadded:: 0.11
        """
        return self._libudev.udev_device_get_devnum(self)

    @property
    def is_initialized(self):
        """
        ``True``, if the device is initialized, ``False`` otherwise.

        A device is initialized, if udev has already handled this device and
        has set up device node permissions and context, or renamed a network
        device.

        Consequently, this property is only implemented for devices with a
        device node or for network devices.  On all other devices this property
        is always ``True``.

        It is *not* recommended, that you use uninitialized devices.

        .. seealso:: :attr:`time_since_initialized`

        .. udevversion:: 165

        .. versionadded:: 0.8
        """
        return bool(self._libudev.udev_device_get_is_initialized(self))

    @property
    def time_since_initialized(self):
        """
        The time elapsed since initialization as :class:`~datetime.timedelta`.

        This property is only implemented on devices, which need to store
        properties in the udev database.  On all other devices this property is
        simply zero :class:`~datetime.timedelta`.

        .. seealso:: :attr:`is_initialized`

        .. udevversion:: 165

        .. versionadded:: 0.8
        """
        microseconds = self._libudev.udev_device_get_usec_since_initialized(self)
        return timedelta(microseconds=microseconds)

    @property
    def device_links(self):
        """
        An iterator, which yields the absolute paths (including the device
        directory, see :attr:`Context.device_path`) of all symbolic links
        pointing to the :attr:`device_node` of this device.  The paths are
        unicode strings.

        UDev can create symlinks to the original device node (see
        :attr:`device_node`) inside the device directory.  This is often
        used to assign a constant, fixed device node to devices like
        removeable media, which technically do not have a constant device
        node, or to map a single device into multiple device hierarchies.
        The property provides access to all such symbolic links, which were
        created by UDev for this device.

        .. warning::

           Links are not necessarily resolved by
           :meth:`Devices.from_device_file()`. Hence do *not* rely on
           ``Devices.from_device_file(context, link).device_path ==
           device.device_path`` from any ``link`` in ``device.device_links``.
        """
        devlinks = self._libudev.udev_device_get_devlinks_list_entry(self)
        for name, _ in udev_list_iterate(self._libudev, devlinks):
            yield ensure_unicode_string(name)

    @property
    def action(self):
        """
        The device event action as string, or ``None``, if this device was not
        received from a :class:`Monitor`.

        Usual actions are:

        ``'add'``
          A device has been added (e.g. a USB device was plugged in)
        ``'remove'``
          A device has been removed (e.g. a USB device was unplugged)
        ``'change'``
          Something about the device changed (e.g. a device property)
        ``'online'``
          The device is online now
        ``'offline'``
          The device is offline now

        .. warning::

           Though the actions listed above are the most common, this property
           *may* return other values, too, so be prepared to handle unknown
           actions!

        .. versionadded:: 0.16
        """
        action = self._libudev.udev_device_get_action(self)
        return ensure_unicode_string(action) if action is not None else None

    @property
    def sequence_number(self):
        """
        The device event sequence number as integer, or ``0`` if this device
        has no sequence number, i.e. was not received from a :class:`Monitor`.

        .. versionadded:: 0.16
        """
        return self._libudev.udev_device_get_seqnum(self)

    @property
    def attributes(self):
        """
        The system attributes of this device as read-only
        :class:`Attributes` mapping.

        System attributes are basically normal files inside the device
        directory.  These files contain all sorts of information about the
        device, which may not be reflected by properties.  These attributes
        are commonly used for matching in udev rules, and can be printed
        using ``udevadm info --attribute-walk``.

        The values of these attributes are not always proper strings, and
        can contain arbitrary bytes.

        :returns: an Attributes object, useful for reading attributes
        :rtype: Attributes

        .. versionadded:: 0.5
        """
        # do *not* cache the created object in an attribute of this class.
        # Doing so creates an uncollectable reference cycle between Device and
        # Attributes, because Attributes refers to this object through
        # Attributes.device.
        return Attributes(self)

    @property
    def properties(self):
        """
        The udev properties of this object as read-only Properties mapping.

        .. versionadded:: 0.21
        """
        return Properties(self)

    @property
    def tags(self):
        """
        A :class:`Tags` object representing the tags attached to this device.

        The :class:`Tags` object supports a test for a single tag as well as
        iteration over all tags:

        >>> from pyudev import Context
        >>> context = Context()
        >>> device = next(iter(context.list_devices(tag='systemd')))
        >>> 'systemd' in device.tags
        True
        >>> list(device.tags)
        [u'seat', u'systemd', u'uaccess']

        Tags are arbitrary classifiers that can be attached to devices by udev
        scripts and daemons.  For instance, systemd_ uses tags for multi-seat_
        support.

        .. _systemd: http://freedesktop.org/wiki/Software/systemd
        .. _multi-seat: http://www.freedesktop.org/wiki/Software/systemd/multiseat

        .. udevversion:: 154

        .. versionadded:: 0.6

        .. versionchanged:: 0.13
           Return a :class:`Tags` object now.
        """
        return Tags(self)

    def __iter__(self):
        """
        Iterate over the names of all properties defined for this device.

        Return a generator yielding the names of all properties of this
        device as unicode strings.

        .. deprecated:: 0.21
           Will be removed in 1.0. Access properties with Device.properties.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Access properties with Device.properties.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.properties.__iter__()

    def __len__(self):
        """
        Return the amount of properties defined for this device as integer.

        .. deprecated:: 0.21
           Will be removed in 1.0. Access properties with Device.properties.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Access properties with Device.properties.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.properties.__len__()

    def __getitem__(self, prop):
        """
        Get the given property from this device.

        ``prop`` is a unicode or byte string containing the name of the
        property.

        Return the property value as unicode string, or raise a
        :exc:`~exceptions.KeyError`, if the given property is not defined
        for this device.

        .. deprecated:: 0.21
           Will be removed in 1.0. Access properties with Device.properties.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Access properties with Device.properties.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.properties.__getitem__(prop)

    def asint(self, prop):
        """
        Get the given property from this device as integer.

        ``prop`` is a unicode or byte string containing the name of the
        property.

        Return the property value as integer. Raise a
        :exc:`~exceptions.KeyError`, if the given property is not defined
        for this device, or a :exc:`~exceptions.ValueError`, if the property
        value cannot be converted to an integer.

        .. deprecated:: 0.21
           Will be removed in 1.0. Use Device.properties.asint() instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use Device.properties.asint instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.properties.asint(prop)

    def asbool(self, prop):
        """
        Get the given property from this device as boolean.

        A boolean property has either a value of ``'1'`` or of ``'0'``,
        where ``'1'`` stands for ``True``, and ``'0'`` for ``False``.  Any
        other value causes a :exc:`~exceptions.ValueError` to be raised.

        ``prop`` is a unicode or byte string containing the name of the
        property.

        Return ``True``, if the property value is ``'1'`` and ``False``, if
        the property value is ``'0'``.  Any other value raises a
        :exc:`~exceptions.ValueError`.  Raise a :exc:`~exceptions.KeyError`,
        if the given property is not defined for this device.

        .. deprecated:: 0.21
           Will be removed in 1.0. Use Device.properties.asbool() instead.
        """
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. Use Device.properties.asbool instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.properties.asbool(prop)

    def __hash__(self):
        return hash(self.device_path)

    def __eq__(self, other):
        if isinstance(other, Device):
            return self.device_path == other.device_path
        return self.device_path == other

    def __ne__(self, other):
        if isinstance(other, Device):
            return self.device_path != other.device_path
        return self.device_path != other

    def __gt__(self, other):
        raise TypeError("Device not orderable")

    def __lt__(self, other):
        raise TypeError("Device not orderable")

    def __le__(self, other):
        raise TypeError("Device not orderable")

    def __ge__(self, other):
        raise TypeError("Device not orderable")


class Properties(collections.abc.Mapping):
    """
    udev properties :class:`Device` objects.

    .. versionadded:: 0.21
    """

    def __init__(self, device):
        collections.abc.Mapping.__init__(self)
        self.device = device
        self._libudev = device._libudev

    def __iter__(self):
        """
        Iterate over the names of all properties defined for the device.

        Return a generator yielding the names of all properties of this
        device as unicode strings.
        """
        properties = self._libudev.udev_device_get_properties_list_entry(self.device)
        for name, _ in udev_list_iterate(self._libudev, properties):
            yield ensure_unicode_string(name)

    def __len__(self):
        """
        Return the amount of properties defined for this device as integer.
        """
        properties = self._libudev.udev_device_get_properties_list_entry(self.device)
        return sum(1 for _ in udev_list_iterate(self._libudev, properties))

    def __getitem__(self, prop):
        """
        Get the given property from this device.

        ``prop`` is a unicode or byte string containing the name of the
        property.

        Return the property value as unicode string, or raise a
        :exc:`~exceptions.KeyError`, if the given property is not defined
        for this device.
        """
        value = self._libudev.udev_device_get_property_value(
            self.device, ensure_byte_string(prop)
        )
        if value is None:
            raise KeyError(prop)
        return ensure_unicode_string(value)

    def asint(self, prop):
        """
        Get the given property from this device as integer.

        ``prop`` is a unicode or byte string containing the name of the
        property.

        Return the property value as integer. Raise a
        :exc:`~exceptions.KeyError`, if the given property is not defined
        for this device, or a :exc:`~exceptions.ValueError`, if the property
        value cannot be converted to an integer.
        """
        return int(self[prop])

    def asbool(self, prop):
        """
        Get the given property from this device as boolean.

        A boolean property has either a value of ``'1'`` or of ``'0'``,
        where ``'1'`` stands for ``True``, and ``'0'`` for ``False``.  Any
        other value causes a :exc:`~exceptions.ValueError` to be raised.

        ``prop`` is a unicode or byte string containing the name of the
        property.

        Return ``True``, if the property value is ``'1'`` and ``False``, if
        the property value is ``'0'``.  Any other value raises a
        :exc:`~exceptions.ValueError`.  Raise a :exc:`~exceptions.KeyError`,
        if the given property is not defined for this device.
        """
        return string_to_bool(self[prop])


class Attributes(object):
    """
    udev attributes for :class:`Device` objects.

    .. versionadded:: 0.5
    """

    def __init__(self, device):
        self.device = device
        self._libudev = device._libudev

    @property
    def available_attributes(self):
        """
        Yield the ``available`` attributes for the device.

        It is not guaranteed that a key in this list will have a value.
        It is not guaranteed that a key not in this list will not have a value.

        It is guaranteed that the keys in this list are the keys that libudev
        considers to be "available" attributes.

        If libudev version does not define udev_device_get_sysattr_list_entry()
        yields nothing.

        See rhbz#1267584.
        """
        if not hasattr(self._libudev, "udev_device_get_sysattr_list_entry"):
            return  # pragma: no cover
        attrs = self._libudev.udev_device_get_sysattr_list_entry(self.device)
        for attribute, _ in udev_list_iterate(self._libudev, attrs):
            yield ensure_unicode_string(attribute)

    def _get(self, attribute):
        """
        Get the given system ``attribute`` for the device.

        :param attribute: the key for an attribute value
        :type attribute: unicode or byte string
        :returns: the value corresponding to ``attribute``
        :rtype: an arbitrary sequence of bytes
        :raises KeyError: if no value found
        """
        value = self._libudev.udev_device_get_sysattr_value(
            self.device, ensure_byte_string(attribute)
        )
        if value is None:
            raise KeyError(attribute)
        return value

    def get(self, attribute, default=None):
        """
        Get the given system ``attribute`` for the device.

        :param attribute: the key for an attribute value
        :type attribute: unicode or byte string
        :param default: a default if no corresponding value found
        :type default: a sequence of bytes
        :returns: the value corresponding to ``attribute`` or ``default``
        :rtype: object
        """
        try:
            return self._get(attribute)
        except KeyError:
            return default

    def asstring(self, attribute):
        """
        Get the given ``attribute`` for the device as unicode string.

        :param attribute: the key for an attribute value
        :type attribute: unicode or byte string
        :returns: the value corresponding to ``attribute``, as unicode
        :rtype: unicode
        :raises KeyError: if no value found for ``attribute``
        :raises UnicodeDecodeError: if value is not convertible
        """
        return ensure_unicode_string(self._get(attribute))

    def asint(self, attribute):
        """
        Get the given ``attribute`` as an int.

        :param attribute: the key for an attribute value
        :type attribute: unicode or byte string
        :returns: the value corresponding to ``attribute``, as an int
        :rtype: int
        :raises KeyError: if no value found for ``attribute``
        :raises UnicodeDecodeError: if value is not convertible to unicode
        :raises ValueError: if unicode value can not be converted to an int
        """
        return int(self.asstring(attribute))

    def asbool(self, attribute):
        """
        Get the given ``attribute`` from this device as a bool.

        :param attribute: the key for an attribute value
        :type attribute: unicode or byte string
        :returns: the value corresponding to ``attribute``, as bool
        :rtype: bool
        :raises KeyError: if no value found for ``attribute``
        :raises UnicodeDecodeError: if value is not convertible to unicode
        :raises ValueError: if unicode value can not be converted to a bool

        A boolean attribute has either a value of ``'1'`` or of ``'0'``,
        where ``'1'`` stands for ``True``, and ``'0'`` for ``False``.  Any
        other value causes a :exc:`~exceptions.ValueError` to be raised.
        """
        return string_to_bool(self.asstring(attribute))


class Tags(collections.abc.Iterable, collections.abc.Container):
    """
    A iterable over :class:`Device` tags.

    Subclasses the ``Container`` and the ``Iterable`` ABC.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, device):
        # pylint: disable=super-init-not-called
        collections.abc.Iterable.__init__(self)
        self.device = device
        self._libudev = device._libudev

    def _has_tag(self, tag):
        """
        Whether ``tag`` exists.

        :param tag: unicode string with name of tag
        :rtype: bool
        """
        if hasattr(self._libudev, "udev_device_has_tag"):
            return bool(
                self._libudev.udev_device_has_tag(self.device, ensure_byte_string(tag))
            )
        return any(t == tag for t in self)  # pragma: no cover

    def __contains__(self, tag):
        """
        Check for existence of ``tag``.

        ``tag`` is a tag as unicode string.

        Return ``True``, if ``tag`` is attached to the device, ``False``
        otherwise.
        """
        return self._has_tag(tag)

    def __iter__(self):
        """
        Iterate over all tags.

        Yield each tag as unicode string.
        """
        tags = self._libudev.udev_device_get_tags_list_entry(self.device)
        for tag, _ in udev_list_iterate(self._libudev, tags):
            yield ensure_unicode_string(tag)
