# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""MPEG audio stream information and tags."""

import struct

from mutagen import StreamInfo
from mutagen._util import MutagenError, enum, BitReader, BitReaderError, \
    convert_error, intround, endswith
from mutagen.id3 import ID3FileType, delete
from mutagen.id3._util import BitPaddedInt

from ._util import XingHeader, XingHeaderError, VBRIHeader, VBRIHeaderError


__all__ = ["MP3", "Open", "delete", "MP3"]


class error(MutagenError):
    pass


class HeaderNotFoundError(error):
    pass


class InvalidMPEGHeader(error):
    pass


@enum
class BitrateMode(object):

    UNKNOWN = 0
    """Probably a CBR file, but not sure"""

    CBR = 1
    """Constant Bitrate"""

    VBR = 2
    """Variable Bitrate"""

    ABR = 3
    """Average Bitrate (a variant of VBR)"""


def _guess_xing_bitrate_mode(xing):

    if xing.lame_header:
        lame = xing.lame_header
        if lame.vbr_method in (1, 8):
            return BitrateMode.CBR
        elif lame.vbr_method in (2, 9):
            return BitrateMode.ABR
        elif lame.vbr_method in (3, 4, 5, 6):
            return BitrateMode.VBR
        # everything else undefined, continue guessing

    # info tags get only written by lame for cbr files
    if xing.is_info:
        return BitrateMode.CBR

    # older lame and non-lame with some variant of vbr
    if xing.vbr_scale != -1 or xing.lame_version_desc:
        return BitrateMode.VBR

    return BitrateMode.UNKNOWN


# Mode values.
STEREO, JOINTSTEREO, DUALCHANNEL, MONO = range(4)


