# Copyright (C) 2006  Lukas Lalinsky
# Copyright (C) 2012  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Musepack audio streams with APEv2 tags.

Musepack is an audio format originally based on the MPEG-1 Layer-2
algorithms. Stream versions 4 through 7 are supported.

For more information, see http://www.musepack.net/.
"""

__all__ = ["Musepack", "Open", "delete"]

import struct

from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, error, delete
from mutagen.id3._util import BitPaddedInt
from mutagen._util import cdata, convert_error, intround, endswith


class MusepackHeaderError(error):
    pass


RATES = [44100, 48000, 37800, 32000]


def _parse_sv8_int(fileobj, limit=9):
    """Reads (max limit) bytes from fileobj until the MSB is zero.
    All 7 LSB will be merged to a big endian uint.

    Raises ValueError in case not MSB is zero, or EOFError in
    case the file ended before limit is reached.

    Returns (parsed number, number of bytes read)
    """

    num = 0
    for i in range(limit):
        c = fileobj.read(1)
        if len(c) != 1:
            raise EOFError
        c = bytearray(c)
        num = (num << 7) | (c[0] & 0x7F)
        if not c[0] & 0x80:
            return num, i + 1
    if limit > 0:
        raise ValueError
    return 0, 0


def _calc_sv8_gain(gain):
    # 64.82 taken from mpcdec
    return 64.82 - gain / 256.0


def _calc_sv8_peak(peak):
    return (10 ** (peak / (256.0 * 20.0)) / 65535.0)


class MusepackInfo(StreamInfo):
    """MusepackInfo()

    Musepack stream information.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bitrate (`int`): audio bitrate, in bits per second
        version (`int`) Musepack stream version

    Optional Attributes:

    Attributes:
        title_gain (`float`): Replay Gain for this song
        title_peak (`float`): Peak data for this song
        album_gain (`float`): Replay Gain for this album
        album_peak (`float`): Peak data for this album

    These attributes are only available in stream version 7/8. The
    gains are a float, +/- some dB. The peaks are a percentage [0..1] of
    the maximum amplitude. This means to get a number comparable to
    VorbisGain, you must multiply the peak by 2.
    """

    @convert_error(IOError, MusepackHeaderError)
    def __init__(self, fileobj):
        """Raises MusepackHeaderError"""

        header = fileobj.read(4)
        if len(header) != 4:
            raise MusepackHeaderError("not a Musepack file")

        # Skip ID3v2 tags
        if header[:3] == b"ID3":
            header = fileobj.read(6)
            if len(header) != 6:
                raise MusepackHeaderError("not a Musepack file")
            size = 10 + BitPaddedInt(header[2:6])
            fileobj.seek(size)
            header = fileobj.read(4)
            if len(header) != 4:
                raise MusepackHeaderError("not a Musepack file")

        if header.startswith(b"MPCK"):
            self.__parse_sv8(fileobj)
        else:
            self.__parse_sv467(fileobj)

        if not self.bitrate and self.length != 0:
            fileobj.seek(0, 2)
            self.bitrate = intround(fileobj.tell() * 8 / self.length)

    def __parse_sv8(self, fileobj):
        # SV8 http://trac.musepack.net/trac/wiki/SV8Specification

        key_size = 2
        mandatory_packets = [b"SH", b"RG"]

        def check_frame_key(key):
            if ((len(frame_type) != key_size) or
                    (not b'AA' <= frame_type <= b'ZZ')):
                raise MusepackHeaderError("Invalid frame key.")

        frame_type = fileobj.read(key_size)
        check_frame_key(frame_type)

        while frame_type not in (b"AP", b"SE") and mandatory_packets:
            try:
                frame_size, slen = _parse_sv8_int(fileobj)
            except (EOFError, ValueError):
                raise MusepackHeaderError("Invalid packet size.")
            data_size = frame_size - key_size - slen
            # packets can be at maximum data_size big and are padded with zeros

            if frame_type == b"SH":
                if frame_type not in mandatory_packets:
                    raise MusepackHeaderError("Duplicate SH packet")
                mandatory_packets.remove(frame_type)
                self.__parse_stream_header(fileobj, data_size)
            elif frame_type == b"RG":
                if frame_type not in mandatory_packets:
                    raise MusepackHeaderError("Duplicate RG packet")
                mandatory_packets.remove(frame_type)
                self.__parse_replaygain_packet(fileobj, data_size)
            else:
                fileobj.seek(data_size, 1)

            frame_type = fileobj.read(key_size)
            check_frame_key(frame_type)

        if mandatory_packets:
            raise MusepackHeaderError("Missing mandatory packets: %s." %
                                      ", ".join(map(repr, mandatory_packets)))

        self.length = float(self.samples) / self.sample_rate
        self.bitrate = 0

    def __parse_stream_header(self, fileobj, data_size):
        # skip CRC
        fileobj.seek(4, 1)
        remaining_size = data_size - 4

        try:
            self.version = bytearray(fileobj.read(1))[0]
        except (TypeError, IndexError):
            raise MusepackHeaderError("SH packet ended unexpectedly.")

        remaining_size -= 1

        try:
            samples, l1 = _parse_sv8_int(fileobj)
            samples_skip, l2 = _parse_sv8_int(fileobj)
        except (EOFError, ValueError):
            raise MusepackHeaderError(
                "SH packet: Invalid sample counts.")

        self.samples = samples - samples_skip
        remaining_size -= l1 + l2

        data = fileobj.read(remaining_size)
        if len(data) != remaining_size or len(data) < 2:
            raise MusepackHeaderError("SH packet ended unexpectedly.")
        rate_index = (bytearray(data)[0] >> 5)
        try:
            self.sample_rate = RATES[rate_index]
        except IndexError:
            raise MusepackHeaderError("Invalid sample rate")
        self.channels = (bytearray(data)[1] >> 4) + 1

    def __parse_replaygain_packet(self, fileobj, data_size):
        data = fileobj.read(data_size)
        if data_size < 9:
            raise MusepackHeaderError("Invalid RG packet size.")
        if len(data) != data_size:
            raise MusepackHeaderError("RG packet ended unexpectedly.")
        title_gain = cdata.short_be(data[1:3])
        title_peak = cdata.short_be(data[3:5])
        album_gain = cdata.short_be(data[5:7])
        album_peak = cdata.short_be(data[7:9])
        if title_gain:
            self.title_gain = _calc_sv8_gain(title_gain)
        if title_peak:
            self.title_peak = _calc_sv8_peak(title_peak)
        if album_gain:
            self.album_gain = _calc_sv8_gain(album_gain)
        if album_peak:
            self.album_peak = _calc_sv8_peak(album_peak)

    def __parse_sv467(self, fileobj):
        fileobj.seek(-4, 1)
        header = fileobj.read(32)
        if len(header) != 32:
            raise MusepackHeaderError("not a Musepack file")

        # SV7
        if header.startswith(b"MP+"):
            self.version = bytearray(header)[3] & 0xF
            if self.version < 7:
                raise MusepackHeaderError("not a Musepack file")
            frames = cdata.uint_le(header[4:8])
            flags = cdata.uint_le(header[8:12])

            self.title_peak, self.title_gain = struct.unpack(
                "<Hh", header[12:16])
            self.album_peak, self.album_gain = struct.unpack(
                "<Hh", header[16:20])
            self.title_gain /= 100.0
            self.album_gain /= 100.0
            self.title_peak /= 65535.0
            self.album_peak /= 65535.0

            self.sample_rate = RATES[(flags >> 16) & 0x0003]
            self.bitrate = 0
        # SV4-SV6
        else:
            header_dword = cdata.uint_le(header[0:4])
            self.version = (header_dword >> 11) & 0x03FF
            if self.version < 4 or self.version > 6:
                raise MusepackHeaderError("not a Musepack file")
            self.bitrate = (header_dword >> 23) & 0x01FF
            self.sample_rate = 44100
            if self.version >= 5:
                frames = cdata.uint_le(header[4:8])
            else:
                frames = cdata.ushort_le(header[6:8])
            if self.version < 6:
                frames -= 1
        self.channels = 2
        self.length = float(frames * 1152 - 576) / self.sample_rate

    def pprint(self):
        rg_data = []
        if hasattr(self, "title_gain"):
            rg_data.append(u"%+0.2f (title)" % self.title_gain)
        if hasattr(self, "album_gain"):
            rg_data.append(u"%+0.2f (album)" % self.album_gain)
        rg_data = (rg_data and ", Gain: " + ", ".join(rg_data)) or ""

        return u"Musepack SV%d, %.2f seconds, %d Hz, %d bps%s" % (
            self.version, self.length, self.sample_rate, self.bitrate, rg_data)


class Musepack(APEv2File):
    """Musepack(filething)

    Arguments:
        filething (filething)

    Attributes:
        info (`MusepackInfo`)
    """

    _Info = MusepackInfo
    _mimes = ["audio/x-musepack", "audio/x-mpc"]

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"MP+") + header.startswith(b"MPCK") +
                endswith(filename, b".mpc"))


Open = Musepack
