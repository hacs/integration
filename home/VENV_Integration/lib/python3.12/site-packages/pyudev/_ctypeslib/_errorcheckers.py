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
    pyudev._ctypeslib._errorcheckers
    ================================

    Error checkers for ctypes wrappers.
"""

# isort: STDLIB
import errno
import os
from ctypes import get_errno

ERRNO_EXCEPTIONS = {
    errno.ENOMEM: MemoryError,
    errno.EOVERFLOW: OverflowError,
    errno.EINVAL: ValueError,
}


def exception_from_errno(errnum):
    """Create an exception from ``errnum``.

    ``errnum`` is an integral error number.

    Return an exception object appropriate to ``errnum``.

    """
    exception = ERRNO_EXCEPTIONS.get(errnum)
    errorstr = os.strerror(errnum)
    if exception is None:
        return EnvironmentError(errnum, errorstr)
    return exception(errorstr)


def check_negative_errorcode(result, _func, *_args):
    """Error checker for funtions, which return negative error codes.

    If ``result`` is smaller than ``0``, it is interpreted as negative error
    code, and an appropriate exception is raised:

    - ``-ENOMEM`` raises a :exc:`~exceptions.MemoryError`
    - ``-EOVERFLOW`` raises a :exc:`~exceptions.OverflowError`
    - all other error codes raise :exc:`~exceptions.EnvironmentError`

    If result is greater or equal to ``0``, it is returned unchanged.

    """
    if result < 0:
        # udev returns the *negative* errno code at this point
        errnum = -result
        raise exception_from_errno(errnum)
    else:
        return result


def check_errno_on_nonzero_return(result, _func, *_args):
    """Error checker to check the system ``errno`` as returned by
    :func:`ctypes.get_errno()`.

    If ``result`` is not ``0``, an exception according to this errno is raised.
    Otherwise nothing happens.

    """
    if result != 0:
        errnum = get_errno()
        if errnum != 0:
            raise exception_from_errno(errnum)
    return result


def check_errno_on_null_pointer_return(result, _func, *_args):
    """Error checker to check the system ``errno`` as returned by
    :func:`ctypes.get_errno()`.

    If ``result`` is a null pointer, an exception according to this errno is
    raised.  Otherwise nothing happens.

    """
    # pylint: disable=invalid-name
    if not result:
        errnum = get_errno()
        if errnum != 0:
            raise exception_from_errno(errnum)
    return result
