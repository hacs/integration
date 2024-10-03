# -*- coding: utf-8 -*-
# Copyright (C) 2010, 2011, 2012, 2013 Sebastian Wiesner <lunaryorn@gmail.com>

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
    pyudev._qt_base
    ===============

    Base mixin class for Qt4,Qt5 support.

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: LOCAL
from pyudev.device import Device


class MonitorObserverMixin(object):
    """
    Base mixin for pyqt monitor observers.
    """

    # pylint: disable=too-few-public-methods

    def _setup_notifier(self, monitor, notifier_class):
        self.monitor = monitor
        self.notifier = notifier_class(monitor.fileno(), notifier_class.Read, self)
        self.notifier.activated[int].connect(self._process_udev_event)

    @property
    def enabled(self):
        """
        Whether this observer is enabled or not.

        If ``True`` (the default), this observer is enabled, and emits events.
        Otherwise it is disabled and does not emit any events.  This merely
        reflects the state of the ``enabled`` property of the underlying
        :attr:`notifier`.

        .. versionadded:: 0.14
        """
        return self.notifier.isEnabled()

    @enabled.setter
    def enabled(self, value):
        self.notifier.setEnabled(value)

    def _process_udev_event(self):
        """
        Attempt to receive a single device event from the monitor, process
        the event and emit corresponding signals.

        Called by ``QSocketNotifier``, if data is available on the udev
        monitoring socket.
        """
        device = self.monitor.poll(timeout=0)
        if device is not None:
            self._emit_event(device)

    def _emit_event(self, device):
        self.deviceEvent.emit(device)


class QUDevMonitorObserverMixin(MonitorObserverMixin):
    """
    Obsolete monitor observer mixin.
    """

    # pylint: disable=too-few-public-methods

    def _setup_notifier(self, monitor, notifier_class):
        MonitorObserverMixin._setup_notifier(self, monitor, notifier_class)
        self._action_signal_map = {
            "add": self.deviceAdded,
            "remove": self.deviceRemoved,
            "change": self.deviceChanged,
            "move": self.deviceMoved,
        }
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. " "Use pyudev.pyqt4.MonitorObserver instead.",
            DeprecationWarning,
        )

    def _emit_event(self, device):
        self.deviceEvent.emit(device.action, device)
        signal = self._action_signal_map.get(device.action)
        if signal is not None:
            signal.emit(device)


def make_init(qobject, socket_notifier):
    """
    Generates an initializer to observer the given ``monitor``
    (a :class:`~pyudev.Monitor`):

    ``parent`` is the parent :class:`~PyQt{4,5}.QtCore.QObject` of this
    object.  It is passed unchanged to the inherited constructor of
    :class:`~PyQt{4,5}.QtCore.QObject`.
    """

    def __init__(self, monitor, parent=None):
        qobject.__init__(self, parent)
        # pylint: disable=protected-access
        self._setup_notifier(monitor, socket_notifier)

    return __init__


class MonitorObserverGenerator(object):
    """
    Class to generate a MonitorObserver class.
    """

    # pylint: disable=too-few-public-methods

    @staticmethod
    def make_monitor_observer(qobject, signal, socket_notifier):
        """Generates an observer for device events integrating into the
        PyQt{4,5} mainloop.

        This class inherits :class:`~PyQt{4,5}.QtCore.QObject` to turn device
        events into Qt signals:

        >>> from pyudev import Context, Monitor
        >>> from pyudev.pyqt4 import MonitorObserver
        >>> context = Context()
        >>> monitor = Monitor.from_netlink(context)
        >>> monitor.filter_by(subsystem='input')
        >>> observer = MonitorObserver(monitor)
        >>> def device_event(device):
        ...     print('event {0} on device {1}'.format(device.action, device))
        >>> observer.deviceEvent.connect(device_event)
        >>> monitor.start()

        This class is a child of :class:`~{PySide, PyQt{4,5}}.QtCore.QObject`.

        """
        return type(
            str("MonitorObserver"),
            (qobject, MonitorObserverMixin),
            {
                str("__init__"): make_init(qobject, socket_notifier),
                str("deviceEvent"): signal(Device),
            },
        )


class QUDevMonitorObserverGenerator(object):
    """
    Class to generate a MonitorObserver class.
    """

    # pylint: disable=too-few-public-methods

    @staticmethod
    def make_monitor_observer(qobject, signal, socket_notifier):
        """Generates an observer for device events integrating into the
        PyQt{4,5} mainloop.

        This class inherits :class:`~PyQt{4,5}.QtCore.QObject` to turn device
        events into Qt signals:

        >>> from pyudev import Context, Monitor
        >>> from pyudev.pyqt4 import MonitorObserver
        >>> context = Context()
        >>> monitor = Monitor.from_netlink(context)
        >>> monitor.filter_by(subsystem='input')
        >>> observer = MonitorObserver(monitor)
        >>> def device_event(device):
        ...     print('event {0} on device {1}'.format(device.action, device))
        >>> observer.deviceEvent.connect(device_event)
        >>> monitor.start()

        This class is a child of :class:`~{PyQt{4,5}, PySide}.QtCore.QObject`.

        """
        return type(
            str("QUDevMonitorObserver"),
            (qobject, QUDevMonitorObserverMixin),
            {
                str("__init__"): make_init(qobject, socket_notifier),
                #: emitted upon arbitrary device events
                str("deviceEvent"): signal(str, Device),
                #: emitted if a device was added
                str("deviceAdded"): signal(Device),
                #: emitted if a device was removed
                str("deviceRemoved"): signal(Device),
                #: emitted if a device was changed
                str("deviceChanged"): signal(Device),
                #: emitted if a device was moved
                str("deviceMoved"): signal(Device),
            },
        )
