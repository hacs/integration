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
    pyudev._os.pipe
    ===============

    Fallback implementations for pipe.

    1. pipe2 from python os module
    2. pipe2 from libc
    3. pipe from python os module

    The Pipe class wraps the chosen implementation.

    .. moduleauthor:: Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: STDLIB
import fcntl
import os
from functools import partial

# isort: LOCAL
from pyudev._ctypeslib.libc import ERROR_CHECKERS, FD_PAIR, SIGNATURES
from pyudev._ctypeslib.utils import load_ctypes_library

# Define O_CLOEXEC, if not present in os already
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0o2000000)


def _pipe2_ctypes(libc, flags):
    """A ``pipe2`` implementation using ``pipe2`` from ctypes.

    ``libc`` is a :class:`ctypes.CDLL` object for libc.  ``flags`` is an
    integer providing the flags to ``pipe2``.

    Return a pair of file descriptors ``(r, w)``.

    """
    fds = FD_PAIR()
    libc.pipe2(fds, flags)
    return fds[0], fds[1]


def _pipe2_by_pipe(flags):
    """A ``pipe2`` implementation using :func:`os.pipe`.

    ``flags`` is an integer providing the flags to ``pipe2``.

    .. warning::

       This implementation is not atomic!

    Return a pair of file descriptors ``(r, w)``.

    """
    fds = os.pipe()
    if flags & os.O_NONBLOCK != 0:
        for file_descriptor in fds:
            set_fd_status_flag(file_descriptor, os.O_NONBLOCK)
    if flags & O_CLOEXEC != 0:
        for file_descriptor in fds:
            set_fd_flag(file_descriptor, O_CLOEXEC)
    return fds


def _get_pipe2_implementation():
    """
    Find the appropriate implementation for ``pipe2``.

    Return a function implementing ``pipe2``."""
    if hasattr(os, "pipe2"):
        return os.pipe2  # pylint: disable=no-member
    try:
        libc = load_ctypes_library("libc", SIGNATURES, ERROR_CHECKERS)
        return (
            partial(_pipe2_ctypes, libc) if hasattr(libc, "pipe2") else _pipe2_by_pipe
        )
    except ImportError:
        return _pipe2_by_pipe


_PIPE2 = _get_pipe2_implementation()


def set_fd_flag(fd, flag):  # pylint: disable=invalid-name
    """Set a flag on a file descriptor.

    ``fd`` is the file descriptor or file object, ``flag`` the flag as integer.

    """
    flags = fcntl.fcntl(fd, fcntl.F_GETFD, 0)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | flag)


def set_fd_status_flag(fd, flag):  # pylint: disable=invalid-name
    """Set a status flag on a file descriptor.

    ``fd`` is the file descriptor or file object, ``flag`` the flag as integer.

    """
    flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | flag)


class Pipe:
    """A unix pipe.

    A pipe object provides two file objects: :attr:`source` is a readable file
    object, and :attr:`sink` a writeable.  Bytes written to :attr:`sink` appear
    at :attr:`source`.

    Open a pipe with :meth:`open()`.

    """

    @classmethod
    def open(cls):
        """Open and return a new :class:`Pipe`.

        The pipe uses non-blocking IO."""
        source, sink = _PIPE2(os.O_NONBLOCK | O_CLOEXEC)
        return cls(source, sink)

    def __init__(self, source_fd, sink_fd):
        """Create a new pipe object from the given file descriptors.

        ``source_fd`` is a file descriptor for the readable side of the pipe,
        ``sink_fd`` is a file descriptor for the writeable side."""
        self.source = os.fdopen(source_fd, "rb", 0)
        self.sink = os.fdopen(sink_fd, "wb", 0)

    def close(self):
        """Closes both sides of the pipe."""
        try:
            self.source.close()
        finally:
            self.sink.close()
