# -*- coding: utf-8 -*-
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.

# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""pyudev.wx
    =========

    Wx integration.

    :class:`MonitorObserver` integrates device monitoring into the wxPython\\_
    mainloop by turing device events into wx events.

    :mod:`wx` from wxPython\\_ must be available when importing this module.

    .. _wxPython: http://wxpython.org/

    .. moduleauthor::  Tobias Eberle  <tobias.eberle@gmx.de>
    .. versionadded:: 0.14

"""

# isort: THIRDPARTY
from wx import EvtHandler, PostEvent  # pylint: disable=import-error
from wx.lib.newevent import NewEvent  # pylint: disable=import-error, no-name-in-module

# isort: LOCAL
# for some reason, pylint thinks pyudev is a third party import
import pyudev  # pylint: disable=wrong-import-order

DeviceEvent, EVT_DEVICE_EVENT = NewEvent()  # pylint: disable=invalid-name


class MonitorObserver(EvtHandler):
    """
    An observer for device events integrating into the :mod:`wx` mainloop.

    This class inherits :class:`~wx.EvtHandler` to turn device events into
    wx events:

    >>> from pyudev import Context, Monitor
    >>> from pyudev.wx import MonitorObserver
    >>> context = Context()
    >>> monitor = Monitor.from_netlink(context)
    >>> monitor.filter_by(subsystem='input')
    >>> observer = MonitorObserver(monitor)
    >>> def device_event(event):
    ...     print('action {0} on device {1}'.format(event.device.action, event.device))
    >>> observer.Bind(EVT_DEVICE_EVENT, device_event)
    >>> monitor.start()

    This class is a child of :class:`wx.EvtHandler`.

    .. versionadded:: 0.17
    """

    def __init__(self, monitor):
        EvtHandler.__init__(self)
        self.monitor = monitor
        self._observer_thread = None
        self.start()

    @property
    def enabled(self):
        """
        Whether this observer is enabled or not.

        If ``True`` (the default), this observer is enabled, and emits events.
        Otherwise it is disabled and does not emit any events.
        """
        return self._observer_thread is not None

    @enabled.setter
    def enabled(self, value):
        if value:
            self.start()
        else:
            self.stop()

    def start(self):
        """
        Enable this observer.

        Do nothing, if the observer is already enabled.
        """
        if self._observer_thread is not None:
            return
        self._observer_thread = pyudev.MonitorObserver(
            self.monitor, callback=self._emit_event, name="wx-observer-thread"
        )
        self._observer_thread.start()

    def stop(self):
        """
        Disable this observer.

        Do nothing, if the observer is already disabled.
        """
        if self._observer_thread is None:
            return
        self._observer_thread.stop()

    def _emit_event(self, device):
        PostEvent(self, DeviceEvent(device=device))


DeviceAddedEvent, EVT_DEVICE_ADDED = NewEvent()  # pylint: disable=invalid-name
DeviceRemovedEvent, EVT_DEVICE_REMOVED = NewEvent()  # pylint: disable=invalid-name
DeviceChangedEvent, EVT_DEVICE_CHANGED = NewEvent()  # pylint: disable=invalid-name
DeviceMovedEvent, EVT_DEVICE_MOVED = NewEvent()  # pylint: disable=invalid-name


class WxUDevMonitorObserver(MonitorObserver):
    """An observer for device events integrating into the :mod:`wx` mainloop.

    .. deprecated:: 0.17
       Will be removed in 1.0.  Use :class:`MonitorObserver` instead.
    """

    _action_event_map = {
        "add": DeviceAddedEvent,
        "remove": DeviceRemovedEvent,
        "change": DeviceChangedEvent,
        "move": DeviceMovedEvent,
    }

    def __init__(self, monitor):
        MonitorObserver.__init__(self, monitor)
        # isort: STDLIB
        import warnings

        warnings.warn(
            "Will be removed in 1.0. " "Use pyudev.wx.MonitorObserver instead.",
            DeprecationWarning,
        )

    def _emit_event(self, device):
        PostEvent(self, DeviceEvent(action=device.action, device=device))
        event_class = self._action_event_map.get(device.action)
        if event_class is not None:
            PostEvent(self, event_class(device=device))
