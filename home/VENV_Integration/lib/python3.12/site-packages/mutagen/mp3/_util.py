# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
http://www.codeproject.com/Articles/8295/MPEG-Audio-Frame-Header
http://wiki.hydrogenaud.io/index.php?title=MP3
"""

from __future__ import division
from functools import partial
from io import BytesIO
from typing import List

from mutagen._util import cdata, BitReader, iterbytes


class LAMEError(Exception):
    pass


class LAMEHeader(object):
    """http://gabriel.mp3-tech.org/mp3infotag.html"""

    vbr_method = 0
    """0: unknown, 1: CBR, 2: ABR, 3/4/5: VBR, others: see the docs"""

    lowpass_filter = 0
    """lowpass filter value in Hz. 0 means unknown"""

    quality = -1
    """Encoding quality: 0..9"""

    vbr_quality = -1
    """VBR quality: 0..9"""

    track_peak = None
    """Peak signal amplitude as float. 1.0 is maximal signal amplitude
    in decoded format. None if unknown.
    """

    track_gain_origin = 0
    """see the docs"""

    track_gain_adjustment = None
    """Track gain adjustment as float (for 89db replay gain) or None"""

    album_gain_origin = 0
    """see the docs"""

    album_gain_adjustment = None
    """Album gain adjustment as float (for 89db replay gain) or None"""

    encoding_flags = 0
    """see docs"""

    ath_type = -1
    """see docs"""

    bitrate = -1
    """Bitrate in kbps. For VBR the minimum bitrate, for anything else
    (CBR, ABR, ..) the target bitrate.
    """

    encoder_delay_start = 0
    """Encoder delay in samples"""

    encoder_padding_end = 0
    """Padding in samples added at the end"""

    source_sample_frequency_enum = -1
    """see docs"""

    unwise_setting_used = False
    """see docs"""

    stereo_mode = 0
    """see docs"""

    noise_shaping = 0
    """see docs"""

    mp3_gain = 0
    """Applied MP3 gain -127..127. Factor is 2 ** (mp3_gain / 4)"""

    surround_info = 0
    """see docs"""

    preset_used = 0
    """lame preset"""

    music_length = 0
    """Length in bytes excluding any ID3 tags"""

    music_crc = -1
    """CRC16 of the data specified by music_length"""

    header_crc = -1
    """CRC16 of this header and everything before (not checked)"""

    def __init__(self, xing, fileobj):
        """Raises LAMEError if parsing fails"""

        payload = fileobj.read(27)
        if len(payload) != 27:
            raise LAMEError("Not enough data")

        # extended lame header
        r = BitReader(BytesIO(payload))
        revision = r.bits(4)
        if revision != 0:
            raise LAMEError("unsupported header revision %d" % revision)

        self.vbr_method = r.bits(4)
        self.lowpass_filter = r.bits(8) * 100

        # these have a different meaning for lame; expose them again here
        self.quality = (100 - xing.vbr_scale) % 10
        self.vbr_quality = (100 - xing.vbr_scale) // 10

        track_peak_data = r.bytes(4)
        if track_peak_data == b"\x00\x00\x00\x00":
            self.track_peak = None
        else:
            # see PutLameVBR() in LAME's VbrTag.c
            self.track_peak = cdata.uint32_be(track_peak_data) / 2 ** 23
        track_gain_type = r.bits(3)
        self.track_gain_origin = r.bits(3)
        sign = r.bits(1)
        gain_adj = r.bits(9) / 10.0
        if sign:
            gain_adj *= -1
        if track_gain_type == 1:
            self.track_gain_adjustment = gain_adj
        else:
            self.track_gain_adjustment = None
        assert r.is_aligned()

        album_gain_type = r.bits(3)
        self.album_gain_origin = r.bits(3)
        sign = r.bits(1)
        album_gain_adj = r.bits(9) / 10.0
        if album_gain_type == 2:
            self.album_gain_adjustment = album_gain_adj
        else:
            self.album_gain_adjustment = None

        self.encoding_flags = r.bits(4)
        self.ath_type = r.bits(4)

        self.bitrate = r.bits(8)

        self.encoder_delay_start = r.bits(12)
        self.encoder_padding_end = r.bits(12)

        self.source_sample_frequency_enum = r.bits(2)
        self.unwise_setting_used = r.bits(1)
        self.stereo_mode = r.bits(3)
        self.noise_shaping = r.bits(2)

        sign = r.bits(1)
        mp3_gain = r.bits(7)
        if sign:
            mp3_gain *= -1
        self.mp3_gain = mp3_gain

        r.skip(2)
        self.surround_info = r.bits(3)
        self.preset_used = r.bits(11)
        self.music_length = r.bits(32)
        self.music_crc = r.bits(16)

        self.header_crc = r.bits(16)
        assert r.is_aligned()

    def guess_settings(self, major, minor):
        """Gives a guess about the encoder settings used. Returns an empty
        string if unknown.

        The guess is mostly correct in case the file was encoded with
        the default options (-V --preset --alt-preset --abr -b etc) and no
        other fancy options.

        Args:
            major (int)
            minor (int)
        Returns:
            text
        """

        version = major, minor

        if self.vbr_method == 2:
            if version in ((3, 90), (3, 91), (3, 92)) and self.encoding_flags:
                if self.bitrate < 255:
                    return u"--alt-preset %d" % self.bitrate
                else:
                    return u"--alt-preset %d+" % self.bitrate
            if self.preset_used != 0:
                return u"--preset %d" % self.preset_used
            elif self.bitrate < 255:
                return u"--abr %d" % self.bitrate
            else:
                return u"--abr %d+" % self.bitrate
        elif self.vbr_method == 1:
            if self.preset_used == 0:
                if self.bitrate < 255:
                    return u"-b %d" % self.bitrate
                else:
                    return u"-b 255+"
            elif self.preset_used == 1003:
                return u"--preset insane"
            return u"-b %d" % self.preset_used
        elif version in ((3, 90), (3, 91), (3, 92)):
            preset_key = (self.vbr_quality, self.quality, self.vbr_method,
                          self.lowpass_filter, self.ath_type)
            if preset_key == (1, 2, 4, 19500, 3):
                return u"--preset r3mix"
            if preset_key == (2, 2, 3, 19000, 4):
                return u"--alt-preset standard"
            if preset_key == (2, 2, 3, 19500, 2):
                return u"--alt-preset extreme"

            if self.vbr_method == 3:
                return u"-V %s" % self.vbr_quality
            elif self.vbr_method in (4, 5):
                return u"-V %s --vbr-new" % self.vbr_quality
        elif version in ((3, 93), (3, 94), (3, 95), (3, 96), (3, 97)):
            if self.preset_used == 1001:
                return u"--preset standard"
            elif self.preset_used == 1002:
                return u"--preset extreme"
            elif self.preset_used == 1004:
                return u"--preset fast standard"
            elif self.preset_used == 1005:
                return u"--preset fast extreme"
            elif self.preset_used == 1006:
                return u"--preset medium"
            elif self.preset_used == 1007:
                return u"--preset fast medium"

            if self.vbr_method == 3:
                return u"-V %s" % self.vbr_quality
            elif self.vbr_method in (4, 5):
                return u"-V %s --vbr-new" % self.vbr_quality
        elif version == (3, 98):
            if self.vbr_method == 3:
                return u"-V %s --vbr-old" % self.vbr_quality
            elif self.vbr_method in (4, 5):
                return u"-V %s" % self.vbr_quality
        elif version >= (3, 99):
            if self.vbr_method == 3:
                return u"-V %s --vbr-old" % self.vbr_quality
            elif self.vbr_method in (4, 5):
                p = self.vbr_quality
                adjust_key = (p, self.bitrate, self.lowpass_filter)
                # https://sourceforge.net/p/lame/bugs/455/
                p = {
                    (5, 32, 0): 7,
                    (5, 8, 0): 8,
                    (6, 8, 0): 9,
                }.get(adjust_key, p)
                return u"-V %s" % p

        return u""

    @classmethod
    def parse_version(cls, fileobj):
        """Returns a version string and True if a LAMEHeader follows.
        The passed file object will be positioned right before the
        lame header if True.

        Raises LAMEError if there is no lame version info.
        """

        # http://wiki.hydrogenaud.io/index.php?title=LAME_version_string

        data = fileobj.read(20)
        if len(data) != 20:
            raise LAMEError("Not a lame header")
        if not data.startswith((b"LAME", b"L3.99")):
            raise LAMEError("Not a lame header")

        data = data.lstrip(b"EMAL")
        major, data = data[0:1], data[1:].lstrip(b".")
        minor = b""
        for c in iterbytes(data):
            if not c.isdigit():
                break
            minor += c
        data = data[len(minor):]

        try:
            major = int(major.decode("ascii"))
            minor = int(minor.decode("ascii"))
        except ValueError:
            raise LAMEError

        # the extended header was added sometimes in the 3.90 cycle
        # e.g. "LAME3.90 (alpha)" should still stop here.
        # (I have seen such a file)
        if (major, minor) < (3, 90) or (
                (major, minor) == (3, 90) and data[-11:-10] == b"("):
            flag = data.strip(b"\x00").rstrip().decode("ascii")
            return (major, minor), u"%d.%d%s" % (major, minor, flag), False

        if len(data) < 11:
            raise LAMEError("Invalid version: too long")

        flag = data[:-11].rstrip(b"\x00")

        flag_string = u""
        patch = u""
        if flag == b"a":
            flag_string = u" (alpha)"
        elif flag == b"b":
            flag_string = u" (beta)"
        elif flag == b"r":
            patch = u".1+"
        elif flag == b" ":
            if (major, minor) > (3, 96):
                patch = u".0"
            else:
                patch = u".0+"
        elif flag == b"" or flag == b".":
            patch = u".0+"
        else:
            flag_string = u" (?)"

        # extended header, seek back to 9 bytes for the caller
        fileobj.seek(-11, 1)

        return (major, minor), \
            u"%d.%d%s%s" % (major, minor, patch, flag_string), True


