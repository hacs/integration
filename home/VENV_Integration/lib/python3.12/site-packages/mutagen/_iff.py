# Copyright (C) 2014  Evan Purkhiser
#               2014  Ben Ockmore
#               2017  Borewit
#               2019-2021  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Base classes for various IFF based formats (e.g. AIFF or RIFF)."""

import sys

from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._util import (
    MutagenError,
    convert_error,
    delete_bytes,
    insert_bytes,
    loadfile,
    reraise,
    resize_bytes,
)


class error(MutagenError):
    pass


class InvalidChunk(error):
    pass


class EmptyChunk(InvalidChunk):
    pass


def is_valid_chunk_id(id: str) -> bool:
    """ is_valid_chunk_id(FOURCC)

    Arguments:
        id (FOURCC)
    Returns:
        true if valid; otherwise false

    Check if argument id is valid FOURCC type.
    """

    assert isinstance(id, str), \
        'id is of type %s, must be str: %r' % (type(id), id)

    return ((0 < len(id) <= 4) and (min(id) >= ' ') and
            (max(id) <= '~'))


#  Assert FOURCC formatted valid
def assert_valid_chunk_id(id: str) -> None:
    if not is_valid_chunk_id(id):
        raise ValueError("IFF chunk ID must be four ASCII characters.")


class IffChunk(object):
    """Generic representation of a single IFF chunk.

    IFF chunks always consist of an ID followed by the chunk size. The exact
    format varies between different IFF based formats, e.g. AIFF uses
    big-endian while RIFF uses little-endian.
    """

    # Chunk headers are usually 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    @classmethod
    def parse_header(cls, header):
        """Read ID and data_size from the given header.
        Must be implemented in subclasses."""
        raise error("Not implemented")

    def write_new_header(self, id_, size):
        """Write the chunk header with id_ and size to the file.
        Must be implemented in subclasses. The data must be written
        to the current position in self._fileobj."""
        raise error("Not implemented")

    def write_size(self):
        """Write self.data_size to the file.
        Must be implemented in subclasses. The data must be written
        to the current position in self._fileobj."""
        raise error("Not implemented")

    @classmethod
    def get_class(cls, id):
        """Returns the class for a new chunk for a given ID.
        Can be overridden in subclasses to implement specific chunk types."""
        return cls

    @classmethod
    def parse(cls, fileobj, parent_chunk=None):
        header = fileobj.read(cls.HEADER_SIZE)
        if len(header) < cls.HEADER_SIZE:
            raise EmptyChunk('Header size < %i' % cls.HEADER_SIZE)
        id, data_size = cls.parse_header(header)
        try:
            id = id.decode('ascii').rstrip()
        except UnicodeDecodeError as e:
            raise InvalidChunk(e)

        if not is_valid_chunk_id(id):
            raise InvalidChunk('Invalid chunk ID %r' % id)

        return cls.get_class(id)(fileobj, id, data_size, parent_chunk)

    def __init__(self, fileobj, id, data_size, parent_chunk):
        self._fileobj = fileobj
        self.id = id
        self.data_size = data_size
        self.parent_chunk = parent_chunk
        self.data_offset = fileobj.tell()
        self.offset = self.data_offset - self.HEADER_SIZE
        self._calculate_size()

    def __repr__(self):
        return ("<%s id=%s, offset=%i, size=%i, data_offset=%i, data_size=%i>"
            % (type(self).__name__, self.id, self.offset, self.size,
               self.data_offset, self.data_size))

    def read(self) -> bytes:
        """Read the chunks data"""

        self._fileobj.seek(self.data_offset)
        return self._fileobj.read(self.data_size)

    def write(self, data: bytes) -> None:
        """Write the chunk data"""

        if len(data) > self.data_size:
            raise ValueError

        self._fileobj.seek(self.data_offset)
        self._fileobj.write(data)
        # Write the padding bytes
        padding = self.padding()
        if padding:
            self._fileobj.seek(self.data_offset + self.data_size)
            self._fileobj.write(b'\x00' * padding)

    def delete(self) -> None:
        """Removes the chunk from the file"""

        delete_bytes(self._fileobj, self.size, self.offset)
        if self.parent_chunk is not None:
            self.parent_chunk._remove_subchunk(self)
        self._fileobj.flush()

    def _update_size(self, size_diff, changed_subchunk=None):
        """Update the size of the chunk"""

        old_size = self.size
        self.data_size += size_diff
        self._fileobj.seek(self.offset + 4)
        self.write_size()
        self._calculate_size()
        if self.parent_chunk is not None:
            self.parent_chunk._update_size(self.size - old_size, self)
        if changed_subchunk:
            self._update_sibling_offsets(
                changed_subchunk, old_size - self.size)

    def _calculate_size(self):
        self.size = self.HEADER_SIZE + self.data_size + self.padding()
        assert self.size % 2 == 0

    def resize(self, new_data_size: int) -> None:
        """Resize the file and update the chunk sizes"""

        old_size = self._get_actual_data_size()
        padding = new_data_size % 2
        resize_bytes(self._fileobj, old_size,
                     new_data_size + padding, self.data_offset)
        size_diff = new_data_size - self.data_size
        self._update_size(size_diff)
        self._fileobj.flush()

    def padding(self) -> int:
        """Returns the number of padding bytes (0 or 1).
        IFF chunks are required to be a even number in total length. If
        data_size is odd a padding byte will be added at the end.
        """
        return self.data_size % 2

    def _get_actual_data_size(self) -> int:
        """Returns the data size that is actually possible.
        Some files have chunks that are truncated and their reported size
        would be outside of the file's actual size."""
        fileobj = self._fileobj
        fileobj.seek(0, 2)
        file_size = fileobj.tell()

        expected_size = self.data_size + self.padding()
        max_size_possible = file_size - self.data_offset
        return min(expected_size, max_size_possible)


