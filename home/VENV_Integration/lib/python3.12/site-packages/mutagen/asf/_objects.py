# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import struct
from typing import Dict, Type

from mutagen._util import cdata, get_size
from mutagen._tags import PaddingInfo

from ._util import guid2bytes, bytes2guid, CODECS, ASFError, ASFHeaderError
from ._attrs import ASFBaseAttribute, ASFUnicodeAttribute


class BaseObject(object):
    """Base ASF object."""

    GUID: bytes
    _TYPES: "Dict[bytes, Type[BaseObject]]" = {}

    def __init__(self):
        self.objects = []
        self.data = b""

    def parse(self, asf, data):
        self.data = data

    def render(self, asf):
        data = self.GUID + struct.pack("<Q", len(self.data) + 24) + self.data
        return data

    def get_child(self, guid):
        for obj in self.objects:
            if obj.GUID == guid:
                return obj
        return None

    @classmethod
    def _register(cls, other):
        cls._TYPES[other.GUID] = other
        return other

    @classmethod
    def _get_object(cls, guid):
        if guid in cls._TYPES:
            return cls._TYPES[guid]()
        else:
            return UnknownObject(guid)

    def __repr__(self):
        return "<%s GUID=%s objects=%r>" % (
            type(self).__name__, bytes2guid(self.GUID), self.objects)

    def pprint(self):
        l = []
        l.append("%s(%s)" % (type(self).__name__, bytes2guid(self.GUID)))
        for o in self.objects:
            for e in o.pprint().splitlines():
                l.append("  " + e)
        return "\n".join(l)


class UnknownObject(BaseObject):
    """Unknown ASF object."""

    def __init__(self, guid):
        super(UnknownObject, self).__init__()
        assert isinstance(guid, bytes)
        self.GUID = guid


@BaseObject._register
class HeaderObject(BaseObject):
    """ASF header."""

    GUID = guid2bytes("75B22630-668E-11CF-A6D9-00AA0062CE6C")

    @classmethod
    def parse_full(cls, asf, fileobj):
        """Raises ASFHeaderError"""

        header = cls()

        remaining_header, num_objects = cls.parse_size(fileobj)
        remaining_header -= 30

        for i in range(num_objects):
            obj_header_size = 24
            if remaining_header < obj_header_size:
                raise ASFHeaderError("invalid header size")
            data = fileobj.read(obj_header_size)
            if len(data) != obj_header_size:
                raise ASFHeaderError("truncated")
            remaining_header -= obj_header_size

            guid, size = struct.unpack("<16sQ", data)
            obj = BaseObject._get_object(guid)

            payload_size = size - obj_header_size
            if remaining_header < payload_size:
                raise ASFHeaderError("invalid object size")
            remaining_header -= payload_size

            try:
                data = fileobj.read(payload_size)
            except (OverflowError, MemoryError):
                # read doesn't take 64bit values
                raise ASFHeaderError("invalid header size")
            if len(data) != payload_size:
                raise ASFHeaderError("truncated")

            try:
                obj.parse(asf, data)
            except struct.error:
                raise ASFHeaderError("truncated")
            header.objects.append(obj)

        return header

    @classmethod
    def parse_size(cls, fileobj):
        """Returns (size, num_objects)

        Raises ASFHeaderError
        """

        header = fileobj.read(30)
        if len(header) != 30 or header[:16] != HeaderObject.GUID:
            raise ASFHeaderError("Not an ASF file.")

        return struct.unpack("<QL", header[16:28])

    def render_full(self, asf, fileobj, available, padding_func):
        # Render everything except padding
        num_objects = 0
        data = bytearray()
        for obj in self.objects:
            if obj.GUID == PaddingObject.GUID:
                continue
            data += obj.render(asf)
            num_objects += 1

        # calculate how much space we need at least
        padding_obj = PaddingObject()
        header_size = len(HeaderObject.GUID) + 14
        padding_overhead = len(padding_obj.render(asf))
        needed_size = len(data) + header_size + padding_overhead

        # ask the user for padding adjustments
        file_size = get_size(fileobj)
        content_size = file_size - available
        if content_size < 0:
            raise ASFHeaderError("truncated content")
        info = PaddingInfo(available - needed_size, content_size)

        # add padding
        padding = info._get_padding(padding_func)
        padding_obj.parse(asf, b"\x00" * padding)
        data += padding_obj.render(asf)
        num_objects += 1

        data = (HeaderObject.GUID +
                struct.pack("<QL", len(data) + 30, num_objects) +
                b"\x01\x02" + data)

        return data

    def parse(self, asf, data):
        raise NotImplementedError

    def render(self, asf):
        raise NotImplementedError


