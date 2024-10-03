# -*- coding: utf-8 -*-
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
    pyudev.pyqt5
    ============

    PyQt5 integration.

    :class:`MonitorObserver` integrates device monitoring into the PyQt5_
    mainloop by turning device events into Qt signals.

    :mod:`PyQt5.QtCore` from PyQt5_ must be available when importing this
    module.

    .. _gPyQt5: http://riverbankcomputing.co.uk/software/pyqt/intro

    .. moduleauthor::  Tobias Gehring  <mail@tobiasgehring.de>
"""

# isort: THIRDPARTY
from PyQt5 import QtCore  # pylint: disable=import-error

from ._qt_base import MonitorObserverGenerator

# pylint: disable=invalid-name
MonitorObserver = MonitorObserverGenerator.make_monitor_observer(
    QtCore.QObject, QtCore.pyqtSignal, QtCore.QSocketNotifier
)
