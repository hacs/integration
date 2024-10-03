# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""True Audio audio stream information and tags.

True Audio is a lossless format designed for real-time encoding and
decoding. This module is based on the documentation at
http://tausoft.org/wiki/True_Audio_Codec_Format

True Audio files use ID3 tags.
"""

__all__ = ["TrueAudio", "Open", "delete", "EasyTrueAudio"]

from mutagen import StreamInfo
from mutagen.id3 import ID3FileType, delete
from mutagen._util import cdata, MutagenError, convert_error, endswith


class error(MutagenError):
    pass


class TrueAudioHeaderError(error):
    pass


class TrueAudioInfo(StreamInfo):
    """TrueAudioInfo()

    True Audio stream information.

    Attributes:
        length (`float`): audio length, in seconds
        sample_rate (`int`): audio sample rate, in Hz
    """

    @convert_error(IOError, TrueAudioHeaderError)
    def __init__(self, fileobj, offset):
        """Raises TrueAudioHeaderError"""

        fileobj.seek(offset or 0)
        header = fileobj.read(18)
        if len(header) != 18 or not header.startswith(b"TTA"):
            raise TrueAudioHeaderError("TTA header not found")
        self.sample_rate = cdata.uint_le(header[10:14])
        samples = cdata.uint_le(header[14:18])
        self.length = 0.0
        if self.sample_rate != 0:
            self.length = float(samples) / self.sample_rate

    def pprint(self):
        return u"True Audio, %.2f seconds, %d Hz." % (
            self.length, self.sample_rate)


class TrueAudio(ID3FileType):
    """TrueAudio(filething, ID3=None)

    A True Audio file.

    Arguments:
        filething (filething)
        ID3 (mutagen.id3.ID3)

    Attributes:
        info (`TrueAudioInfo`)
        tags (`mutagen.id3.ID3`)
    """

    _Info = TrueAudioInfo
    _mimes = ["audio/x-tta"]

    @staticmethod
    def score(filename, fileobj, header):
        return (header.startswith(b"ID3") + header.startswith(b"TTA") +
                endswith(filename.lower(), b".tta") * 2)


Open = TrueAudio


class EasyTrueAudio(TrueAudio):
    """EasyTrueAudio(filething, ID3=None)

    Like MP3, but uses EasyID3 for tags.

    Arguments:
        filething (filething)
        ID3 (mutagen.id3.ID3)

    Attributes:
        info (`TrueAudioInfo`)
        tags (`mutagen.easyid3.EasyID3`)
    """

    from mutagen.easyid3 import EasyID3 as ID3
    ID3 = ID3  # type: ignore
