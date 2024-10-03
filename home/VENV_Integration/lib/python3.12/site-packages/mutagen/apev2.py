# Copyright (C) 2005  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""APEv2 reading and writing.

The APEv2 format is most commonly used with Musepack files, but is
also the format of choice for WavPack and other formats. Some MP3s
also have APEv2 tags, but this can cause problems with many MP3
decoders and taggers.

APEv2 tags, like Vorbis comments, are freeform key=value pairs. APEv2
keys can be any ASCII string with characters from 0x20 to 0x7E,
between 2 and 255 characters long.  Keys are case-sensitive, but
readers are recommended to be case insensitive, and it is forbidden to
multiple keys which differ only in case.  Keys are usually stored
title-cased (e.g. 'Artist' rather than 'artist').

APEv2 values are slightly more structured than Vorbis comments; values
are flagged as one of text, binary, or an external reference (usually
a URI).

Based off the format specification found at
http://wiki.hydrogenaudio.org/index.php?title=APEv2_specification.
"""

__all__ = ["APEv2", "APEv2File", "Open", "delete"]

import sys
import struct
from io import BytesIO
from collections.abc import MutableSequence

from mutagen import Metadata, FileType, StreamInfo
from mutagen._util import DictMixin, cdata, delete_bytes, total_ordering, \
    MutagenError, loadfile, convert_error, seek_end, get_size, reraise


def is_valid_apev2_key(key):
    # https://wiki.hydrogenaud.io/index.php?title=APE_key
    if not isinstance(key, str):
        raise TypeError("APEv2 key must be str")

    # PY26 - Change to set literal syntax (since set is faster than list here)
    return ((2 <= len(key) <= 255) and (min(key) >= u' ') and
            (max(key) <= u'~') and
            (key not in [u"OggS", u"TAG", u"ID3", u"MP+"]))

# There are three different kinds of APE tag values.
# "0: Item contains text information coded in UTF-8
#  1: Item contains binary information
#  2: Item is a locator of external stored information [e.g. URL]
#  3: reserved"
TEXT, BINARY, EXTERNAL = range(3)

HAS_HEADER = 1 << 31
HAS_NO_FOOTER = 1 << 30
IS_HEADER = 1 << 29


class error(MutagenError):
    pass


class APENoHeaderError(error):
    pass


class APEUnsupportedVersionError(error):
    pass


class APEBadItemError(error):
    pass


class _APEv2Data(object):
    # Store offsets of the important parts of the file.
    start = header = data = footer = end = None
    # Footer or header; seek here and read 32 to get version/size/items/flags
    metadata = None
    # Actual tag data
    tag = None

    version = None
    size = None
    items = None
    flags = 0

    # The tag is at the start rather than the end. A tag at both
    # the start and end of the file (i.e. the tag is the whole file)
    # is not considered to be at the start.
    is_at_start = False

    def __init__(self, fileobj):
        """Raises IOError and apev2.error"""

        self.__find_metadata(fileobj)

        if self.header is None:
            self.metadata = self.footer
        elif self.footer is None:
            self.metadata = self.header
        else:
            self.metadata = max(self.header, self.footer)

        if self.metadata is None:
            return

        self.__fill_missing(fileobj)
        self.__fix_brokenness(fileobj)
        if self.data is not None:
            fileobj.seek(self.data)
            self.tag = fileobj.read(self.size)

    def __find_metadata(self, fileobj):
        # Try to find a header or footer.

        # Check for a simple footer.
        try:
            fileobj.seek(-32, 2)
        except IOError:
            fileobj.seek(0, 2)
            return
        if fileobj.read(8) == b"APETAGEX":
            fileobj.seek(-8, 1)
            self.footer = self.metadata = fileobj.tell()
            return

        # Check for an APEv2 tag followed by an ID3v1 tag at the end.
        try:
            if get_size(fileobj) < 128:
                raise IOError
            fileobj.seek(-128, 2)
            if fileobj.read(3) == b"TAG":

                fileobj.seek(-35, 1)  # "TAG" + header length
                if fileobj.read(8) == b"APETAGEX":
                    fileobj.seek(-8, 1)
                    self.footer = fileobj.tell()
                    return

                # ID3v1 tag at the end, maybe preceded by Lyrics3v2.
                # (http://www.id3.org/lyrics3200.html)
                # (header length - "APETAGEX") - "LYRICS200"
                fileobj.seek(15, 1)
                if fileobj.read(9) == b'LYRICS200':
                    fileobj.seek(-15, 1)  # "LYRICS200" + size tag
                    try:
                        offset = int(fileobj.read(6))
                    except ValueError:
                        raise IOError

                    fileobj.seek(-32 - offset - 6, 1)
                    if fileobj.read(8) == b"APETAGEX":
                        fileobj.seek(-8, 1)
                        self.footer = fileobj.tell()
                        return

        except IOError:
            pass

        # Check for a tag at the start.
        fileobj.seek(0, 0)
        if fileobj.read(8) == b"APETAGEX":
            self.is_at_start = True
            self.header = 0

    def __fill_missing(self, fileobj):
        """Raises IOError and apev2.error"""

        fileobj.seek(self.metadata + 8)

        data = fileobj.read(16)
        if len(data) != 16:
            raise error

        self.version = data[:4]
        self.size = cdata.uint32_le(data[4:8])
        self.items = cdata.uint32_le(data[8:12])
        self.flags = cdata.uint32_le(data[12:])

        if self.header is not None:
            self.data = self.header + 32
            # If we're reading the header, the size is the header
            # offset + the size, which includes the footer.
            self.end = self.data + self.size
            fileobj.seek(self.end - 32, 0)
            if fileobj.read(8) == b"APETAGEX":
                self.footer = self.end - 32
        elif self.footer is not None:
            self.end = self.footer + 32
            self.data = self.end - self.size
            if self.flags & HAS_HEADER:
                self.header = self.data - 32
            else:
                self.header = self.data
        else:
            raise APENoHeaderError("No APE tag found")

        # exclude the footer from size
        if self.footer is not None:
            self.size -= 32

    def __fix_brokenness(self, fileobj):
        # Fix broken tags written with PyMusepack.
        if self.header is not None:
            start = self.header
        else:
            start = self.data
        fileobj.seek(start)

        while start > 0:
            # Clean up broken writing from pre-Mutagen PyMusepack.
            # It didn't remove the first 24 bytes of header.
            try:
                fileobj.seek(-24, 1)
            except IOError:
                break
            else:
                if fileobj.read(8) == b"APETAGEX":
                    fileobj.seek(-8, 1)
                    start = fileobj.tell()
                else:
                    break
        self.start = start


class _CIDictProxy(DictMixin):

    def __init__(self, *args, **kwargs):
        self.__casemap = {}
        self.__dict = {}
        super(_CIDictProxy, self).__init__(*args, **kwargs)
        # Internally all names are stored as lowercase, but the case
        # they were set with is remembered and used when saving.  This
        # is roughly in line with the standard, which says that keys
        # are case-sensitive but two keys differing only in case are
        # not allowed, and recommends case-insensitive
        # implementations.

    def __getitem__(self, key):
        return self.__dict[key.lower()]

    def __setitem__(self, key, value):
        lower = key.lower()
        self.__casemap[lower] = key
        self.__dict[lower] = value

    def __delitem__(self, key):
        lower = key.lower()
        del self.__casemap[lower]
        del self.__dict[lower]

    def keys(self):
        return [self.__casemap.get(key, key) for key in self.__dict.keys()]


class APEv2(_CIDictProxy, Metadata):
    """APEv2(filething=None)

    A file with an APEv2 tag.

    ID3v1 tags are silently ignored and overwritten.
    """

    filename = None

    def pprint(self):
        """Return tag key=value pairs in a human-readable format."""

        items = sorted(self.items())
        return u"\n".join(u"%s=%s" % (k, v.pprint()) for k, v in items)

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething):
        """Load tags from a filename.

        Raises apev2.error
        """

        data = _APEv2Data(filething.fileobj)

        if data.tag:
            self.clear()
            self.__parse_tag(data.tag, data.items)
        else:
            raise APENoHeaderError("No APE tag found")

    def __parse_tag(self, tag, count):
        """Raises IOError and APEBadItemError"""

        fileobj = BytesIO(tag)

        for i in range(count):
            tag_data = fileobj.read(8)
            # someone writes wrong item counts
            if not tag_data:
                break
            if len(tag_data) != 8:
                raise error
            size = cdata.uint32_le(tag_data[:4])
            flags = cdata.uint32_le(tag_data[4:8])

            # Bits 1 and 2 bits are flags, 0-3
            # Bit 0 is read/write flag, ignored
            kind = (flags & 6) >> 1
            if kind == 3:
                raise APEBadItemError("value type must be 0, 1, or 2")

            key = value = fileobj.read(1)
            if not key:
                raise APEBadItemError
            while key[-1:] != b'\x00' and value:
                value = fileobj.read(1)
                if not value:
                    raise APEBadItemError
                key += value
            if key[-1:] == b"\x00":
                key = key[:-1]

            try:
                key = key.decode("ascii")
            except UnicodeError as err:
                reraise(APEBadItemError, err, sys.exc_info()[2])

            if not is_valid_apev2_key(key):
                raise APEBadItemError("%r is not a valid APEv2 key" % key)

            value = fileobj.read(size)
            if len(value) != size:
                raise APEBadItemError

            value = _get_value_type(kind)._new(value)

            self[key] = value

    def __getitem__(self, key):
        if not is_valid_apev2_key(key):
            raise KeyError("%r is not a valid APEv2 key" % key)

        return super(APEv2, self).__getitem__(key)

    def __delitem__(self, key):
        if not is_valid_apev2_key(key):
            raise KeyError("%r is not a valid APEv2 key" % key)

        super(APEv2, self).__delitem__(key)

    def __setitem__(self, key, value):
        """'Magic' value setter.

        This function tries to guess at what kind of value you want to
        store. If you pass in a valid UTF-8 or Unicode string, it
        treats it as a text value. If you pass in a list, it treats it
        as a list of string/Unicode values.  If you pass in a string
        that is not valid UTF-8, it assumes it is a binary value.

        Python 3: all bytes will be assumed to be a byte value, even
        if they are valid utf-8.

        If you need to force a specific type of value (e.g. binary
        data that also happens to be valid UTF-8, or an external
        reference), use the APEValue factory and set the value to the
        result of that::

            from mutagen.apev2 import APEValue, EXTERNAL
            tag['Website'] = APEValue('http://example.org', EXTERNAL)
        """

        if not is_valid_apev2_key(key):
            raise KeyError("%r is not a valid APEv2 key" % key)

        if not isinstance(value, _APEValue):
            # let's guess at the content if we're not already a value...
            if isinstance(value, str):
                # unicode? we've got to be text.
                value = APEValue(value, TEXT)
            elif isinstance(value, list):
                items = []
                for v in value:
                    if not isinstance(v, str):
                        raise TypeError("item in list not str")
                    items.append(v)

                # list? text.
                value = APEValue(u"\0".join(items), TEXT)
            else:
                value = APEValue(value, BINARY)

        super(APEv2, self).__setitem__(key, value)

    @convert_error(IOError, error)
    @loadfile(writable=True, create=True)
    def save(self, filething=None):
        """Save changes to a file.

        If no filename is given, the one most recently loaded is used.

        Tags are always written at the end of the file, and include
        a header and a footer.
        """

        fileobj = filething.fileobj

        data = _APEv2Data(fileobj)

        if data.is_at_start:
            delete_bytes(fileobj, data.end - data.start, data.start)
        elif data.start is not None:
            fileobj.seek(data.start)
            # Delete an ID3v1 tag if present, too.
            fileobj.truncate()
        fileobj.seek(0, 2)

        tags = []
        for key, value in self.items():
            # Packed format for an item:
            # 4B: Value length
            # 4B: Value type
            # Key name
            # 1B: Null
            # Key value
            value_data = value._write()
            if not isinstance(key, bytes):
                key = key.encode("utf-8")
            tag_data = bytearray()
            tag_data += struct.pack("<2I", len(value_data), value.kind << 1)
            tag_data += key + b"\0" + value_data
            tags.append(bytes(tag_data))

        # "APE tags items should be sorted ascending by size... This is
        # not a MUST, but STRONGLY recommended. Actually the items should
        # be sorted by importance/byte, but this is not feasible."
        tags.sort(key=lambda tag: (len(tag), tag))
        num_tags = len(tags)
        tags = b"".join(tags)

        header = bytearray(b"APETAGEX")
        # version, tag size, item count, flags
        header += struct.pack("<4I", 2000, len(tags) + 32, num_tags,
                              HAS_HEADER | IS_HEADER)
        header += b"\0" * 8
        fileobj.write(header)

        fileobj.write(tags)

        footer = bytearray(b"APETAGEX")
        footer += struct.pack("<4I", 2000, len(tags) + 32, num_tags,
                              HAS_HEADER)
        footer += b"\0" * 8

        fileobj.write(footer)

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def delete(self, filething=None):
        """Remove tags from a file."""

        fileobj = filething.fileobj
        data = _APEv2Data(fileobj)
        if data.start is not None and data.size is not None:
            delete_bytes(fileobj, data.end - data.start, data.start)
        self.clear()


Open = APEv2


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """delete(filething)

    Arguments:
        filething (filething)
    Raises:
        mutagen.MutagenError

    Remove tags from a file.
    """

    try:
        t = APEv2(filething)
    except APENoHeaderError:
        return
    filething.fileobj.seek(0)
    t.delete(filething)


def _get_value_type(kind):
    """Returns a _APEValue subclass or raises ValueError"""

    if kind == TEXT:
        return APETextValue
    elif kind == BINARY:
        return APEBinaryValue
    elif kind == EXTERNAL:
        return APEExtValue
    raise ValueError("unknown kind %r" % kind)


def APEValue(value, kind):
    """APEv2 tag value factory.

    Use this if you need to specify the value's type manually.  Binary
    and text data are automatically detected by APEv2.__setitem__.
    """

    try:
        type_ = _get_value_type(kind)
    except ValueError:
        raise ValueError("kind must be TEXT, BINARY, or EXTERNAL")
    else:
        return type_(value)


class _APEValue(object):

    kind: int
    value = None

    def __init__(self, value, kind=None):
        # kind kwarg is for backwards compat
        if kind is not None and kind != self.kind:
            raise ValueError
        self.value = self._validate(value)

    @classmethod
    def _new(cls, data):
        instance = cls.__new__(cls)
        instance._parse(data)
        return instance

    def _parse(self, data):
        """Sets value or raises APEBadItemError"""

        raise NotImplementedError

    def _write(self):
        """Returns bytes"""

        raise NotImplementedError

    def _validate(self, value):
        """Returns validated value or raises TypeError/ValueErrr"""

        raise NotImplementedError

    def __repr__(self):
        return "%s(%r, %d)" % (type(self).__name__, self.value, self.kind)


@total_ordering
class _APEUtf8Value(_APEValue):

    def _parse(self, data):
        try:
            self.value = data.decode("utf-8")
        except UnicodeDecodeError as e:
            reraise(APEBadItemError, e, sys.exc_info()[2])

    def _validate(self, value):
        if not isinstance(value, str):
            raise TypeError("value not str")
        return value

    def _write(self):
        return self.value.encode("utf-8")

    def __len__(self):
        return len(self.value)

    def __bytes__(self):
        return self._write()

    def __eq__(self, other):
        return self.value == other

    def __lt__(self, other):
        return self.value < other

    def __str__(self):
        return self.value


class APETextValue(_APEUtf8Value, MutableSequence):
    """An APEv2 text value.

    Text values are Unicode/UTF-8 strings. They can be accessed like
    strings (with a null separating the values), or arrays of strings.
    """

    kind = TEXT

    def __iter__(self):
        """Iterate over the strings of the value (not the characters)"""

        return iter(self.value.split(u"\0"))

    def __getitem__(self, index):
        return self.value.split(u"\0")[index]

    def __len__(self):
        return self.value.count(u"\0") + 1

    def __setitem__(self, index, value):
        if not isinstance(value, str):
            raise TypeError("value not str")

        values = list(self)
        values[index] = value
        self.value = u"\0".join(values)

    def insert(self, index, value):
        if not isinstance(value, str):
            raise TypeError("value not str")

        values = list(self)
        values.insert(index, value)
        self.value = u"\0".join(values)

    def __delitem__(self, index):
        values = list(self)
        del values[index]
        self.value = u"\0".join(values)

    def pprint(self):
        return u" / ".join(self)


@total_ordering
class APEBinaryValue(_APEValue):
    """An APEv2 binary value."""

    kind = BINARY

    def _parse(self, data):
        self.value = data

    def _write(self):
        return self.value

    def _validate(self, value):
        if not isinstance(value, bytes):
            raise TypeError("value not bytes")
        return bytes(value)

    def __len__(self):
        return len(self.value)

    def __bytes__(self):
        return self._write()

    def __eq__(self, other):
        return self.value == other

    def __lt__(self, other):
        return self.value < other

    def pprint(self):
        return u"[%d bytes]" % len(self)


class APEExtValue(_APEUtf8Value):
    """An APEv2 external value.

    External values are usually URI or IRI strings.
    """

    kind = EXTERNAL

    def pprint(self):
        return u"[External] %s" % self.value


class APEv2File(FileType):
    """APEv2File(filething)

    Arguments:
        filething (filething)

    Attributes:
        tags (`APEv2`)
    """

    class _Info(StreamInfo):
        length = 0
        bitrate = 0

        def __init__(self, fileobj):
            pass

        @staticmethod
        def pprint():
            return u"Unknown format with APEv2 tag."

    @loadfile()
    def load(self, filething):
        fileobj = filething.fileobj

        self.info = self._Info(fileobj)
        try:
            fileobj.seek(0, 0)
        except IOError as e:
            raise error(e)

        try:
            self.tags = APEv2(fileobj)
        except APENoHeaderError:
            self.tags = None

    def add_tags(self):
        if self.tags is None:
            self.tags = APEv2()
        else:
            raise error("%r already has tags: %r" % (self, self.tags))

    @staticmethod
    def score(filename, fileobj, header):
        try:
            seek_end(fileobj, 160)
            footer = fileobj.read()
        except IOError:
            return -1
        return ((b"APETAGEX" in footer) - header.startswith(b"ID3"))
