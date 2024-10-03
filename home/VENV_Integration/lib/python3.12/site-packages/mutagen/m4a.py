# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
since 1.9: mutagen.m4a is deprecated; use mutagen.mp4 instead.
since 1.31: mutagen.m4a will no longer work; any operation that could fail
            will fail now.
"""

import warnings

from mutagen import FileType, Tags, StreamInfo
from ._util import DictProxy, MutagenError, loadfile

warnings.warn(
    "mutagen.m4a is deprecated; use mutagen.mp4 instead.",
    DeprecationWarning)


class error(MutagenError):
    pass


class M4AMetadataError(error):
    pass


class M4AStreamInfoError(error):
    pass


class M4AMetadataValueError(error):
    pass


__all__ = ['M4A', 'Open', 'delete', 'M4ACover']


class M4ACover(bytes):

    FORMAT_JPEG = 0x0D
    FORMAT_PNG = 0x0E

    def __new__(cls, data, imageformat=None):
        self = bytes.__new__(cls, data)
        if imageformat is None:
            imageformat = M4ACover.FORMAT_JPEG
        self.imageformat = imageformat
        return self


class M4ATags(DictProxy, Tags):

    def load(self, atoms, fileobj):
        raise error("deprecated")

    def save(self, filename):
        raise error("deprecated")

    def delete(self, filename):
        raise error("deprecated")

    def pprint(self):
        return u""


class M4AInfo(StreamInfo):

    bitrate = 0

    def __init__(self, atoms, fileobj):
        raise error("deprecated")

    def pprint(self):
        return u""


class M4A(FileType):

    _mimes = ["audio/mp4", "audio/x-m4a", "audio/mpeg4", "audio/aac"]

    @loadfile()
    def load(self, filething):
        raise error("deprecated")

    def add_tags(self):
        self.tags = M4ATags()

    @staticmethod
    def score(filename, fileobj, header):
        return 0


Open = M4A


def delete(filename):
    raise error("deprecated")
