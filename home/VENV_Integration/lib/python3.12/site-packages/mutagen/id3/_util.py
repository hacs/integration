# Copyright (C) 2005  Michael Urman
#               2013  Christoph Reiter
#               2014  Ben Ockmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Union

from mutagen._util import MutagenError


def is_valid_frame_id(frame_id):
    return frame_id.isalnum() and frame_id.isupper()


class ID3SaveConfig(object):

    def __init__(self, v2_version=4, v23_separator=None):
        assert v2_version in (3, 4)
        self.v2_version = v2_version
        self.v23_separator = v23_separator


class error(MutagenError):
    pass


class ID3NoHeaderError(error, ValueError):
    pass


class ID3UnsupportedVersionError(error, NotImplementedError):
    pass


class ID3EncryptionUnsupportedError(error, NotImplementedError):
    pass


class ID3JunkFrameError(error):
    pass


class unsynch(object):
    @staticmethod
    def decode(value: bytes) -> bytes:
        fragments = bytearray(value).split(b'\xff')
        if len(fragments) > 1 and not fragments[-1]:
            raise ValueError('string ended unsafe')

        for f in fragments[1:]:
            if (not f) or (f[0] >= 0xE0):
                raise ValueError('invalid sync-safe string')

            if f[0] == 0x00:
                del f[0]

        return bytes(bytearray(b'\xff').join(fragments))

    @staticmethod
    def encode(value: bytes) -> bytes:
        fragments = bytearray(value).split(b'\xff')
        for f in fragments[1:]:
            if (not f) or (f[0] >= 0xE0) or (f[0] == 0x00):
                f.insert(0, 0x00)
        return bytes(bytearray(b'\xff').join(fragments))


class _BitPaddedMixin(object):

    def as_str(self, width=4, minwidth=4):
        return self.to_str(self, self.bits, self.bigendian, width, minwidth)

    @staticmethod
    def to_str(value: int, bits: int = 7, bigendian: bool = True,
               width: int = 4, minwidth: int = 4) -> bytes:
        mask = (1 << bits) - 1

        if width != -1:
            index = 0
            bytes_ = bytearray(width)
            try:
                while value:
                    bytes_[index] = value & mask
                    value >>= bits
                    index += 1
            except IndexError:
                raise ValueError('Value too wide (>%d bytes)' % width)
        else:
            # PCNT and POPM use growing integers
            # of at least 4 bytes (=minwidth) as counters.
            bytes_ = bytearray()
            append = bytes_.append
            while value:
                append(value & mask)
                value >>= bits
            bytes_ = bytes_.ljust(minwidth, b"\x00")

        if bigendian:
            bytes_.reverse()
        return bytes(bytes_)

    @staticmethod
    def has_valid_padding(value: Union[int, bytes], bits: int = 7) -> bool:
        """Whether the padding bits are all zero"""

        assert bits <= 8

        mask = (((1 << (8 - bits)) - 1) << bits)

        if isinstance(value, int):
            while value:
                if value & mask:
                    return False
                value >>= 8
        elif isinstance(value, bytes):
            for byte in bytearray(value):
                if byte & mask:
                    return False
        else:
            raise TypeError

        return True


class BitPaddedInt(int, _BitPaddedMixin):

    def __new__(cls, value, bits=7, bigendian=True):

        mask = (1 << (bits)) - 1
        numeric_value = 0
        shift = 0

        if isinstance(value, int):
            if value < 0:
                raise ValueError
            while value:
                numeric_value += (value & mask) << shift
                value >>= 8
                shift += bits
        elif isinstance(value, bytes):
            if bigendian:
                value = reversed(value)
            for byte in bytearray(value):
                numeric_value += (byte & mask) << shift
                shift += bits
        else:
            raise TypeError

        self = int.__new__(BitPaddedInt, numeric_value)

        self.bits = bits
        self.bigendian = bigendian
        return self


class ID3BadUnsynchData(error, ValueError):
    """Deprecated"""


class ID3BadCompressedData(error, ValueError):
    """Deprecated"""


class ID3TagError(error, ValueError):
    """Deprecated"""


class ID3Warning(error, UserWarning):
    """Deprecated"""
