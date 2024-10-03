# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Mutagen aims to be an all purpose multimedia tagging library.

::

    import mutagen.[format]
    metadata = mutagen.[format].Open(filename)

``metadata`` acts like a dictionary of tags in the file. Tags are generally a
list of string-like values, but may have additional methods available
depending on tag or format. They may also be entirely different objects
for certain keys, again depending on format.
"""

from mutagen._util import MutagenError
from mutagen._file import FileType, StreamInfo, File
from mutagen._tags import Tags, Metadata, PaddingInfo

version = (1, 47, 0)
"""Version tuple."""

version_string = ".".join(map(str, version))
"""Version string."""

MutagenError

FileType

StreamInfo

File

Tags

Metadata

PaddingInfo