@BaseObject._register
class ContentDescriptionObject(BaseObject):
    """Content description."""

    GUID = guid2bytes("75B22633-668E-11CF-A6D9-00AA0062CE6C")

    NAMES = [
        u"Title",
        u"Author",
        u"Copyright",
        u"Description",
        u"Rating",
    ]

    def parse(self, asf, data):
        super(ContentDescriptionObject, self).parse(asf, data)
        lengths = struct.unpack("<HHHHH", data[:10])
        texts = []
        pos = 10
        for length in lengths:
            end = pos + length
            if length > 0:
                texts.append(data[pos:end].decode("utf-16-le").strip(u"\x00"))
            else:
                texts.append(None)
            pos = end

        for key, value in zip(self.NAMES, texts):
            if value is not None:
                value = ASFUnicodeAttribute(value=value)
                asf._tags.setdefault(self.GUID, []).append((key, value))

    def render(self, asf):
        def render_text(name):
            value = asf.to_content_description.get(name)
            if value is not None:
                return str(value).encode("utf-16-le") + b"\x00\x00"
            else:
                return b""

        texts = [render_text(x) for x in self.NAMES]
        data = struct.pack("<HHHHH", *map(len, texts)) + b"".join(texts)
        return self.GUID + struct.pack("<Q", 24 + len(data)) + data


@BaseObject._register
class ExtendedContentDescriptionObject(BaseObject):
    """Extended content description."""

    GUID = guid2bytes("D2D0A440-E307-11D2-97F0-00A0C95EA850")

    def parse(self, asf, data):
        super(ExtendedContentDescriptionObject, self).parse(asf, data)
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in range(num_attributes):
            name_length, = struct.unpack("<H", data[pos:pos + 2])
            pos += 2
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value_type, value_length = struct.unpack("<HH", data[pos:pos + 4])
            pos += 4
            value = data[pos:pos + value_length]
            pos += value_length
            attr = ASFBaseAttribute._get_type(value_type)(data=value)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_extended_content_description.items()
        data = b"".join(attr.render(name) for (name, attr) in attrs)
        data = struct.pack("<QH", 26 + len(data), len(attrs)) + data
        return self.GUID + data


@BaseObject._register
class FilePropertiesObject(BaseObject):
    """File properties."""

    GUID = guid2bytes("8CABDCA1-A947-11CF-8EE4-00C00C205365")

    def parse(self, asf, data):
        super(FilePropertiesObject, self).parse(asf, data)
        if len(data) < 64:
            raise ASFError("invalid field property entry")
        length, _, preroll = struct.unpack("<QQQ", data[40:64])
        # there are files where preroll is larger than length, limit to >= 0
        asf.info.length = max((length / 10000000.0) - (preroll / 1000.0), 0.0)


@BaseObject._register
class StreamPropertiesObject(BaseObject):
    """Stream properties."""

    GUID = guid2bytes("B7DC0791-A9B7-11CF-8EE6-00C00C205365")

    def parse(self, asf, data):
        super(StreamPropertiesObject, self).parse(asf, data)
        channels, sample_rate, bitrate = struct.unpack("<HII", data[56:66])
        asf.info.channels = channels
        asf.info.sample_rate = sample_rate
        asf.info.bitrate = bitrate * 8


@BaseObject._register
class CodecListObject(BaseObject):
    """Codec List"""

    GUID = guid2bytes("86D15240-311D-11D0-A3A4-00A0C90348F6")

    def _parse_entry(self, data, offset):
        """can raise cdata.error"""

        type_, offset = cdata.uint16_le_from(data, offset)

        units, offset = cdata.uint16_le_from(data, offset)
        # utf-16 code units, not characters..
        next_offset = offset + units * 2
        try:
            name = data[offset:next_offset].decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError:
            name = u""
        offset = next_offset

        units, offset = cdata.uint16_le_from(data, offset)
        next_offset = offset + units * 2
        try:
            desc = data[offset:next_offset].decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError:
            desc = u""
        offset = next_offset

        bytes_, offset = cdata.uint16_le_from(data, offset)
        next_offset = offset + bytes_
        codec = u""
        if bytes_ == 2:
            codec_id = cdata.uint16_le_from(data, offset)[0]
            if codec_id in CODECS:
                codec = CODECS[codec_id]
        offset = next_offset

        return offset, type_, name, desc, codec

    def parse(self, asf, data):
        super(CodecListObject, self).parse(asf, data)

        offset = 16
        count, offset = cdata.uint32_le_from(data, offset)
        for i in range(count):
            try:
                offset, type_, name, desc, codec = \
                    self._parse_entry(data, offset)
            except cdata.error:
                raise ASFError("invalid codec entry")

            # go with the first audio entry
            if type_ == 2:
                name = name.strip()
                desc = desc.strip()
                asf.info.codec_type = codec
                asf.info.codec_name = name
                asf.info.codec_description = desc
                return


