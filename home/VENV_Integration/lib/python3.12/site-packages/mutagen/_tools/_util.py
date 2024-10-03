# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import signal
import contextlib
import optparse

from mutagen._util import iterbytes


def split_escape(string, sep, maxsplit=None, escape_char="\\"):
    """Like unicode/str/bytes.split but allows for the separator to be escaped

    If passed unicode/str/bytes will only return list of unicode/str/bytes.
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    if isinstance(string, bytes):
        if isinstance(escape_char, str):
            escape_char = escape_char.encode("ascii")
        iter_ = iterbytes
    else:
        iter_ = iter

    if maxsplit is None:
        maxsplit = len(string)

    empty = string[:0]
    result = []
    current = empty
    escaped = False
    for char in iter_(string):
        if escaped:
            if char != escape_char and char != sep:
                current += escape_char
            current += char
            escaped = False
        else:
            if char == escape_char:
                escaped = True
            elif char == sep and len(result) < maxsplit:
                result.append(current)
                current = empty
            else:
                current += char
    result.append(current)
    return result


class SignalHandler(object):

    def __init__(self):
        self._interrupted = False
        self._nosig = False
        self._init = False

    def init(self):
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)
        if os.name != "nt":
            signal.signal(signal.SIGHUP, self._handler)

    def _handler(self, signum, frame):
        self._interrupted = True
        if not self._nosig:
            raise SystemExit("Aborted...")

    @contextlib.contextmanager
    def block(self):
        """While this context manager is active any signals for aborting
        the process will be queued and exit the program once the context
        is left.
        """

        self._nosig = True
        yield
        self._nosig = False
        if self._interrupted:
            raise SystemExit("Aborted...")


OptionParser = optparse.OptionParser
