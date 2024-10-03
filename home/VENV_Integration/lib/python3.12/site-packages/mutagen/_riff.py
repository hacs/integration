# Copyright (C) 2017  Borewit
# Copyright (C) 2019-2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Resource Interchange File Format (RIFF)."""

import struct
from struct import pack

from mutagen._iff import (
    IffChunk,
    IffContainerChunkMixin,
    IffFile,
    InvalidChunk,
)


class RiffChunk(IffChunk):
    """Generic RIFF chunk"""

    @classmethod
    def parse_header(cls, header):
        return struct.unpack('<4sI', header)

    @classmethod
    def get_class(cls, id):
        if id in (u'LIST', u'RIFF'):
            return RiffListChunk
        else:
            return cls

    def write_new_header(self, id_, size):
        self._fileobj.write(pack('<4sI', id_, size))

    def write_size(self):
        self._fileobj.write(pack('<I', self.data_size))


class RiffListChunk(RiffChunk, IffContainerChunkMixin):
    """A RIFF chunk containing other chunks.
    This is either a 'LIST' or 'RIFF'
    """

    def parse_next_subchunk(self):
        return RiffChunk.parse(self._fileobj, self)

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id not in (u'RIFF', u'LIST'):
            raise InvalidChunk('Expected RIFF or LIST chunk, got %s' % id)

        RiffChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container()


class RiffFile(IffFile):
    """Representation of a RIFF file"""

    def __init__(self, fileobj):
        super().__init__(RiffChunk, fileobj)

        if self.root.id != u'RIFF':
            raise InvalidChunk("Root chunk must be a RIFF chunk, got %s"
                               % self.root.id)

        self.file_type = self.root.name
