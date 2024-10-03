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
    pyudev.pyqt4
    ============

    PyQt4 integration.

    :class:`MonitorObserver` integrates device monitoring into the PyQt4\\_
    mainloop by turning device events into Qt signals.

    :mod:`PyQt4.QtCore` from PyQt4\\_ must be available when importing this
    module.

    .. _PyQt4: http://riverbankcomputing.co.uk/software/pyqt/intro

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: THIRDPARTY
from PyQt4 import QtCore  # pylint: disable=import-error

from ._qt_base import MonitorObserverGenerator, QUDevMonitorObserverGenerator

# pylint: disable=invalid-name
MonitorObserver = MonitorObserverGenerator.make_monitor_observer(
    QtCore.QObject, QtCore.pyqtSignal, QtCore.QSocketNotifier
)
"""
.. deprecated:: 0.17
   Will be removed in 1.0.  Use :class:`MonitorObserver` instead.
"""
QUDevMonitorObserver = QUDevMonitorObserverGenerator.make_monitor_observer(
    QtCore.QObject, QtCore.pyqtSignal, QtCore.QSocketNotifier
)