class MPEGFrame(object):

    # Map (version, layer) tuples to bitrates.
    __BITRATE = {
        (1., 1): [0, 32, 64, 96, 128, 160, 192, 224,
                  256, 288, 320, 352, 384, 416, 448],
        (1., 2): [0, 32, 48, 56, 64, 80, 96, 112, 128,
                  160, 192, 224, 256, 320, 384],
        (1., 3): [0, 32, 40, 48, 56, 64, 80, 96, 112,
                  128, 160, 192, 224, 256, 320],
        (2., 1): [0, 32, 48, 56, 64, 80, 96, 112, 128,
                  144, 160, 176, 192, 224, 256],
        (2., 2): [0, 8, 16, 24, 32, 40, 48, 56, 64,
                  80, 96, 112, 128, 144, 160],
    }

    __BITRATE[(2, 3)] = __BITRATE[(2, 2)]
    for i in range(1, 4):
        __BITRATE[(2.5, i)] = __BITRATE[(2, i)]

    # Map version to sample rates.
    __RATES = {
        1: [44100, 48000, 32000],
        2: [22050, 24000, 16000],
        2.5: [11025, 12000, 8000]
    }

    sketchy = False

    def __init__(self, fileobj):
        """Raises HeaderNotFoundError"""

        self.frame_offset = fileobj.tell()

        r = BitReader(fileobj)
        try:
            if r.bits(11) != 0x7ff:
                raise HeaderNotFoundError("invalid sync")
            version = r.bits(2)
            layer = r.bits(2)
            protection = r.bits(1)
            bitrate = r.bits(4)
            sample_rate = r.bits(2)
            padding = r.bits(1)
            r.skip(1)  # private
            self.mode = r.bits(2)
            r.skip(6)
        except BitReaderError:
            raise HeaderNotFoundError("truncated header")

        assert r.get_position() == 32 and r.is_aligned()

        # try to be strict here to redice the chance of a false positive
        if version == 1 or layer == 0 or sample_rate == 0x3 or \
                bitrate == 0xf or bitrate == 0:
            raise HeaderNotFoundError("invalid header")

        self.channels = 1 if self.mode == MONO else 2

        self.version = [2.5, None, 2, 1][version]
        self.layer = 4 - layer
        self.protected = not protection
        self.padding = bool(padding)

        self.bitrate = self.__BITRATE[(self.version, self.layer)][bitrate]
        self.bitrate *= 1000
        self.sample_rate = self.__RATES[self.version][sample_rate]

        if self.layer == 1:
            frame_size = 384
            slot = 4
        elif self.version >= 2 and self.layer == 3:
            frame_size = 576
            slot = 1
        else:
            frame_size = 1152
            slot = 1

        frame_length = (
            ((frame_size // 8 * self.bitrate) // self.sample_rate) +
            padding) * slot

        self.sketchy = True

        # Try to find/parse the Xing header, which trumps the above length
        # and bitrate calculation.
        if self.layer == 3:
            self._parse_vbr_header(fileobj, self.frame_offset, frame_size,
                                   frame_length)

        fileobj.seek(self.frame_offset + frame_length, 0)

    def _parse_vbr_header(self, fileobj, frame_offset, frame_size,
                          frame_length):
        """Does not raise"""

        # Xing
        xing_offset = XingHeader.get_offset(self)
        fileobj.seek(frame_offset + xing_offset, 0)
        try:
            xing = XingHeader(fileobj)
        except XingHeaderError:
            pass
        else:
            lame = xing.lame_header
            self.sketchy = False
            self.bitrate_mode = _guess_xing_bitrate_mode(xing)
            self.encoder_settings = xing.get_encoder_settings()
            if xing.frames != -1:
                samples = frame_size * xing.frames
                if xing.bytes != -1 and samples > 0:
                    # the first frame is only included in xing.bytes but
                    # not in xing.frames, skip it.
                    audio_bytes = max(0, xing.bytes - frame_length)
                    self.bitrate = intround((
                        audio_bytes * 8 * self.sample_rate) / float(samples))
                if lame is not None:
                    samples -= lame.encoder_delay_start
                    samples -= lame.encoder_padding_end
                if samples < 0:
                    # older lame versions wrote bogus delay/padding for short
                    # files with low bitrate
                    samples = 0
                self.length = float(samples) / self.sample_rate
            if xing.lame_version_desc:
                self.encoder_info = u"LAME %s" % xing.lame_version_desc
            if lame is not None:
                self.track_gain = lame.track_gain_adjustment
                self.track_peak = lame.track_peak
                self.album_gain = lame.album_gain_adjustment
            return

        # VBRI
        vbri_offset = VBRIHeader.get_offset(self)
        fileobj.seek(frame_offset + vbri_offset, 0)
        try:
            vbri = VBRIHeader(fileobj)
        except VBRIHeaderError:
            pass
        else:
            self.bitrate_mode = BitrateMode.VBR
            self.encoder_info = u"FhG"
            self.sketchy = False
            self.length = float(frame_size * vbri.frames) / self.sample_rate
            if self.length:
                self.bitrate = int((vbri.bytes * 8) / self.length)


def skip_id3(fileobj):
    """Might raise IOError"""

    # WMP writes multiple id3s, so skip as many as we find
    while True:
        idata = fileobj.read(10)
        try:
            id3, insize = struct.unpack('>3sxxx4s', idata)
        except struct.error:
            id3, insize = b'', 0
        insize = BitPaddedInt(insize)
        if id3 == b'ID3' and insize > 0:
            fileobj.seek(insize, 1)
        else:
            fileobj.seek(-len(idata), 1)
            break


def iter_sync(fileobj, max_read):
    """Iterate over a fileobj and yields on each mpeg sync.

    When yielding the fileobj offset is right before the sync and can be
    changed between iterations without affecting the iteration process.

    Might raise IOError.
    """

    read = 0
    size = 2
    last_byte = b""
    is_second = lambda b: ord(b) & 0xe0 == 0xe0

    while read < max_read:
        data_offset = fileobj.tell()
        new_data = fileobj.read(min(max_read - read, size))
        if not new_data:
            return
        read += len(new_data)

        if last_byte == b"\xff" and is_second(new_data[0:1]):
            fileobj.seek(data_offset - 1, 0)
            yield

        size *= 2
        last_byte = new_data[-1:]

        find_offset = 0
        while True:
            index = new_data.find(b"\xff", find_offset)
            # if not found or the last byte -> read more
            if index == -1 or index == len(new_data) - 1:
                break

            if is_second(new_data[index + 1:index + 2]):
                fileobj.seek(data_offset + index, 0)
                yield
            find_offset = index + 1

        fileobj.seek(data_offset + len(new_data), 0)


class MPEGInfo(StreamInfo):
    """MPEGInfo()

    MPEG audio stream information

    Parse information about an MPEG audio file. This also reads the
    Xing VBR header format.

    This code was implemented based on the format documentation at
    http://mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm.

    Useful attributes:

    Attributes:
        length (`float`): audio length, in seconds
        channels (`int`): number of audio channels
        bitrate (`int`): audio bitrate, in bits per second.
            In case :attr:`bitrate_mode` is :attr:`BitrateMode.UNKNOWN` the
            bitrate is guessed based on the first frame.
        sample_rate (`int`): audio sample rate, in Hz
        encoder_info (`mutagen.text`): a string containing encoder name and
            possibly version. In case a lame tag is present this will start
            with ``"LAME "``, if unknown it is empty, otherwise the
            text format is undefined.
        encoder_settings (`mutagen.text`): a string containing a guess about
            the settings used for encoding. The format is undefined and
            depends on the encoder.
        bitrate_mode (`BitrateMode`): a :class:`BitrateMode`
        track_gain (`float` or `None`): replaygain track gain (89db) or None
        track_peak (`float` or `None`): replaygain track peak or None
        album_gain (`float` or `None`): replaygain album gain (89db) or None

    Useless attributes:

    Attributes:
        version (`float`): MPEG version (1, 2, 2.5)
        layer (`int`): 1, 2, or 3
        mode (`int`): One of STEREO, JOINTSTEREO, DUALCHANNEL, or MONO (0-3)
        protected (`bool`): whether or not the file is "protected"
        sketchy (`bool`): if true, the file may not be valid MPEG audio
    """

    sketchy = False
    encoder_info = u""
    encoder_settings = u""
    bitrate_mode = BitrateMode.UNKNOWN
    track_gain = track_peak = album_gain = album_peak = None

    @convert_error(IOError, error)
    def __init__(self, fileobj, offset=None):
        """Parse MPEG stream information from a file-like object.

        If an offset argument is given, it is used to start looking
        for stream information and Xing headers; otherwise, ID3v2 tags
        will be skipped automatically. A correct offset can make
        loading files significantly faster.

        Raises HeaderNotFoundError, error
        """

        if offset is None:
            fileobj.seek(0, 0)
        else:
            fileobj.seek(offset, 0)

        # skip anyway, because wmp stacks multiple id3 tags
        skip_id3(fileobj)

        # find a sync in the first 1024K, give up after some invalid syncs
        max_read = 1024 * 1024
        max_syncs = 1500
        enough_frames = 4
        min_frames = 2

        self.sketchy = True
        frames = []
        first_frame = None

        for _ in iter_sync(fileobj, max_read):
            max_syncs -= 1
            if max_syncs <= 0:
                break

            for _ in range(enough_frames):
                try:
                    frame = MPEGFrame(fileobj)
                except HeaderNotFoundError:
                    break
                frames.append(frame)
                if not frame.sketchy:
                    break

            # if we have min frames, save it in case this is all we get
            if len(frames) >= min_frames and first_frame is None:
                first_frame = frames[0]

            # if the last frame was a non-sketchy one (has a valid vbr header)
            # we use that
            if frames and not frames[-1].sketchy:
                first_frame = frames[-1]
                self.sketchy = False
                break

            # if we have enough valid frames, use the first
            if len(frames) >= enough_frames:
                first_frame = frames[0]
                self.sketchy = False
                break

            # otherwise start over with the next sync
            del frames[:]

        if first_frame is None:
            raise HeaderNotFoundError("can't sync to MPEG frame")

        assert first_frame

        self.length = -1
        sketchy = self.sketchy
        self.__dict__.update(first_frame.__dict__)
        self.sketchy = sketchy

        # no length, estimate based on file size
        if self.length == -1:
            fileobj.seek(0, 2)
            content_size = fileobj.tell() - first_frame.frame_offset
            self.length = 8 * content_size / float(self.bitrate)

    def pprint(self):
        info = str(self.bitrate_mode).split(".", 1)[-1]
        if self.bitrate_mode == BitrateMode.UNKNOWN:
            info = u"CBR?"
        if self.encoder_info:
            info += ", %s" % self.encoder_info
        if self.encoder_settings:
            info += ", %s" % self.encoder_settings
        s = u"MPEG %s layer %d, %d bps (%s), %s Hz, %d chn, %.2f seconds" % (
            self.version, self.layer, self.bitrate, info,
            self.sample_rate, self.channels, self.length)
        if self.sketchy:
            s += u" (sketchy)"
        return s


class MP3(ID3FileType):
    """MP3(filething)

    An MPEG audio (usually MPEG-1 Layer 3) file.

    Arguments:
        filething (filething)

    Attributes:
        info (`MPEGInfo`)
        tags (`mutagen.id3.ID3`)
    """

    _Info = MPEGInfo

    _mimes = ["audio/mpeg", "audio/mpg", "audio/x-mpeg"]

    @property
    def mime(self):
        l = self.info.layer
        return ["audio/mp%d" % l, "audio/x-mp%d" % l] + super(MP3, self).mime

    @staticmethod
    def score(filename, fileobj, header_data):
        filename = filename.lower()

        return ((header_data.startswith(b"ID3") or
                 header_data.startswith(b'\xFF\xF2') or
                 header_data.startswith(b'\xFF\xF3') or
                 header_data.startswith(b'\xFF\xFA') or
                 header_data.startswith(b'\xFF\xFB')) * 2 +
                endswith(filename, b".mp3") +
                endswith(filename, b".mp2") + endswith(filename, b".mpg") +
                endswith(filename, b".mpeg"))


Open = MP3


class EasyMP3(MP3):
    """EasyMP3(filething)

    Like MP3, but uses EasyID3 for tags.

    Arguments:
        filething (filething)

    Attributes:
        info (`MPEGInfo`)
        tags (`mutagen.easyid3.EasyID3`)
    """

    from mutagen.easyid3 import EasyID3 as ID3
    ID3 = ID3  # type: ignore
