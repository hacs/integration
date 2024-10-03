# -*- coding: utf-8 -*-
# Copyright (C) 2013 Sebastian Wiesner <lunaryorn@gmail.com>

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
    pyudev._ctypeslib.utils
    =======================

    Utilities for loading ctypeslib.

    .. moduleauthor::  Anne Mulhern  <amulhern@redhat.com>
"""

# isort: STDLIB
from ctypes import CDLL
from ctypes.util import find_library


def load_ctypes_library(name, signatures, error_checkers):
    """
    Load library ``name`` and return a :class:`ctypes.CDLL` object for it.

    :param str name: the library name
    :param signatures: signatures of methods
    :type signatures: dict of str * (tuple of (list of type) * type)
    :param error_checkers: error checkers for methods
    :type error_checkers: dict of str * ((int * ptr * arglist) -> int)

    The library has errno handling enabled.
    Important functions are given proper signatures and return types to support
    type checking and argument conversion.

    :returns: a loaded library
    :rtype: ctypes.CDLL
    :raises ImportError: if the library is not found
    """
    library_name = find_library(name)
    if not library_name:
        raise ImportError("No library named %s" % name)
    lib = CDLL(library_name, use_errno=True)
    # Add function signatures
    for funcname, signature in signatures.items():
        function = getattr(lib, funcname, None)
        if function:
            argtypes, restype = signature
            function.argtypes = argtypes
            function.restype = restype
            errorchecker = error_checkers.get(funcname)
            if errorchecker:
                function.errcheck = errorchecker
    return lib