class XingHeaderError(Exception):
    pass


class XingHeaderFlags(object):
    FRAMES = 0x1
    BYTES = 0x2
    TOC = 0x4
    VBR_SCALE = 0x8


class XingHeader(object):

    frames = -1
    """Number of frames, -1 if unknown"""

    bytes = -1
    """Number of bytes, -1 if unknown"""

    toc: List[int] = []
    """List of 100 file offsets in percent encoded as 0-255. E.g. entry
    50 contains the file offset in percent at 50% play time.
    Empty if unknown.
    """

    vbr_scale = -1
    """VBR quality indicator 0-100. -1 if unknown"""

    lame_header = None
    """A LAMEHeader instance or None"""

    lame_version = (0, 0)
    """The LAME version as two element tuple (major, minor)"""

    lame_version_desc = u""
    """The version of the LAME encoder e.g. '3.99.0'. Empty if unknown"""

    is_info = False
    """If the header started with 'Info' and not 'Xing'"""

    def __init__(self, fileobj):
        """Parses the Xing header or raises XingHeaderError.

        The file position after this returns is undefined.
        """

        data = fileobj.read(8)
        if len(data) != 8 or data[:4] not in (b"Xing", b"Info"):
            raise XingHeaderError("Not a Xing header")

        self.is_info = (data[:4] == b"Info")

        flags = cdata.uint32_be_from(data, 4)[0]

        if flags & XingHeaderFlags.FRAMES:
            data = fileobj.read(4)
            if len(data) != 4:
                raise XingHeaderError("Xing header truncated")
            self.frames = cdata.uint32_be(data)

        if flags & XingHeaderFlags.BYTES:
            data = fileobj.read(4)
            if len(data) != 4:
                raise XingHeaderError("Xing header truncated")
            self.bytes = cdata.uint32_be(data)

        if flags & XingHeaderFlags.TOC:
            data = fileobj.read(100)
            if len(data) != 100:
                raise XingHeaderError("Xing header truncated")
            self.toc = list(bytearray(data))

        if flags & XingHeaderFlags.VBR_SCALE:
            data = fileobj.read(4)
            if len(data) != 4:
                raise XingHeaderError("Xing header truncated")
            self.vbr_scale = cdata.uint32_be(data)

        try:
            self.lame_version, self.lame_version_desc, has_header = \
                LAMEHeader.parse_version(fileobj)
            if has_header:
                self.lame_header = LAMEHeader(self, fileobj)
        except LAMEError:
            pass

    def get_encoder_settings(self):
        """Returns the guessed encoder settings"""

        if self.lame_header is None:
            return u""
        return self.lame_header.guess_settings(*self.lame_version)

    @classmethod
    def get_offset(cls, info):
        """Calculate the offset to the Xing header from the start of the
        MPEG header including sync based on the MPEG header's content.
        """

        assert info.layer == 3

        if info.version == 1:
            if info.mode != 3:
                return 36
            else:
                return 21
        else:
            if info.mode != 3:
                return 21
            else:
                return 13


