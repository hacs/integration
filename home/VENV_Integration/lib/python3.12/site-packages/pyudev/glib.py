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
"""pyudev.glib
    ===========

    Glib integration.

    :class:`MonitorObserver` integrates device monitoring into the Glib
    mainloop by turing device events into Glib signals.

    :mod:`gi.repository.GLib` and :mod:`gi.repository.GObject` from PyGObject_
    must be available when importing this module. PyGtk is not required.

    .. _PyGObject: http://www.pygtk.org/

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
    .. versionadded:: 0.7

"""

# isort: THIRDPARTY
from gi.repository import GLib, GObject  # pylint: disable=import-error


class _ObserverMixin(object):
    """Mixin to provide observer behavior to the old and the new API."""

    # pylint: disable=too-few-public-methods

    def _setup_observer(self, monitor):
        # pylint: disable=attribute-defined-outside-init
        self.monitor = monitor
        self.event_source = None
        self.enabled = True

    @property
    def enabled(self):
        """
        Whether this observer is enabled or not.

        If ``True`` (the default), this observer is enabled, and emits events.
        Otherwise it is disabled and does not emit any events.

        .. versionadded:: 0.14
        """
        return self.event_source is not None

    @enabled.setter
    def enabled(self, value):
        if value and self.event_source is None:
            # pylint: disable=attribute-defined-outside-init
            # pylint: disable=no-member
            self.event_source = GLib.io_add_watch(
                self.monitor,
                GLib.PRIORITY_DEFAULT,
                GLib.IO_IN,
                self._process_udev_event,
            )
        elif not value and self.event_source is not None:
            # pylint: disable=no-member
            GLib.source_remove(self.event_source)

    def _process_udev_event(self, source, condition):
        # pylint: disable=unused-argument
        # pylint: disable=no-member
        if condition == GLib.IO_IN:
            device = self.monitor.poll(timeout=0)
            if device is not None:
                self._emit_event(device)
        return True

    def _emit_event(self, device):
        self.emit("device-event", device)


class MonitorObserver(GObject.Object, _ObserverMixin):
    # pylint: disable=too-few-public-methods
    """
    An observer for device events integrating into the :mod:`gi.repository.GLib`
    mainloop.

    This class inherits :class:`~gi.repository.GObject.Object` to turn device
    events into glib signals.

    >>> from pyudev import Context, Monitor
    >>> from pyudev.glib import MonitorObserver
    >>> context = Context()
    >>> monitor = Monitor.from_netlink(context)
    >>> monitor.filter_by(subsystem='input')
    >>> observer = MonitorObserver(monitor)
    >>> def device_event(observer, device):
    ...     print('event {0} on device {1}'.format(device.action, device))
    >>> observer.connect('device-event', device_event)
    >>> monitor.start()

    This class is a child of :class:`gi.repository.GObject.Object`.
    """

    __gsignals__ = {
        # explicitly convert the signal to str, because glib expects the
        # *native* string type of the corresponding python version as type of
        # signal name, and str() is the name of the native string type of both
        # python versions.  We could also remove the "unicode_literals" import,
        # but I don't want to make exceptions to the standard set of future
        # imports used throughout pyudev for the sake of consistency.
        str("device-event"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(self, monitor):
        GObject.Object.__init__(self)
        self._setup_observer(monitor)


GObject.type_register(MonitorObserver)


class GUDevMonitorObserver(GObject.Object, _ObserverMixin):
    # pylint: disable=too-few-public-methods
    """
    An observer for device events integrating into the :mod:`gi.repository.GLib`
    mainloop.

    .. deprecated:: 0.17
       Will be removed in 1.0.  Use :class:`MonitorObserver` instead.
    """

    _action_signal_map = {
        "add": "device-added",
        "remove": "device-removed",
        "change": "device-changed",
        "move": "device-moved",
    }

    __gsignals__ = {
        str("device-event"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_STRING, GObject.TYPE_PYOBJECT),
        ),
        str("device-added"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,),
        ),
        str("device-removed"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,),
        ),
        str("device-changed"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,),
        ),
        str("device-moved"): (
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,),
        ),
    }

    def __init__(self, monitor):
        GObject.Object.__init__(self)
        self._setup_observer(monitor)
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. " "Use pyudev.glib.MonitorObserver instead.",
            DeprecationWarning,
        )

    def _emit_event(self, device):
        self.emit("device-event", device.action, device)
        signal = self._action_signal_map.get(device.action)
        if signal is not None:
            self.emit(signal, device)


GObject.type_register(GUDevMonitorObserver)
