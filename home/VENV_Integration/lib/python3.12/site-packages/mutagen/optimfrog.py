# Copyright (C) 2006  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""OptimFROG audio streams with APEv2 tags.

OptimFROG is a lossless audio compression program. Its main goal is to
reduce at maximum the size of audio files, while permitting bit
identical restoration for all input. It is similar with the ZIP
compression, but it is highly specialized to compress audio data.

Only versions 4.5 and higher are supported.

For more information, see http://www.losslessaudio.org/
"""

__all__ = ["OptimFROG", "Open", "delete"]

import struct

from ._util import convert_error, endswith
from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, error, delete


SAMPLE_TYPE_BITS = {
    0: 8,
    1: 8,
    2: 16,
    3: 16,
    4: 24,
    5: 24,
    6: 32,
    7: 32,
}


class OptimFROGHeaderError(error):
    pass


class OptimFROGInfo(StreamInfo):
    """OptimFROGInfo()

    OptimFROG stream information.

    Attributes:
        channels (`int`): number of audio channels
        length (`float`): file length in seconds, as a float
        sample_rate (`int`): audio sampling rate in Hz
        bits_per_sample (`int`): the audio sample size
        encoder_info (`mutagen.text`): encoder version, e.g. "5.100"
    """

    @convert_error(IOError, OptimFROGHeaderError)
    def __init__(self, fileobj):
        """Raises OptimFROGHeaderError"""

        header = fileobj.read(76)
        if len(header) != 76 or not header.startswith(b"OFR "):
            raise OptimFROGHeaderError("not an OptimFROG file")
        data_size = struct.unpack("<I", header[4:8])[0]
        if data_size != 12 and data_size < 15:
            raise OptimFROGHeaderError("not an OptimFROG file")
        (total_samples, total_samples_high, sample_type, self.channels,
         self.sample_rate) = struct.unpack("<IHBBI", header[8:20])
        total_samples += total_samples_high << 32
        self.channels += 1
        self.bits_per_sample = SAMPLE_TYPE_BITS.get(sample_type)
        if self.sample_rate:
            self.length = float(total_samples) / (self.channels *
                                                  self.sample_rate)
        else:
            self.length = 0.0
        if data_size >= 15:
            encoder_id = struct.unpack("<H", header[20:22])[0]
            version = str((encoder_id >> 4) + 4500)
            self.encoder_info = "%s.%s" % (version[0], version[1:])
        else:
            self.encoder_info = ""

    def pprint(self):
        return u"OptimFROG, %.2f seconds, %d Hz" % (self.length,
                                                    self.sample_rate)


class OptimFROG(APEv2File):
    """OptimFROG(filething)

    Attributes:
        info (`OptimFROGInfo`)
        tags (`mutagen.apev2.APEv2`)
    """

    _Info = OptimFROGInfo

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"OFR") + endswith(filename, b".ofr") +
                endswith(filename, b".ofs"))

Open = OptimFROG