class VBRIHeaderError(Exception):
    pass


class VBRIHeader(object):

    version = 0
    """VBRI header version"""

    quality = 0
    """Quality indicator"""

    bytes = 0
    """Number of bytes"""

    frames = 0
    """Number of frames"""

    toc_scale_factor = 0
    """Scale factor of TOC entries"""

    toc_frames = 0
    """Number of frames per table entry"""

    toc: List[int] = []
    """TOC"""

    def __init__(self, fileobj):
        """Reads the VBRI header or raises VBRIHeaderError.

        The file position is undefined after this returns
        """

        data = fileobj.read(26)
        if len(data) != 26 or not data.startswith(b"VBRI"):
            raise VBRIHeaderError("Not a VBRI header")

        offset = 4
        self.version, offset = cdata.uint16_be_from(data, offset)
        if self.version != 1:
            raise VBRIHeaderError(
                "Unsupported header version: %r" % self.version)

        offset += 2  # float16.. can't do
        self.quality, offset = cdata.uint16_be_from(data, offset)
        self.bytes, offset = cdata.uint32_be_from(data, offset)
        self.frames, offset = cdata.uint32_be_from(data, offset)

        toc_num_entries, offset = cdata.uint16_be_from(data, offset)
        self.toc_scale_factor, offset = cdata.uint16_be_from(data, offset)
        toc_entry_size, offset = cdata.uint16_be_from(data, offset)
        self.toc_frames, offset = cdata.uint16_be_from(data, offset)
        toc_size = toc_entry_size * toc_num_entries
        toc_data = fileobj.read(toc_size)
        if len(toc_data) != toc_size:
            raise VBRIHeaderError("VBRI header truncated")

        self.toc = []
        if toc_entry_size == 2:
            unpack = partial(cdata.uint16_be_from, toc_data)
        elif toc_entry_size == 4:
            unpack = partial(cdata.uint32_be_from, toc_data)
        else:
            raise VBRIHeaderError("Invalid TOC entry size")

        self.toc = [unpack(i)[0] for i in range(0, toc_size, toc_entry_size)]

    @classmethod
    def get_offset(cls, info):
        """Offset in bytes from the start of the MPEG header including sync"""

        assert info.layer == 3

        return 36
