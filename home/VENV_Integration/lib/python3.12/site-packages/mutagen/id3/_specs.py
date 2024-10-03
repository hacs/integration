# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import struct
import codecs
from struct import unpack, pack

from .._util import total_ordering, decode_terminated, enum, flags, \
    cdata, encode_endian, intround, bchr
from ._util import BitPaddedInt, is_valid_frame_id


@enum
class PictureType(object):
    """Enumeration of image types defined by the ID3 standard for the APIC
    frame, but also reused in WMA/FLAC/VorbisComment.
    """

    OTHER = 0
    """Other"""

    FILE_ICON = 1
    """32x32 pixels 'file icon' (PNG only)"""

    OTHER_FILE_ICON = 2
    """Other file icon"""

    COVER_FRONT = 3
    """Cover (front)"""

    COVER_BACK = 4
    """Cover (back)"""

    LEAFLET_PAGE = 5
    """Leaflet page"""

    MEDIA = 6
    """Media (e.g. label side of CD)"""

    LEAD_ARTIST = 7
    """Lead artist/lead performer/soloist"""

    ARTIST = 8
    """Artist/performer"""

    CONDUCTOR = 9
    """Conductor"""

    BAND = 10
    """Band/Orchestra"""

    COMPOSER = 11
    """Composer"""

    LYRICIST = 12
    """Lyricist/text writer"""

    RECORDING_LOCATION = 13
    """Recording Location"""

    DURING_RECORDING = 14
    """During recording"""

    DURING_PERFORMANCE = 15
    """During performance"""

    SCREEN_CAPTURE = 16
    """Movie/video screen capture"""

    FISH = 17
    """A bright coloured fish"""

    ILLUSTRATION = 18
    """Illustration"""

    BAND_LOGOTYPE = 19
    """Band/artist logotype"""

    PUBLISHER_LOGOTYPE = 20
    """Publisher/Studio logotype"""

    def _pprint(self):
        return str(self).split(".", 1)[-1].lower().replace("_", " ")


@flags
class CTOCFlags(object):

    TOP_LEVEL = 0x2
    """Identifies the CTOC root frame"""

    ORDERED = 0x1
    """Child elements are ordered"""


class SpecError(Exception):
    pass


class Spec(object):

    handle_nodata = False
    """If reading empty data is possible and writing it back will again
    result in no data.
    """

    def __init__(self, name, default):
        self.name = name
        self.default = default

    def __hash__(self):
        raise TypeError("Spec objects are unhashable")

    def _validate23(self, frame, value, **kwargs):
        """Return a possibly modified value which, if written,
        results in valid id3v2.3 data.
        """

        return value

    def read(self, header, frame, data):
        """
        Returns:
            (value: object, left_data: bytes)
        Raises:
            SpecError
        """

        raise NotImplementedError

    def write(self, config, frame, value):
        """
        Returns:
            bytes: The serialized data
        Raises:
            SpecError
        """
        raise NotImplementedError

    def validate(self, frame, value):
        """
        Returns:
            the validated value
        Raises:
            ValueError
            TypeError
        """

        raise NotImplementedError


