# Copyright (C) 2014  Evan Purkhiser
#               2014  Ben Ockmore
#               2019-2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""AIFF audio stream information and tags."""

import struct
from struct import pack

from mutagen import StreamInfo, FileType

from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._iff import (
    IffChunk,
    IffContainerChunkMixin,
    IffFile,
    IffID3,
    InvalidChunk,
    error as IffError,
)
from mutagen._util import (
    convert_error,
    loadfile,
    endswith,
)

__all__ = ["AIFF", "Open", "delete"]


class error(IffError):
    pass


# based on stdlib's aifc
_HUGE_VAL = 1.79769313486231e+308


def read_float(data):
    """Raises OverflowError"""

    assert len(data) == 10
    expon, himant, lomant = struct.unpack('>hLL', data)
    sign = 1
    if expon < 0:
        sign = -1
        expon = expon + 0x8000
    if expon == himant == lomant == 0:
        f = 0.0
    elif expon == 0x7FFF:
        raise OverflowError("inf and nan not supported")
    else:
        expon = expon - 16383
        # this can raise OverflowError too
        f = (himant * 0x100000000 + lomant) * pow(2.0, expon - 63)
    return sign * f


class AIFFChunk(IffChunk):
    """Representation of a single IFF chunk"""

    @classmethod
    def parse_header(cls, header):
        return struct.unpack('>4sI', header)

    @classmethod
    def get_class(cls, id):
        if id == 'FORM':
            return AIFFFormChunk
        else:
            return cls

    def write_new_header(self, id_, size):
        self._fileobj.write(pack('>4sI', id_, size))

    def write_size(self):
        self._fileobj.write(pack('>I', self.data_size))


class AIFFFormChunk(AIFFChunk, IffContainerChunkMixin):
    """The  AIFF root chunk."""

    def parse_next_subchunk(self):
        return AIFFChunk.parse(self._fileobj, self)

    def __init__(self, fileobj, id, data_size, parent_chunk):
        if id != u'FORM':
            raise InvalidChunk('Expected FORM chunk, got %s' % id)

        AIFFChunk.__init__(self, fileobj, id, data_size, parent_chunk)
        self.init_container()


class AIFFFile(IffFile):
    """Representation of a AIFF file"""

    def __init__(self, fileobj):
        # AIFF Files always start with the FORM chunk which contains a 4 byte
        # ID before the start of other chunks
        super().__init__(AIFFChunk, fileobj)

        if self.root.id != u'FORM':
            raise InvalidChunk("Root chunk must be a FORM chunk, got %s"
                               % self.root.id)

    def __contains__(self, id_):
        if id_ == 'FORM':  # For backwards compatibility
            return True
        return super().__contains__(id_)

    def __getitem__(self, id_):
        if id_ == 'FORM':  # For backwards compatibility
            return self.root
        return super().__getitem__(id_)


class AIFFInfo(StreamInfo):
    """AIFFInfo()

    AIFF audio stream information.

    Information is parsed from the COMM chunk of the AIFF file

    Attributes:
        length (`float`): audio length, in seconds
        bitrate (`int`): audio bitrate, in bits per second
        channels (`int`): The number of audio channels
        sample_rate (`int`): audio sample rate, in Hz
        bits_per_sample (`int`): The audio sample size
    """

    length = 0
    bitrate = 0
    channels = 0
    sample_rate = 0

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""

        iff = AIFFFile(fileobj)
        try:
            common_chunk = iff[u'COMM']
        except KeyError as e:
            raise error(str(e))

        data = common_chunk.read()
        if len(data) < 18:
            raise error

        info = struct.unpack('>hLh10s', data[:18])
        channels, frame_count, sample_size, sample_rate = info

        try:
            self.sample_rate = int(read_float(sample_rate))
        except OverflowError:
            raise error("Invalid sample rate")
        if self.sample_rate < 0:
            raise error("Invalid sample rate")
        if self.sample_rate != 0:
            self.length = frame_count / float(self.sample_rate)

        self.bits_per_sample = sample_size
        self.sample_size = sample_size  # For backward compatibility
        self.channels = channels
        self.bitrate = channels * sample_size * self.sample_rate

    def pprint(self):
        return u"%d channel AIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _IFFID3(IffID3):
    """A AIFF file with ID3v2 tags"""

    def _load_file(self, fileobj):
        return AIFFFile(fileobj)


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Completely removes the ID3 chunk from the AIFF file"""

    try:
        del AIFFFile(filething.fileobj)[u'ID3']
    except KeyError:
        pass


class AIFF(FileType):
    """AIFF(filething)

    An AIFF audio file.

    Arguments:
        filething (filething)

    Attributes:
        tags (`mutagen.id3.ID3`)
        info (`AIFFInfo`)
    """

    _mimes = ["audio/aiff", "audio/x-aiff"]

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"FORM") * 2 + endswith(filename, b".aif") +
                endswith(filename, b".aiff") + endswith(filename, b".aifc"))

    def add_tags(self):
        """Add an empty ID3 tag to the file."""
        if self.tags is None:
            self.tags = _IFFID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething, **kwargs):
        """Load stream and tag information from a file."""

        fileobj = filething.fileobj

        try:
            self.tags = _IFFID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename

        fileobj.seek(0, 0)
        self.info = AIFFInfo(fileobj)


Open = AIFF
