# Copyright (C) 2008  Lukáš Lalinský
# Copyright (C) 2019  Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Tom's lossless Audio Kompressor (TAK) streams with APEv2 tags.

TAK is a lossless audio compressor developed by Thomas Becker.

For more information, see:

* http://www.thbeck.de/Tak/Tak.html
* http://wiki.hydrogenaudio.org/index.php?title=TAK
"""

__all__ = ["TAK", "Open", "delete"]

import struct

from mutagen import StreamInfo
from mutagen.apev2 import (
    APEv2File,
    delete,
    error,
)
from mutagen._util import (
    BitReader,
    BitReaderError,
    convert_error,
    enum,
    endswith,
)


@enum
class TAKMetadata(object):
    END = 0
    STREAM_INFO = 1
    SEEK_TABLE = 2  # Removed in TAK 1.1.1
    SIMPLE_WAVE_DATA = 3
    ENCODER_INFO = 4
    UNUSED_SPACE = 5  # New in TAK 1.0.3
    MD5 = 6  # New in TAK 1.1.1
    LAST_FRAME_INFO = 7  # New in TAK 1.1.1


CRC_SIZE = 3

ENCODER_INFO_CODEC_BITS = 6
ENCODER_INFO_PROFILE_BITS = 4
ENCODER_INFO_TOTAL_BITS = ENCODER_INFO_CODEC_BITS + ENCODER_INFO_PROFILE_BITS

SIZE_INFO_FRAME_DURATION_BITS = 4
SIZE_INFO_SAMPLE_NUM_BITS = 35
SIZE_INFO_TOTAL_BITS = (SIZE_INFO_FRAME_DURATION_BITS
                        + SIZE_INFO_SAMPLE_NUM_BITS)

AUDIO_FORMAT_DATA_TYPE_BITS = 3
AUDIO_FORMAT_SAMPLE_RATE_BITS = 18
AUDIO_FORMAT_SAMPLE_BITS_BITS = 5
AUDIO_FORMAT_CHANNEL_NUM_BITS = 4
AUDIO_FORMAT_HAS_EXTENSION_BITS = 1
AUDIO_FORMAT_BITS_MIN = 31
AUDIO_FORMAT_BITS_MAX = 31 + 102

SAMPLE_RATE_MIN = 6000
SAMPLE_BITS_MIN = 8
CHANNEL_NUM_MIN = 1

STREAM_INFO_BITS_MIN = (ENCODER_INFO_TOTAL_BITS
                        + SIZE_INFO_TOTAL_BITS
                        + AUDIO_FORMAT_BITS_MIN)
STREAM_INFO_BITS_MAX = (ENCODER_INFO_TOTAL_BITS
                        + SIZE_INFO_TOTAL_BITS
                        + AUDIO_FORMAT_BITS_MAX)
STREAM_INFO_SIZE_MIN = (STREAM_INFO_BITS_MIN + 7) / 8
STREAM_INFO_SIZE_MAX = (STREAM_INFO_BITS_MAX + 7) / 8


class _LSBBitReader(BitReader):
    """BitReader implementation which reads bits starting at LSB in each byte.
    """

    def _lsb(self, count):
        value = self._buffer & 0xff >> (8 - count)
        self._buffer = self._buffer >> count
        self._bits -= count
        return value

    def bits(self, count):
        """Reads `count` bits and returns an uint, LSB read first.

        May raise BitReaderError if not enough data could be read or
        IOError by the underlying file object.
        """
        if count < 0:
            raise ValueError

        value = 0
        if count <= self._bits:
            value = self._lsb(count)
        else:
            # First read all available bits
            shift = 0
            remaining = count
            if self._bits > 0:
                remaining -= self._bits
                shift = self._bits
                value = self._lsb(self._bits)
                assert self._bits == 0

            # Now add additional bytes
            n_bytes = (remaining - self._bits + 7) // 8
            data = self._fileobj.read(n_bytes)
            if len(data) != n_bytes:
                raise BitReaderError("not enough data")
            for b in bytearray(data):
                if remaining > 8:  # Use full byte
                    remaining -= 8
                    value = (b << shift) | value
                    shift += 8
                else:
                    self._buffer = b
                    self._bits = 8
                    b = self._lsb(remaining)
                    value = (b << shift) | value

        assert 0 <= self._bits < 8
        return value


class TAKHeaderError(error):
    pass


class TAKInfo(StreamInfo):

    """TAK stream information.

    Attributes:
      channels (`int`): number of audio channels
      length (`float`): file length in seconds, as a float
      sample_rate (`int`): audio sampling rate in Hz
      bits_per_sample (`int`): audio sample size
      encoder_info (`mutagen.text`): encoder version
    """

    channels = 0
    length = 0
    sample_rate = 0
    bitrate = 0
    encoder_info = ""

    @convert_error(IOError, TAKHeaderError)
    @convert_error(BitReaderError, TAKHeaderError)
    def __init__(self, fileobj):
        stream_id = fileobj.read(4)
        if len(stream_id) != 4 or not stream_id == b"tBaK":
            raise TAKHeaderError("not a TAK file")

        bitreader = _LSBBitReader(fileobj)
        found_stream_info = False
        while True:
            type = TAKMetadata(bitreader.bits(7))
            bitreader.skip(1)  # Unused
            size = struct.unpack("<I", bitreader.bytes(3) + b'\0')[0]
            data_size = size - CRC_SIZE
            pos = fileobj.tell()

            if type == TAKMetadata.END:
                break
            elif type == TAKMetadata.STREAM_INFO:
                self._parse_stream_info(bitreader, size)
                found_stream_info = True
            elif type == TAKMetadata.ENCODER_INFO:
                self._parse_encoder_info(bitreader, data_size)

            assert bitreader.is_aligned()
            fileobj.seek(pos + size)

        if not found_stream_info:
            raise TAKHeaderError("missing stream info")

        if self.sample_rate > 0:
            self.length = self.number_of_samples / float(self.sample_rate)

    def _parse_stream_info(self, bitreader, size):
        if size < STREAM_INFO_SIZE_MIN or size > STREAM_INFO_SIZE_MAX:
            raise TAKHeaderError("stream info has invalid length")

        # Encoder Info
        bitreader.skip(ENCODER_INFO_CODEC_BITS)
        bitreader.skip(ENCODER_INFO_PROFILE_BITS)

        # Size Info
        bitreader.skip(SIZE_INFO_FRAME_DURATION_BITS)
        self.number_of_samples = bitreader.bits(SIZE_INFO_SAMPLE_NUM_BITS)

        # Audio Format
        bitreader.skip(AUDIO_FORMAT_DATA_TYPE_BITS)
        self.sample_rate = (bitreader.bits(AUDIO_FORMAT_SAMPLE_RATE_BITS)
                            + SAMPLE_RATE_MIN)
        self.bits_per_sample = (bitreader.bits(AUDIO_FORMAT_SAMPLE_BITS_BITS)
                                + SAMPLE_BITS_MIN)
        self.channels = (bitreader.bits(AUDIO_FORMAT_CHANNEL_NUM_BITS)
                         + CHANNEL_NUM_MIN)
        bitreader.skip(AUDIO_FORMAT_HAS_EXTENSION_BITS)

    def _parse_encoder_info(self, bitreader, size):
        patch = bitreader.bits(8)
        minor = bitreader.bits(8)
        major = bitreader.bits(8)
        self.encoder_info = "TAK %d.%d.%d" % (major, minor, patch)

    def pprint(self):
        return u"%s, %d Hz, %d bits, %.2f seconds, %d channel(s)" % (
            self.encoder_info or "TAK", self.sample_rate, self.bits_per_sample,
            self.length, self.channels)


class TAK(APEv2File):
    """TAK(filething)

    Arguments:
        filething (filething)

    Attributes:
        info (`TAKInfo`)
    """

    _Info = TAKInfo
    _mimes = ["audio/x-tak"]

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"tBaK") + endswith(filename.lower(), ".tak")


Open = TAK