@BaseObject._register
class PaddingObject(BaseObject):
    """Padding object"""

    GUID = guid2bytes("1806D474-CADF-4509-A4BA-9AABCB96AAE8")


@BaseObject._register
class StreamBitratePropertiesObject(BaseObject):
    """Stream bitrate properties"""

    GUID = guid2bytes("7BF875CE-468D-11D1-8D82-006097C9A2B2")


@BaseObject._register
class ContentEncryptionObject(BaseObject):
    """Content encryption"""

    GUID = guid2bytes("2211B3FB-BD23-11D2-B4B7-00A0C955FC6E")


@BaseObject._register
class ExtendedContentEncryptionObject(BaseObject):
    """Extended content encryption"""

    GUID = guid2bytes("298AE614-2622-4C17-B935-DAE07EE9289C")


@BaseObject._register
class HeaderExtensionObject(BaseObject):
    """Header extension."""

    GUID = guid2bytes("5FBF03B5-A92E-11CF-8EE3-00C00C205365")

    def parse(self, asf, data):
        super(HeaderExtensionObject, self).parse(asf, data)
        datasize, = struct.unpack("<I", data[18:22])
        datapos = 0
        while datapos < datasize:
            guid, size = struct.unpack(
                "<16sQ", data[22 + datapos:22 + datapos + 24])
            if size < 1:
                raise ASFHeaderError("invalid size in header extension")
            obj = BaseObject._get_object(guid)
            obj.parse(asf, data[22 + datapos + 24:22 + datapos + size])
            self.objects.append(obj)
            datapos += size

    def render(self, asf):
        data = bytearray()
        for obj in self.objects:
            # some files have the padding in the extension header, but we
            # want to add it at the end of the top level header. Just
            # skip padding at this level.
            if obj.GUID == PaddingObject.GUID:
                continue
            data += obj.render(asf)
        return (self.GUID + struct.pack("<Q", 24 + 16 + 6 + len(data)) +
                b"\x11\xD2\xD3\xAB\xBA\xA9\xcf\x11" +
                b"\x8E\xE6\x00\xC0\x0C\x20\x53\x65" +
                b"\x06\x00" + struct.pack("<I", len(data)) + data)


@BaseObject._register
class MetadataObject(BaseObject):
    """Metadata description."""

    GUID = guid2bytes("C5F8CBEA-5BAF-4877-8467-AA8C44FA4CCA")

    def parse(self, asf, data):
        super(MetadataObject, self).parse(asf, data)
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in range(num_attributes):
            (reserved, stream, name_length, value_type,
             value_length) = struct.unpack("<HHHHI", data[pos:pos + 12])
            pos += 12
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value = data[pos:pos + value_length]
            pos += value_length
            args = {'data': value, 'stream': stream}
            if value_type == 2:
                args['dword'] = False
            attr = ASFBaseAttribute._get_type(value_type)(**args)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_metadata.items()
        data = b"".join([attr.render_m(name) for (name, attr) in attrs])
        return (self.GUID + struct.pack("<QH", 26 + len(data), len(attrs)) +
                data)


@BaseObject._register
class MetadataLibraryObject(BaseObject):
    """Metadata library description."""

    GUID = guid2bytes("44231C94-9498-49D1-A141-1D134E457054")

    def parse(self, asf, data):
        super(MetadataLibraryObject, self).parse(asf, data)
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in range(num_attributes):
            (language, stream, name_length, value_type,
             value_length) = struct.unpack("<HHHHI", data[pos:pos + 12])
            pos += 12
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value = data[pos:pos + value_length]
            pos += value_length
            args = {'data': value, 'language': language, 'stream': stream}
            if value_type == 2:
                args['dword'] = False
            attr = ASFBaseAttribute._get_type(value_type)(**args)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_metadata_library
        data = b"".join([attr.render_ml(name) for (name, attr) in attrs])
        return (self.GUID + struct.pack("<QH", 26 + len(data), len(attrs)) +
                data)
