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
    pyudev.pyside
    =============

    PySide integration.

    :class:`QUDevMonitorObserver` integrates device monitoring into the
    PySide\\_ mainloop by turing device events into Qt signals.

    :mod:`PySide.QtCore` from PySide\\_ must be available when importing this
    module.

    .. _PySide: http://www.pyside.org

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
    .. versionadded:: 0.6
"""

# isort: THIRDPARTY
from PySide6 import QtCore  # pylint: disable=import-error

from ._qt_base import MonitorObserverGenerator

# pylint: disable=invalid-name
MonitorObserver = MonitorObserverGenerator.make_monitor_observer(
    QtCore.QObject, QtCore.Signal, QtCore.QSocketNotifier
)