class ByteSpec(Spec):

    def __init__(self, name, default=0):
        super(ByteSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        return bytearray(data)[0], data[1:]

    def write(self, config, frame, value):
        return bchr(value)

    def validate(self, frame, value):
        if value is not None:
            bchr(value)
        return value


class PictureTypeSpec(ByteSpec):

    def __init__(self, name, default=PictureType.COVER_FRONT):
        super(PictureTypeSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        value, data = ByteSpec.read(self, header, frame, data)
        return PictureType(value), data

    def validate(self, frame, value):
        value = ByteSpec.validate(self, frame, value)
        if value is not None:
            return PictureType(value)
        return value


class CTOCFlagsSpec(ByteSpec):

    def read(self, header, frame, data):
        value, data = ByteSpec.read(self, header, frame, data)
        return CTOCFlags(value), data

    def validate(self, frame, value):
        value = ByteSpec.validate(self, frame, value)
        if value is not None:
            return CTOCFlags(value)
        return value


class IntegerSpec(Spec):
    def read(self, header, frame, data):
        return int(BitPaddedInt(data, bits=8)), b''

    def write(self, config, frame, value):
        return BitPaddedInt.to_str(value, bits=8, width=-1)

    def validate(self, frame, value):
        return value


class SizedIntegerSpec(Spec):

    def __init__(self, name, size, default):
        self.name, self.__sz = name, size
        self.default = default

    def read(self, header, frame, data):
        return int(BitPaddedInt(data[:self.__sz], bits=8)), data[self.__sz:]

    def write(self, config, frame, value):
        return BitPaddedInt.to_str(value, bits=8, width=self.__sz)

    def validate(self, frame, value):
        return value


@enum
class Encoding(object):
    """Text Encoding"""

    LATIN1 = 0
    """ISO-8859-1"""

    UTF16 = 1
    """UTF-16 with BOM"""

    UTF16BE = 2
    """UTF-16BE without BOM"""

    UTF8 = 3
    """UTF-8"""


class EncodingSpec(ByteSpec):

    def __init__(self, name, default=Encoding.UTF16):
        super(EncodingSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        enc, data = super(EncodingSpec, self).read(header, frame, data)
        if enc not in (Encoding.LATIN1, Encoding.UTF16, Encoding.UTF16BE,
                       Encoding.UTF8):
            raise SpecError('Invalid Encoding: %r' % enc)
        return Encoding(enc), data

    def validate(self, frame, value):
        if value is None:
            raise TypeError
        if value not in (Encoding.LATIN1, Encoding.UTF16, Encoding.UTF16BE,
                         Encoding.UTF8):
            raise ValueError('Invalid Encoding: %r' % value)
        return Encoding(value)

    def _validate23(self, frame, value, **kwargs):
        # only 0, 1 are valid in v2.3, default to utf-16
        if value not in (Encoding.LATIN1, Encoding.UTF16):
            value = Encoding.UTF16
        return value


class StringSpec(Spec):
    """A fixed size ASCII only payload."""

    def __init__(self, name, length, default=None):
        if default is None:
            default = u" " * length
        super(StringSpec, self).__init__(name, default)
        self.len = length

    def read(s, header, frame, data):
        chunk = data[:s.len]
        try:
            ascii = chunk.decode("ascii")
        except UnicodeDecodeError:
            raise SpecError("not ascii")
        else:
            chunk = ascii

        return chunk, data[s.len:]

    def write(self, config, frame, value):

        value = value.encode("ascii")
        return (bytes(value) + b'\x00' * self.len)[:self.len]

    def validate(self, frame, value):
        if value is None:
            raise TypeError

        if not isinstance(value, str):
            raise TypeError("%s has to be str" % self.name)
        value.encode("ascii")

        if len(value) == self.len:
            return value

        raise ValueError('Invalid StringSpec[%d] data: %r' % (self.len, value))


class RVASpec(Spec):

    def __init__(self, name, stereo_only, default=[0, 0]):
        # two_chan: RVA has only 2 channels, while RVAD has 6 channels
        super(RVASpec, self).__init__(name, default)
        self._max_values = 4 if stereo_only else 12

    def read(self, header, frame, data):
        # inc/dec flags
        spec = ByteSpec("flags", 0)
        flags, data = spec.read(header, frame, data)
        if not data:
            raise SpecError("truncated")

        # how many bytes per value
        bits, data = spec.read(header, frame, data)
        if bits == 0:
            # not allowed according to spec
            raise SpecError("bits used has to be > 0")
        bytes_per_value = (bits + 7) // 8

        values = []
        while len(data) >= bytes_per_value and len(values) < self._max_values:
            v = BitPaddedInt(data[:bytes_per_value], bits=8)
            data = data[bytes_per_value:]
            values.append(v)

        if len(values) < 2:
            raise SpecError("First two values not optional")

        # if the respective flag bit is zero, take as decrement
        for bit, index in enumerate([0, 1, 4, 5, 8, 10]):
            if not cdata.test_bit(flags, bit):
                try:
                    values[index] = -values[index]
                except IndexError:
                    break

        return values, data

    def write(self, config, frame, values):
        if len(values) < 2 or len(values) > self._max_values:
            raise SpecError(
                "at least two volume change values required, max %d" %
                self._max_values)

        spec = ByteSpec("flags", 0)

        flags = 0
        values = list(values)
        for bit, index in enumerate([0, 1, 4, 5, 8, 10]):
            try:
                if values[index] < 0:
                    values[index] = -values[index]
                else:
                    flags |= (1 << bit)
            except IndexError:
                break

        buffer_ = bytearray()
        buffer_.extend(spec.write(config, frame, flags))

        # serialized and make them all the same size (min 2 bytes)
        byte_values = [
            BitPaddedInt.to_str(v, bits=8, width=-1, minwidth=2)
            for v in values]
        max_bytes = max([len(v) for v in byte_values])
        byte_values = [v.ljust(max_bytes, b"\x00") for v in byte_values]

        bits = max_bytes * 8
        buffer_.extend(spec.write(config, frame, bits))

        for v in byte_values:
            buffer_.extend(v)

        return bytes(buffer_)

    def validate(self, frame, values):
        if len(values) < 2 or len(values) > self._max_values:
            raise ValueError("needs list of length 2..%d" % self._max_values)
        return values


class FrameIDSpec(StringSpec):

    def __init__(self, name, length):
        super(FrameIDSpec, self).__init__(name, length, u"X" * length)

    def validate(self, frame, value):
        value = super(FrameIDSpec, self).validate(frame, value)
        if not is_valid_frame_id(value):
            raise ValueError("Invalid frame ID")
        return value


class BinaryDataSpec(Spec):

    handle_nodata = True

    def __init__(self, name, default=b""):
        super(BinaryDataSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        return data, b''

    def write(self, config, frame, value):
        if isinstance(value, bytes):
            return value
        value = str(value).encode("ascii")
        return value

    def validate(self, frame, value):
        if value is None:
            raise TypeError
        if isinstance(value, bytes):
            return value
        else:
            raise TypeError("%s has to be bytes" % self.name)

        value = str(value).encode("ascii")
        return value


def iter_text_fixups(data, encoding):
    """Yields a series of repaired text values for decoding"""

    yield data
    if encoding == Encoding.UTF16BE:
        # wrong termination
        yield data + b"\x00"
    elif encoding == Encoding.UTF16:
        # wrong termination
        yield data + b"\x00"
        # utf-16 is missing BOM, content is usually utf-16-le
        yield codecs.BOM_UTF16_LE + data
        # both cases combined
        yield codecs.BOM_UTF16_LE + data + b"\x00"


class EncodedTextSpec(Spec):

    _encodings = {
        Encoding.LATIN1: ('latin1', b'\x00'),
        Encoding.UTF16: ('utf16', b'\x00\x00'),
        Encoding.UTF16BE: ('utf_16_be', b'\x00\x00'),
        Encoding.UTF8: ('utf8', b'\x00'),
    }

    def __init__(self, name, default=u""):
        super(EncodedTextSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        enc, term = self._encodings[frame.encoding]
        err = None
        for data in iter_text_fixups(data, frame.encoding):
            try:
                value, data = decode_terminated(data, enc, strict=False)
            except ValueError as e:
                err = e
            else:
                # Older id3 did not support multiple values, but we still
                # read them. To not missinterpret zero padded values with
                # a list of empty strings, stop if everything left is zero.
                # https://github.com/quodlibet/mutagen/issues/276
                if header.version < header._V24 and not data.strip(b"\x00"):
                    data = b""
                return value, data
        raise SpecError(err)

    def write(self, config, frame, value):
        enc, term = self._encodings[frame.encoding]
        try:
            return encode_endian(value, enc, le=True) + term
        except UnicodeEncodeError as e:
            raise SpecError(e)

    def validate(self, frame, value):
        return str(value)


class MultiSpec(Spec):
    def __init__(self, name, *specs, **kw):
        super(MultiSpec, self).__init__(name, default=kw.get('default'))
        self.specs = specs
        self.sep = kw.get('sep')

    def read(self, header, frame, data):
        values = []
        while data:
            record = []
            for spec in self.specs:
                value, data = spec.read(header, frame, data)
                record.append(value)
            if len(self.specs) != 1:
                values.append(record)
            else:
                values.append(record[0])
        return values, data

    def write(self, config, frame, value):
        data = []
        if len(self.specs) == 1:
            for v in value:
                data.append(self.specs[0].write(config, frame, v))
        else:
            for record in value:
                for v, s in zip(record, self.specs):
                    data.append(s.write(config, frame, v))
        return b''.join(data)

    def validate(self, frame, value):
        if self.sep and isinstance(value, str):
            value = value.split(self.sep)
        if isinstance(value, list):
            if len(self.specs) == 1:
                return [self.specs[0].validate(frame, v) for v in value]
            else:
                return [
                    [s.validate(frame, v) for (v, s) in zip(val, self.specs)]
                    for val in value]
        raise ValueError('Invalid MultiSpec data: %r' % value)

    def _validate23(self, frame, value, **kwargs):
        if len(self.specs) != 1:
            return [[s._validate23(frame, v, **kwargs)
                     for (v, s) in zip(val, self.specs)]
                    for val in value]

        spec = self.specs[0]

        # Merge single text spec multispecs only.
        # (TimeStampSpec being the exception, but it's not a valid v2.3 frame)
        if not isinstance(spec, EncodedTextSpec) or \
                isinstance(spec, TimeStampSpec):
            return value

        value = [spec._validate23(frame, v, **kwargs) for v in value]
        if kwargs.get("sep") is not None:
            return [spec.validate(frame, kwargs["sep"].join(value))]
        return value


class EncodedNumericTextSpec(EncodedTextSpec):
    pass


class EncodedNumericPartTextSpec(EncodedTextSpec):
    pass


class Latin1TextSpec(Spec):

    def __init__(self, name, default=u""):
        super(Latin1TextSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        if b'\x00' in data:
            data, ret = data.split(b'\x00', 1)
        else:
            ret = b''
        return data.decode('latin1'), ret

    def write(self, config, data, value):
        return value.encode('latin1') + b'\x00'

    def validate(self, frame, value):
        return str(value)


class ID3FramesSpec(Spec):

    handle_nodata = True

    def __init__(self, name, default=[]):
        super(ID3FramesSpec, self).__init__(name, default)

    def read(self, header, frame, data):
        from ._tags import ID3Tags

        tags = ID3Tags()
        return tags, tags._read(header, data)

    def _validate23(self, frame, value, **kwargs):
        from ._tags import ID3Tags

        v = ID3Tags()
        for frame in value.values():
            v.add(frame._get_v23_frame(**kwargs))
        return v

    def write(self, config, frame, value):
        return bytes(value._write(config))

    def validate(self, frame, value):
        from ._tags import ID3Tags

        if isinstance(value, ID3Tags):
            return value

        tags = ID3Tags()
        for v in value:
            tags.add(v)

        return tags


class Latin1TextListSpec(Spec):

    def __init__(self, name, default=[]):
        super(Latin1TextListSpec, self).__init__(name, default)
        self._bspec = ByteSpec("entry_count", default=0)
        self._lspec = Latin1TextSpec("child_element_id")

    def read(self, header, frame, data):
        count, data = self._bspec.read(header, frame, data)
        entries = []
        for i in range(count):
            entry, data = self._lspec.read(header, frame, data)
            entries.append(entry)
        return entries, data

    def write(self, config, frame, value):
        b = self._bspec.write(config, frame, len(value))
        for v in value:
            b += self._lspec.write(config, frame, v)
        return b

    def validate(self, frame, value):
        return [self._lspec.validate(frame, v) for v in value]


@total_ordering
class ID3TimeStamp(object):
    """A time stamp in ID3v2 format.

    This is a restricted form of the ISO 8601 standard; time stamps
    take the form of:
        YYYY-MM-DD HH:MM:SS
    Or some partial form (YYYY-MM-DD HH, YYYY, etc.).

    The 'text' attribute contains the raw text data of the time stamp.
    """

    import re

    def __init__(self, text):
        if isinstance(text, ID3TimeStamp):
            text = text.text
        elif not isinstance(text, str):
            raise TypeError("not a str")

        self.text = text

    __formats = ['%04d'] + ['%02d'] * 5
    __seps = ['-', '-', ' ', ':', ':', 'x']

    def get_text(self):
        parts = [self.year, self.month, self.day,
                 self.hour, self.minute, self.second]
        pieces = []
        for i, part in enumerate(parts):
            if part is None:
                break
            pieces.append(self.__formats[i] % part + self.__seps[i])
        return u''.join(pieces)[:-1]

    def set_text(self, text, splitre=re.compile('[-T:/.]|\\s+')):
        year, month, day, hour, minute, second = \
            splitre.split(text + ':::::')[:6]
        for a in 'year month day hour minute second'.split():
            try:
                v = int(locals()[a])
            except ValueError:
                v = None
            setattr(self, a, v)

    text = property(get_text, set_text, doc="ID3v2.4 date and time.")

    def __str__(self):
        return self.text

    def __bytes__(self):
        return self.text.encode("utf-8")

    def __repr__(self):
        return repr(self.text)

    def __eq__(self, other):
        return isinstance(other, ID3TimeStamp) and self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    __hash__ = object.__hash__

    def encode(self, *args):
        return self.text.encode(*args)


class TimeStampSpec(EncodedTextSpec):
    def read(self, header, frame, data):
        value, data = super(TimeStampSpec, self).read(header, frame, data)
        return self.validate(frame, value), data

    def write(self, config, frame, data):
        return super(TimeStampSpec, self).write(config, frame,
                                                data.text.replace(' ', 'T'))

    def validate(self, frame, value):
        try:
            return ID3TimeStamp(value)
        except TypeError:
            raise ValueError("Invalid ID3TimeStamp: %r" % value)


class ChannelSpec(ByteSpec):
    (OTHER, MASTER, FRONTRIGHT, FRONTLEFT, BACKRIGHT, BACKLEFT, FRONTCENTRE,
     BACKCENTRE, SUBWOOFER) = range(9)


class VolumeAdjustmentSpec(Spec):
    def read(self, header, frame, data):
        value, = unpack('>h', data[0:2])
        return value / 512.0, data[2:]

    def write(self, config, frame, value):
        number = intround(value * 512)
        # pack only fails in 2.7, do it manually in 2.6
        if not -32768 <= number <= 32767:
            raise SpecError("not in range")
        return pack('>h', number)

    def validate(self, frame, value):
        if value is not None:
            try:
                self.write(None, frame, value)
            except SpecError:
                raise ValueError("out of range")
        return value


class VolumePeakSpec(Spec):
    def read(self, header, frame, data):
        # http://bugs.xmms.org/attachment.cgi?id=113&action=view
        peak = 0
        data_array = bytearray(data)
        bits = data_array[0]
        vol_bytes = min(4, (bits + 7) >> 3)
        # not enough frame data
        if vol_bytes + 1 > len(data):
            raise SpecError("not enough frame data")
        shift = ((8 - (bits & 7)) & 7) + (4 - vol_bytes) * 8
        for i in range(1, vol_bytes + 1):
            peak *= 256
            peak += data_array[i]
        peak *= 2 ** shift
        return (float(peak) / (2 ** 31 - 1)), data[1 + vol_bytes:]

    def write(self, config, frame, value):
        number = intround(value * 32768)
        # pack only fails in 2.7, do it manually in 2.6
        if not 0 <= number <= 65535:
            raise SpecError("not in range")
        # always write as 16 bits for sanity.
        return b"\x10" + pack('>H', number)

    def validate(self, frame, value):
        if value is not None:
            try:
                self.write(None, frame, value)
            except SpecError:
                raise ValueError("out of range")
        return value


class SynchronizedTextSpec(EncodedTextSpec):
    def read(self, header, frame, data):
        texts = []
        encoding, term = self._encodings[frame.encoding]
        while data:
            try:
                value, data = decode_terminated(data, encoding)
            except ValueError:
                raise SpecError("decoding error")

            if len(data) < 4:
                raise SpecError("not enough data")
            time, = struct.unpack(">I", data[:4])

            texts.append((value, time))
            data = data[4:]
        return texts, b""

    def write(self, config, frame, value):
        data = []
        encoding, term = self._encodings[frame.encoding]
        for text, time in value:
            try:
                text = encode_endian(text, encoding, le=True) + term
            except UnicodeEncodeError as e:
                raise SpecError(e)
            data.append(text + struct.pack(">I", time))
        return b"".join(data)

    def validate(self, frame, value):
        return value


class KeyEventSpec(Spec):
    def read(self, header, frame, data):
        events = []
        while len(data) >= 5:
            events.append(struct.unpack(">bI", data[:5]))
            data = data[5:]
        return events, data

    def write(self, config, frame, value):
        return b"".join(struct.pack(">bI", *event) for event in value)

    def validate(self, frame, value):
        return list(value)


class VolumeAdjustmentsSpec(Spec):
    # Not to be confused with VolumeAdjustmentSpec.
    def read(self, header, frame, data):
        adjustments = {}
        while len(data) >= 4:
            freq, adj = struct.unpack(">Hh", data[:4])
            data = data[4:]
            freq /= 2.0
            adj /= 512.0
            adjustments[freq] = adj
        adjustments = sorted(adjustments.items())
        return adjustments, data

    def write(self, config, frame, value):
        value.sort()
        return b"".join(struct.pack(">Hh", int(freq * 2), int(adj * 512))
                        for (freq, adj) in value)

    def validate(self, frame, value):
        return list(value)


class ASPIIndexSpec(Spec):

    def read(self, header, frame, data):
        if frame.b == 16:
            format = "H"
            size = 2
        elif frame.b == 8:
            format = "B"
            size = 1
        else:
            raise SpecError("invalid bit count in ASPI (%d)" % frame.b)

        indexes = data[:frame.N * size]
        data = data[frame.N * size:]
        try:
            return list(struct.unpack(">" + format * frame.N, indexes)), data
        except struct.error as e:
            raise SpecError(e)

    def write(self, config, frame, values):
        if frame.b == 16:
            format = "H"
        elif frame.b == 8:
            format = "B"
        else:
            raise SpecError("frame.b must be 8 or 16")
        try:
            return struct.pack(">" + format * frame.N, *values)
        except struct.error as e:
            raise SpecError(e)

    def validate(self, frame, values):
        return list(values)