class IffContainerChunkMixin():
    """A IFF chunk containing other chunks.

    A container chunk can have an additional name as the first 4 bytes of the
    chunk data followed by an arbitrary number of subchunks. The root chunk of
    the file is always a container chunk (e.g. the AIFF chunk or the FORM chunk
    for RIFF) but there can be other types of container chunks (e.g. the LIST
    chunks used in RIFF).
    """

    def parse_next_subchunk(self):
        """"""
        raise error("Not implemented")

    def init_container(self, name_size=4):
        # Lists can store an additional name identifier before the subchunks
        self.__name_size = name_size
        if self.data_size < name_size:
            raise InvalidChunk(
                'Container chunk data size < %i' % name_size)

        # Read the container name
        if name_size > 0:
            try:
                self.name = self._fileobj.read(name_size).decode('ascii')
            except UnicodeDecodeError as e:
                raise error(e)
        else:
            self.name = None

        # Load all IFF subchunks
        self.__subchunks = []

    def subchunks(self):
        """Returns a list of all subchunks.
        The list is lazily loaded on first access.
        """
        if not self.__subchunks:
            next_offset = self.data_offset + self.__name_size
            while next_offset < self.offset + self.size:
                self._fileobj.seek(next_offset)
                try:
                    chunk = self.parse_next_subchunk()
                except EmptyChunk:
                    break
                except InvalidChunk:
                    break
                self.__subchunks.append(chunk)

                # Calculate the location of the next chunk
                next_offset = chunk.offset + chunk.size
        return self.__subchunks

    def insert_chunk(self, id_, data=None):
        """Insert a new chunk at the end of the container chunk"""

        if not is_valid_chunk_id(id_):
            raise KeyError("Invalid IFF key.")

        next_offset = self.data_offset + self._get_actual_data_size()
        size = self.HEADER_SIZE
        data_size = 0
        if data:
            data_size = len(data)
            padding = data_size % 2
            size += data_size + padding
        insert_bytes(self._fileobj, size, next_offset)
        self._fileobj.seek(next_offset)
        self.write_new_header(id_.ljust(4).encode('ascii'), data_size)
        self._fileobj.seek(next_offset)
        chunk = self.parse_next_subchunk()
        self._update_size(chunk.size)
        if data:
            chunk.write(data)
        self.subchunks().append(chunk)
        self._fileobj.flush()
        return chunk

    def __contains__(self, id_):
        """Check if this chunk contains a specific subchunk."""
        assert_valid_chunk_id(id_)
        try:
            self[id_]
            return True
        except KeyError:
            return False

    def __getitem__(self, id_):
        """Get a subchunk by ID."""
        assert_valid_chunk_id(id_)
        found_chunk = None
        for chunk in self.subchunks():
            if chunk.id == id_:
                found_chunk = chunk
                break
        else:
            raise KeyError("No %r chunk found" % id_)
        return found_chunk

    def __delitem__(self, id_):
        """Remove a chunk from the IFF file"""
        assert_valid_chunk_id(id_)
        self[id_].delete()

    def _remove_subchunk(self, chunk):
        assert chunk in self.__subchunks
        self._update_size(-chunk.size, chunk)
        self.__subchunks.remove(chunk)

    def _update_sibling_offsets(self, changed_subchunk, size_diff):
        """Update the offsets of subchunks after `changed_subchunk`.
        """
        index = self.__subchunks.index(changed_subchunk)
        sibling_chunks = self.__subchunks[index + 1:len(self.__subchunks)]
        for sibling in sibling_chunks:
            sibling.offset -= size_diff
            sibling.data_offset -= size_diff


class IffFile:
    """Representation of a IFF file"""

    def __init__(self, chunk_cls, fileobj):
        fileobj.seek(0)
        self.root = chunk_cls.parse(fileobj)

    def __contains__(self, id_):
        """Check if the IFF file contains a specific chunk"""
        return id_ in self.root

    def __getitem__(self, id_):
        """Get a chunk from the IFF file"""
        return self.root[id_]

    def __delitem__(self, id_):
        """Remove a chunk from the IFF file"""
        self.delete_chunk(id_)

    def delete_chunk(self, id_):
        """Remove a chunk from the IFF file"""
        del self.root[id_]

    def insert_chunk(self, id_, data=None):
        """Insert a new chunk at the end of the IFF file"""
        return self.root.insert_chunk(id_, data)


class IffID3(ID3):
    """A generic IFF file with ID3v2 tags"""

    def _load_file(self, fileobj):
        raise error("Not implemented")

    def _pre_load_header(self, fileobj):
        try:
            fileobj.seek(self._load_file(fileobj)['ID3'].data_offset)
        except (InvalidChunk, KeyError):
            raise ID3NoHeaderError("No ID3 chunk")

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething=None, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the IFF file"""

        fileobj = filething.fileobj

        iff_file = self._load_file(fileobj)

        if 'ID3' not in iff_file:
            iff_file.insert_chunk('ID3')

        chunk = iff_file['ID3']

        try:
            data = self._prepare_data(
                fileobj, chunk.data_offset, chunk.data_size, v2_version,
                v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        chunk.resize(len(data))
        chunk.write(data)

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def delete(self, filething=None):
        """Completely removes the ID3 chunk from the IFF file"""

        try:
            iff_file = self._load_file(filething.fileobj)
            del iff_file['ID3']
        except KeyError:
            pass
        self.clear()
