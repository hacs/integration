# Copyright (C) 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen._util import cdata


def parse_full_atom(data):
    """Some atoms are versioned. Split them up in (version, flags, payload).
    Can raise ValueError.
    """

    if len(data) < 4:
        raise ValueError("not enough data")

    version = ord(data[0:1])
    flags = cdata.uint_be(b"\x00" + data[1:4])
    return version, flags, data[4:]
