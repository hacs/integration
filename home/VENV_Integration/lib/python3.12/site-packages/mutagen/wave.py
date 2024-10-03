# Copyright (C) 2017  Borewit
# Copyright (C) 2019-2020  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Microsoft WAVE/RIFF audio file/stream information and tags."""

import sys
import struct

from mutagen import StreamInfo, FileType

from mutagen.id3 import ID3
from mutagen._riff import RiffFile, InvalidChunk
from mutagen._iff import error as IffError
from mutagen.id3._util import ID3NoHeaderError, error as ID3Error
from mutagen._util import (
    convert_error,
    endswith,
    loadfile,
    reraise,
)

__all__ = ["WAVE", "Open", "delete"]


class error(IffError):
    """WAVE stream parsing errors."""


class _WaveFile(RiffFile):
    """Representation of a RIFF/WAVE file"""

    def __init__(self, fileobj):
        RiffFile.__init__(self, fileobj)

        if self.file_type != u'WAVE':
            raise error("Expected RIFF/WAVE.")

        # Normalize ID3v2-tag-chunk to lowercase
        if u'ID3' in self:
            self[u'ID3'].id = u'id3'


class WaveStreamInfo(StreamInfo):
    """WaveStreamInfo()

    Microsoft WAVE file information.

    Information is parsed from the 'fmt' & 'data'chunk of the RIFF/WAVE file

    Attributes:
        length (`float`): audio length, in seconds
        bitrate (`int`): audio bitrate, in bits per second
        channels (`int`): The number of audio channels
        sample_rate (`int`): audio sample rate, in Hz
        bits_per_sample (`int`): The audio sample size
    """

    length = 0.0
    bitrate = 0
    channels = 0
    sample_rate = 0
    bits_per_sample = 0

    SIZE = 16

    @convert_error(IOError, error)
    def __init__(self, fileobj):
        """Raises error"""

        wave_file = _WaveFile(fileobj)
        try:
            format_chunk = wave_file[u'fmt']
        except KeyError as e:
            raise error(str(e))

        data = format_chunk.read()
        if len(data) < 16:
            raise InvalidChunk()

        # RIFF: http://soundfile.sapp.org/doc/WaveFormat/
        #  Python struct.unpack:
        #    https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
        info = struct.unpack('<HHLLHH', data[:self.SIZE])
        self.audio_format, self.channels, self.sample_rate, byte_rate, \
            block_align, self.bits_per_sample = info
        self.bitrate = self.channels * self.bits_per_sample * self.sample_rate

        # Calculate duration
        self._number_of_samples = 0
        if block_align > 0:
            try:
                data_chunk = wave_file[u'data']
                self._number_of_samples = data_chunk.data_size / block_align
            except KeyError:
                pass

        if self.sample_rate > 0:
            self.length = self._number_of_samples / self.sample_rate

    def pprint(self):
        return u"%d channel RIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _WaveID3(ID3):
    """A Wave file with ID3v2 tags"""

    def _pre_load_header(self, fileobj):
        try:
            fileobj.seek(_WaveFile(fileobj)[u'id3'].data_offset)
        except (InvalidChunk, KeyError):
            raise ID3NoHeaderError("No ID3 chunk")

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething, v1=1, v2_version=4, v23_sep='/', padding=None):
        """Save ID3v2 data to the Wave/RIFF file"""

        fileobj = filething.fileobj
        wave_file = _WaveFile(fileobj)

        if u'id3' not in wave_file:
            wave_file.insert_chunk(u'id3')

        chunk = wave_file[u'id3']

        try:
            data = self._prepare_data(
                fileobj, chunk.data_offset, chunk.data_size, v2_version,
                v23_sep, padding)
        except ID3Error as e:
            reraise(error, e, sys.exc_info()[2])

        chunk.resize(len(data))
        chunk.write(data)

    def delete(self, filething):
        """Completely removes the ID3 chunk from the RIFF/WAVE file"""

        delete(filething)
        self.clear()


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Completely removes the ID3 chunk from the RIFF/WAVE file"""

    try:
        _WaveFile(filething.fileobj).delete_chunk(u'id3')
    except KeyError:
        pass


class WAVE(FileType):
    """WAVE(filething)

    A Waveform Audio File Format
    (WAVE, or more commonly known as WAV due to its filename extension)

    Arguments:
        filething (filething)

    Attributes:
        tags (`mutagen.id3.ID3`)
        info (`WaveStreamInfo`)
    """

    _mimes = ["audio/wav", "audio/wave"]

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"RIFF") + (header[8:12] == b'WAVE')
                + endswith(filename, b".wav") + endswith(filename, b".wave"))

    def add_tags(self):
        """Add an empty ID3 tag to the file."""
        if self.tags is None:
            self.tags = _WaveID3()
        else:
            raise error("an ID3 tag already exists")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething, **kwargs):
        """Load stream and tag information from a file."""

        fileobj = filething.fileobj
        self.info = WaveStreamInfo(fileobj)
        fileobj.seek(0, 0)

        try:
            self.tags = _WaveID3(fileobj, **kwargs)
        except ID3NoHeaderError:
            self.tags = None
        except ID3Error as e:
            raise error(e)
        else:
            self.tags.filename = self.filename


Open = WAVE
