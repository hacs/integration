# Copyright (C) 2019 Philipp Wolfer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


"""Pure AC3 file information.
"""

__all__ = ["AC3", "Open"]

from mutagen import StreamInfo
from mutagen._file import FileType
from mutagen._util import (
    BitReader,
    BitReaderError,
    MutagenError,
    convert_error,
    enum,
    loadfile,
    endswith,
)


@enum
class ChannelMode(object):
    DUALMONO = 0
    MONO = 1
    STEREO = 2
    C3F = 3
    C2F1R = 4
    C3F1R = 5
    C2F2R = 6
    C3F2R = 7


AC3_CHANNELS = {
    ChannelMode.DUALMONO: 2,
    ChannelMode.MONO: 1,
    ChannelMode.STEREO: 2,
    ChannelMode.C3F: 3,
    ChannelMode.C2F1R: 3,
    ChannelMode.C3F1R: 4,
    ChannelMode.C2F2R: 4,
    ChannelMode.C3F2R: 5
}

AC3_HEADER_SIZE = 7

AC3_SAMPLE_RATES = [48000, 44100, 32000]

AC3_BITRATES = [
    32, 40, 48, 56, 64, 80, 96, 112, 128,
    160, 192, 224, 256, 320, 384, 448, 512, 576, 640
]


@enum
class EAC3FrameType(object):
    INDEPENDENT = 0
    DEPENDENT = 1
    AC3_CONVERT = 2
    RESERVED = 3


EAC3_BLOCKS = [1, 2, 3, 6]


class AC3Error(MutagenError):
    pass


