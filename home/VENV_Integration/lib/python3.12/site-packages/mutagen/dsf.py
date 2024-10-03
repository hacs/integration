# Copyright (C) 2017  Boris Pruessmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write DSF audio stream information and tags."""


import sys
import struct
from io import BytesIO

from mutagen import FileType, StreamInfo
from mutagen._util import cdata, MutagenError, loadfile, \
    convert_error, reraise, endswith
from mutagen.id3 import ID3
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error


__all__ = ["DSF", "Open", "delete"]


class error(MutagenError):
    pass


class DSFChunk(object):
    """A generic chunk of a DSFFile."""

    chunk_offset = 0
    chunk_header = "    "
    chunk_size = -1

    def __init__(self, fileobj, create=False):
        self.fileobj = fileobj

        if not create:
            self.chunk_offset = fileobj.tell()
            self.load()

    def load(self):
        raise NotImplementedError

    def write(self):
        raise NotImplementedError


class DSDChunk(DSFChunk):
    """Represents the first chunk of a DSF file"""

    CHUNK_SIZE = 28

    total_size = 0
    offset_metdata_chunk = 0

    def __init__(self, fileobj, create=False):
        super(DSDChunk, self).__init__(fileobj, create)

        if create:
            self.chunk_header = b"DSD "
            self.chunk_size = DSDChunk.CHUNK_SIZE

    def load(self):
        data = self.fileobj.read(DSDChunk.CHUNK_SIZE)
        if len(data) != DSDChunk.CHUNK_SIZE:
            raise error("DSF chunk truncated")

        self.chunk_header = data[0:4]
        if self.chunk_header != b"DSD ":
            raise error("DSF dsd header not found")

        self.chunk_size = cdata.ulonglong_le(data[4:12])
        if self.chunk_size != DSDChunk.CHUNK_SIZE:
            raise error("DSF dsd header size mismatch")

        self.total_size = cdata.ulonglong_le(data[12:20])
        self.offset_metdata_chunk = cdata.ulonglong_le(data[20:28])

    def write(self):
        f = BytesIO()
        f.write(self.chunk_header)
        f.write(struct.pack("<Q", DSDChunk.CHUNK_SIZE))
        f.write(struct.pack("<Q", self.total_size))
        f.write(struct.pack("<Q", self.offset_metdata_chunk))

        self.fileobj.seek(self.chunk_offset)
        self.fileobj.write(f.getvalue())

    def pprint(self):
        return (u"DSD Chunk (Total file size = %d, "
                u"Pointer to Metadata chunk = %d)" % (
                    self.total_size, self.offset_metdata_chunk))


class FormatChunk(DSFChunk):

    CHUNK_SIZE = 52

    VERSION = 1

    FORMAT_DSD_RAW = 0
    """Format ID: DSD Raw"""

    format_version = VERSION
    format_id = FORMAT_DSD_RAW
    channel_type = 1
    channel_num = 1
    sampling_frequency = 2822400
    bits_per_sample = 1
    sample_count = 0
    block_size_per_channel = 4096

    def __init__(self, fileobj, create=False):
        super(FormatChunk, self).__init__(fileobj, create)

        if create:
            self.chunk_header = b"fmt "
            self.chunk_size = FormatChunk.CHUNK_SIZE

    def load(self):
        data = self.fileobj.read(FormatChunk.CHUNK_SIZE)
        if len(data) != FormatChunk.CHUNK_SIZE:
            raise error("DSF chunk truncated")

        self.chunk_header = data[0:4]
        if self.chunk_header != b"fmt ":
            raise error("DSF fmt header not found")

        self.chunk_size = cdata.ulonglong_le(data[4:12])
        if self.chunk_size != FormatChunk.CHUNK_SIZE:
            raise error("DSF dsd header size mismatch")

        self.format_version = cdata.uint_le(data[12:16])
        if self.format_version != FormatChunk.VERSION:
            raise error("Unsupported format version")

        self.format_id = cdata.uint_le(data[16:20])
        if self.format_id != FormatChunk.FORMAT_DSD_RAW:
            raise error("Unsupported format ID")

        self.channel_type = cdata.uint_le(data[20:24])
        self.channel_num = cdata.uint_le(data[24:28])
        self.sampling_frequency = cdata.uint_le(data[28:32])
        self.bits_per_sample = cdata.uint_le(data[32:36])
        self.sample_count = cdata.ulonglong_le(data[36:44])

    def pprint(self):
        return u"fmt Chunk (Channel Type = %d, Channel Num = %d, " \
               u"Sampling Frequency = %d, %.2f seconds)" % \
               (self.channel_type, self.channel_num, self.sampling_frequency,
                self.length)