class AC3Info(StreamInfo):

    """AC3 stream information.
    The length of the stream is just a guess and might not be correct.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bitrate (`int`): audio bitrate, in bits per second
        codec (`str`): ac-3 or ec-3 (Enhanced AC-3)
    """

    channels = 0
    length = 0
    sample_rate = 0
    bitrate = 0
    codec = 'ac-3'

    @convert_error(IOError, AC3Error)
    def __init__(self, fileobj):
        """Raises AC3Error"""
        header = bytearray(fileobj.read(6))

        if len(header) < 6:
            raise AC3Error("not enough data")

        if not header.startswith(b"\x0b\x77"):
            raise AC3Error("not a AC3 file")

        bitstream_id = header[5] >> 3
        if bitstream_id > 16:
            raise AC3Error("invalid bitstream_id %i" % bitstream_id)

        fileobj.seek(2)
        self._read_header(fileobj, bitstream_id)

    def _read_header(self, fileobj, bitstream_id):
        bitreader = BitReader(fileobj)
        try:
            # This is partially based on code from
            # https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/ac3_parser.c
            if bitstream_id <= 10:  # Normal AC-3
                self._read_header_normal(bitreader, bitstream_id)
            else:  # Enhanced AC-3
                self._read_header_enhanced(bitreader)
        except BitReaderError as e:
            raise AC3Error(e)

        self.length = self._guess_length(fileobj)

    def _read_header_normal(self, bitreader, bitstream_id):
        r = bitreader
        r.skip(16)  # 16 bit CRC
        sr_code = r.bits(2)
        if sr_code == 3:
            raise AC3Error("invalid sample rate code %i" % sr_code)

        frame_size_code = r.bits(6)
        if frame_size_code > 37:
            raise AC3Error("invalid frame size code %i" % frame_size_code)

        r.skip(5)  # bitstream ID, already read
        r.skip(3)  # bitstream mode, not needed
        channel_mode = ChannelMode(r.bits(3))
        r.skip(2)  # dolby surround mode or surround mix level
        lfe_on = r.bits(1)

        sr_shift = max(bitstream_id, 8) - 8
        try:
            self.sample_rate = AC3_SAMPLE_RATES[sr_code] >> sr_shift
            self.bitrate = (AC3_BITRATES[frame_size_code >> 1] * 1000
                            ) >> sr_shift
        except KeyError as e:
            raise AC3Error(e)
        self.channels = self._get_channels(channel_mode, lfe_on)
        self._skip_unused_header_bits_normal(r, channel_mode)

    def _read_header_enhanced(self, bitreader):
        r = bitreader
        self.codec = "ec-3"
        frame_type = r.bits(2)
        if frame_type == EAC3FrameType.RESERVED:
            raise AC3Error("invalid frame type %i" % frame_type)

        r.skip(3)  # substream ID, not needed

        frame_size = (r.bits(11) + 1) << 1
        if frame_size < AC3_HEADER_SIZE:
            raise AC3Error("invalid frame size %i" % frame_size)

        sr_code = r.bits(2)
        try:
            if sr_code == 3:
                sr_code2 = r.bits(2)
                if sr_code2 == 3:
                    raise AC3Error("invalid sample rate code %i" % sr_code2)

                numblocks_code = 3
                self.sample_rate = AC3_SAMPLE_RATES[sr_code2] // 2
            else:
                numblocks_code = r.bits(2)
                self.sample_rate = AC3_SAMPLE_RATES[sr_code]

            channel_mode = ChannelMode(r.bits(3))
            lfe_on = r.bits(1)
            self.bitrate = 8 * frame_size * self.sample_rate // (
                EAC3_BLOCKS[numblocks_code] * 256)
        except KeyError as e:
            raise AC3Error(e)
        r.skip(5)  # bitstream ID, already read
        self.channels = self._get_channels(channel_mode, lfe_on)
        self._skip_unused_header_bits_enhanced(
            r, frame_type, channel_mode, sr_code, numblocks_code)

    @staticmethod
    def _skip_unused_header_bits_normal(bitreader, channel_mode):
        r = bitreader
        r.skip(5)  # Dialogue Normalization
        if r.bits(1):  # Compression Gain Word Exists
            r.skip(8)  # Compression Gain Word
        if r.bits(1):  # Language Code Exists
            r.skip(8)  # Language Code
        if r.bits(1):  # Audio Production Information Exists
            # Mixing Level, 5 Bits
            # Room Type, 2 Bits
            r.skip(7)
        if channel_mode == ChannelMode.DUALMONO:
            r.skip(5)  # Dialogue Normalization, ch2
            if r.bits(1):  # Compression Gain Word Exists, ch2
                r.skip(8)  # Compression Gain Word, ch2
            if r.bits(1):  # Language Code Exists, ch2
                r.skip(8)  # Language Code, ch2
            if r.bits(1):  # Audio Production Information Exists, ch2
                # Mixing Level, ch2, 5 Bits
                # Room Type, ch2, 2 Bits
                r.skip(7)
        # Copyright Bit, 1 Bit
        # Original Bit Stream, 1 Bit
        r.skip(2)
        timecod1e = r.bits(1)  # Time Code First Halve Exists
        timecod2e = r.bits(1)  # Time Code Second Halve Exists
        if timecod1e:
            r.skip(14)  # Time Code First Half
        if timecod2e:
            r.skip(14)  # Time Code Second Half
        if r.bits(1):  # Additional Bit Stream Information Exists
            addbsil = r.bits(6)  # Additional Bit Stream Information Length
            r.skip((addbsil + 1) * 8)

    @staticmethod
    def _skip_unused_header_bits_enhanced(bitreader, frame_type, channel_mode,
                                          sr_code, numblocks_code):
        r = bitreader
        r.skip(5)  # Dialogue Normalization
        if r.bits(1):  # Compression Gain Word Exists
            r.skip(8)  # Compression Gain Word
        if channel_mode == ChannelMode.DUALMONO:
            r.skip(5)  # Dialogue Normalization, ch2
            if r.bits(1):  # Compression Gain Word Exists, ch2
                r.skip(8)  # Compression Gain Word, ch2
        if frame_type == EAC3FrameType.DEPENDENT:
            if r.bits(1):  # chanmap exists
                r.skip(16)  # chanmap
        if r.bits(1):  # mixmdate, 1 Bit
            # FIXME: Handle channel dependent fields
            return
        if r.bits(1):  # Informational Metadata Exists
            # bsmod, 3 Bits
            # Copyright Bit, 1 Bit
            # Original Bit Stream, 1 Bit
            r.skip(5)
            if channel_mode == ChannelMode.STEREO:
                # dsurmod. 2 Bits
                # dheadphonmod, 2 Bits
                r.skip(4)
            elif channel_mode >= ChannelMode.C2F2R:
                r.skip(2)  # dsurexmod
            if r.bits(1):  # Audio Production Information Exists
                # Mixing Level, 5 Bits
                # Room Type, 2 Bits
                # adconvtyp, 1 Bit
                r.skip(8)
            if channel_mode == ChannelMode.DUALMONO:
                if r.bits(1):  # Audio Production Information Exists, ch2
                    # Mixing Level, ch2, 5 Bits
                    # Room Type, ch2, 2 Bits
                    # adconvtyp, ch2, 1 Bit
                    r.skip(8)
            if sr_code < 3:  # if not half sample rate
                r.skip(1)  # sourcefscod
        if frame_type == EAC3FrameType.INDEPENDENT and numblocks_code == 3:
            r.skip(1)  # convsync
        if frame_type == EAC3FrameType.AC3_CONVERT:
            if numblocks_code != 3:
                if r.bits(1):  # blkid
                    r.skip(6)  # frmsizecod
        if r.bits(1):  # Additional Bit Stream Information Exists
            addbsil = r.bits(6)  # Additional Bit Stream Information Length
            r.skip((addbsil + 1) * 8)

    @staticmethod
    def _get_channels(channel_mode, lfe_on):
        try:
            return AC3_CHANNELS[channel_mode] + lfe_on
        except KeyError as e:
            raise AC3Error(e)

    def _guess_length(self, fileobj):
        # use bitrate + data size to guess length
        if self.bitrate == 0:
            return
        start = fileobj.tell()
        fileobj.seek(0, 2)
        length = fileobj.tell() - start
        return 8.0 * length / self.bitrate

    def pprint(self):
        return u"%s, %d Hz, %.2f seconds, %d channel(s), %d bps" % (
            self.codec, self.sample_rate, self.length, self.channels,
            self.bitrate)


class AC3(FileType):
    """AC3(filething)

    Arguments:
        filething (filething)

    Load AC3 or EAC3 files.

    Tagging is not supported.
    Use the ID3/APEv2 classes directly instead.

    Attributes:
        info (`AC3Info`)
    """

    _mimes = ["audio/ac3"]

    @loadfile()
    def load(self, filething):
        self.info = AC3Info(filething.fileobj)

    def add_tags(self):
        raise AC3Error("doesn't support tags")

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"\x0b\x77") * 2 \
            + (endswith(filename, ".ac3") or endswith(filename, ".eac3"))


Open = AC3
error = AC3Error