class DataChunk(DSFChunk):

    CHUNK_SIZE = 12

    data = ""

    def __init__(self, fileobj, create=False):
        super(DataChunk, self).__init__(fileobj, create)

        if create:
            self.chunk_header = b"data"
            self.chunk_size = DataChunk.CHUNK_SIZE

    def load(self):
        data = self.fileobj.read(DataChunk.CHUNK_SIZE)
        if len(data) != DataChunk.CHUNK_SIZE:
            raise error("DSF chunk truncated")

        self.chunk_header = data[0:4]
        if self.chunk_header != b"data":
            raise error("DSF data header not found")

        self.chunk_size = cdata.ulonglong_le(data[4:12])
        if self.chunk_size < DataChunk.CHUNK_SIZE:
            raise error("DSF data header size mismatch")

    def pprint(self):
        return u"data Chunk (Chunk Offset = %d, Chunk Size = %d)" % (
            self.chunk_offset, self.chunk_size)


class _DSFID3(ID3):
    """A DSF file with ID3v2 tags"""

    @convert_error(IOError, error)
    def _pre_load_header(self, fileobj):
        fileobj.seek(0)
        id3_location = DSDChunk(fileobj).offset_metdata_chunk
        if id3_location == 0:
            raise ID3NoHeaderError("File has no existing ID3 tag")

        fileobj.seek(id3_location)

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething=None, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the DSF file"""

        fileobj = filething.fileobj
        fileobj.seek(0)

        dsd_header = DSDChunk(fileobj)
        if dsd_header.offset_metdata_chunk == 0:
            # create a new ID3 chunk at the end of the file
            fileobj.seek(0, 2)

            # store reference to ID3 location
            dsd_header.offset_metdata_chunk = fileobj.tell()
            dsd_header.write()

        try:
            data = self._prepare_data(
                fileobj, dsd_header.offset_metdata_chunk, self.size,
                v2_version, v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        fileobj.seek(dsd_header.offset_metdata_chunk)
        fileobj.write(data)
        fileobj.truncate()

        # Update total file size
        dsd_header.total_size = fileobj.tell()
        dsd_header.write()


class DSFInfo(StreamInfo):
    """DSF audio stream information.

    Information is parsed from the fmt chunk of the DSF file.

    Attributes:
        length (`float`): audio length, in seconds.
        channels (`int`): The number of audio channels.
        sample_rate (`int`):
            Sampling frequency, in Hz.
            (2822400, 5644800, 11289600, or 22579200)
        bits_per_sample (`int`): The audio sample size.
        bitrate (`int`): The audio bitrate.
    """

    def __init__(self, fmt_chunk):
        self.fmt_chunk = fmt_chunk

    @property
    def length(self):
        return float(self.fmt_chunk.sample_count) / self.sample_rate

    @property
    def channels(self):
        return self.fmt_chunk.channel_num

    @property
    def sample_rate(self):
        return self.fmt_chunk.sampling_frequency

    @property
    def bits_per_sample(self):
        return self.fmt_chunk.bits_per_sample

    @property
    def bitrate(self):
        return self.sample_rate * self.bits_per_sample * self.channels

    def pprint(self):
        return u"%d channel DSF @ %d bits, %s Hz, %.2f seconds" % (
            self.channels, self.bits_per_sample, self.sample_rate, self.length)


class DSFFile(object):

    dsd_chunk = None
    fmt_chunk = None
    data_chunk = None

    def __init__(self, fileobj):
        self.dsd_chunk = DSDChunk(fileobj)
        self.fmt_chunk = FormatChunk(fileobj)
        self.data_chunk = DataChunk(fileobj)


class DSF(FileType):
    """An DSF audio file.

    Arguments:
        filething (filething)

    Attributes:
        info (`DSFInfo`)
        tags (`mutagen.id3.ID3Tags` or `None`)
    """

    _mimes = ["audio/dsf"]

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"DSD ") * 2 + \
            endswith(filename.lower(), ".dsf")

    def add_tags(self):
        """Add a DSF tag block to the file."""

        if self.tags is None:
            self.tags = _DSFID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething, **kwargs):
        dsf_file = DSFFile(filething.fileobj)

        try:
            self.tags = _DSFID3(filething.fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename

        self.info = DSFInfo(dsf_file.fmt_chunk)

    @loadfile(writable=True)
    def delete(self, filething=None):
        self.tags = None
        delete(filething)


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Remove tags from a file.

    Args:
        filething (filething)
    Raises:
        mutagen.MutagenError
    """

    dsf_file = DSFFile(filething.fileobj)

    if dsf_file.dsd_chunk.offset_metdata_chunk != 0:
        id3_location = dsf_file.dsd_chunk.offset_metdata_chunk
        dsf_file.dsd_chunk.offset_metdata_chunk = 0
        dsf_file.dsd_chunk.write()

        filething.fileobj.seek(id3_location)
        filething.fileobj.truncate()


Open = DSF
