# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write ASF (Window Media Audio) files."""

__all__ = ["ASF", "Open"]

from mutagen import FileType, Tags, StreamInfo
from mutagen._util import resize_bytes, DictMixin, loadfile, convert_error

from ._util import error, ASFError, ASFHeaderError
from ._objects import HeaderObject, MetadataLibraryObject, MetadataObject, \
    ExtendedContentDescriptionObject, HeaderExtensionObject, \
    ContentDescriptionObject
from ._attrs import ASFGUIDAttribute, ASFWordAttribute, ASFQWordAttribute, \
    ASFDWordAttribute, ASFBoolAttribute, ASFByteArrayAttribute, \
    ASFUnicodeAttribute, ASFBaseAttribute, ASFValue


# flake8
error, ASFError, ASFHeaderError, ASFValue


class ASFInfo(StreamInfo):
    """ASFInfo()

    ASF stream information.

    Attributes:
        length (`float`): "Length in seconds
        sample_rate (`int`): Sample rate in Hz
        bitrate (`int`): Bitrate in bps
        channels (`int`): Number of channels
        codec_type (`mutagen.text`): Name of the codec type of the first
            audio stream or an empty string if unknown. Example:
            ``Windows Media Audio 9 Standard``
        codec_name (`mutagen.text`): Name and maybe version of the codec used.
            Example: ``Windows Media Audio 9.1``
        codec_description (`mutagen.text`): Further information on the codec
            used. Example: ``64 kbps, 48 kHz, stereo 2-pass CBR``
    """

    length = 0.0
    sample_rate = 0
    bitrate = 0
    channels = 0
    codec_type = u""
    codec_name = u""
    codec_description = u""

    def __init__(self):
        self.length = 0.0
        self.sample_rate = 0
        self.bitrate = 0
        self.channels = 0
        self.codec_type = u""
        self.codec_name = u""
        self.codec_description = u""

    def pprint(self):
        """Returns:
            text: a stream information text summary
        """

        s = u"ASF (%s) %d bps, %s Hz, %d channels, %.2f seconds" % (
            self.codec_type or self.codec_name or u"???", self.bitrate,
            self.sample_rate, self.channels, self.length)
        return s


class ASFTags(list, DictMixin, Tags):  # type: ignore
    """ASFTags()

    Dictionary containing ASF attributes.
    """

    def __getitem__(self, key):
        """A list of values for the key.

        This is a copy, so comment['title'].append('a title') will not
        work.

        """

        if isinstance(key, slice):
            return list.__getitem__(self, key)

        values = [value for (k, value) in self if k == key]
        if not values:
            raise KeyError(key)
        else:
            return values

    def __delitem__(self, key):
        """Delete all values associated with the key."""

        if isinstance(key, slice):
            return list.__delitem__(self, key)

        to_delete = [x for x in self if x[0] == key]
        if not to_delete:
            raise KeyError(key)
        else:
            for k in to_delete:
                self.remove(k)

    def __contains__(self, key):
        """Return true if the key has any values."""
        for k, value in self:
            if k == key:
                return True
        else:
            return False

    def __setitem__(self, key, values):
        """Set a key's value or values.

        Setting a value overwrites all old ones. The value may be a
        list of Unicode or UTF-8 strings, or a single Unicode or UTF-8
        string.
        """

        if isinstance(key, slice):
            return list.__setitem__(self, key, values)

        if not isinstance(values, list):
            values = [values]

        to_append = []
        for value in values:
            if not isinstance(value, ASFBaseAttribute):
                if isinstance(value, str):
                    value = ASFUnicodeAttribute(value)
                elif isinstance(value, bytes):
                    value = ASFByteArrayAttribute(value)
                elif isinstance(value, bool):
                    value = ASFBoolAttribute(value)
                elif isinstance(value, int):
                    value = ASFDWordAttribute(value)
                else:
                    raise TypeError("Invalid type %r" % type(value))
            to_append.append((key, value))

        try:
            del self[key]
        except KeyError:
            pass

        self.extend(to_append)

    def keys(self):
        """Return a sequence of all keys in the comment."""

        return self and set(next(zip(*self)))

    def as_dict(self):
        """Return a copy of the comment data in a real dict."""

        d = {}
        for key, value in self:
            d.setdefault(key, []).append(value)
        return d

    def pprint(self):
        """Returns a string containing all key, value pairs.

        :rtype: text
        """

        return "\n".join("%s=%s" % (k, v) for k, v in self)


UNICODE = ASFUnicodeAttribute.TYPE
"""Unicode string type"""

BYTEARRAY = ASFByteArrayAttribute.TYPE
"""Byte array type"""

BOOL = ASFBoolAttribute.TYPE
"""Bool type"""

DWORD = ASFDWordAttribute.TYPE
""""DWord type (uint32)"""

QWORD = ASFQWordAttribute.TYPE
"""QWord type (uint64)"""

WORD = ASFWordAttribute.TYPE
"""Word type (uint16)"""

GUID = ASFGUIDAttribute.TYPE
"""GUID type"""


class ASF(FileType):
    """ASF(filething)

    An ASF file, probably containing WMA or WMV.

    Arguments:
        filething (filething)

    Attributes:
        info (`ASFInfo`)
        tags (`ASFTags`)
    """

    _mimes = ["audio/x-ms-wma", "audio/x-ms-wmv", "video/x-ms-asf",
              "audio/x-wma", "video/x-wmv"]

    info = None
    tags = None

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething):
        """load(filething)

        Args:
            filething (filething)
        Raises:
            mutagen.MutagenError
        """

        fileobj = filething.fileobj

        self.info = ASFInfo()
        self.tags = ASFTags()

        self._tags = {}
        self._header = HeaderObject.parse_full(self, fileobj)

        for guid in [ContentDescriptionObject.GUID,
                     ExtendedContentDescriptionObject.GUID,
                     MetadataObject.GUID,
                     MetadataLibraryObject.GUID]:
            self.tags.extend(self._tags.pop(guid, []))

        assert not self._tags

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething=None, padding=None):
        """save(filething=None, padding=None)

        Save tag changes back to the loaded file.

        Args:
            filething (filething)
            padding (:obj:`mutagen.PaddingFunction`)
        Raises:
            mutagen.MutagenError
        """

        # Move attributes to the right objects
        self.to_content_description = {}
        self.to_extended_content_description = {}
        self.to_metadata = {}
        self.to_metadata_library = []
        for name, value in self.tags:
            library_only = (value.data_size() > 0xFFFF or value.TYPE == GUID)
            can_cont_desc = value.TYPE == UNICODE

            if library_only or value.language is not None:
                self.to_metadata_library.append((name, value))
            elif value.stream is not None:
                if name not in self.to_metadata:
                    self.to_metadata[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            elif name in ContentDescriptionObject.NAMES:
                if name not in self.to_content_description and can_cont_desc:
                    self.to_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            else:
                if name not in self.to_extended_content_description:
                    self.to_extended_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))

        # Add missing objects
        header = self._header
        if header.get_child(ContentDescriptionObject.GUID) is None:
            header.objects.append(ContentDescriptionObject())
        if header.get_child(ExtendedContentDescriptionObject.GUID) is None:
            header.objects.append(ExtendedContentDescriptionObject())
        header_ext = header.get_child(HeaderExtensionObject.GUID)
        if header_ext is None:
            header_ext = HeaderExtensionObject()
            header.objects.append(header_ext)
        if header_ext.get_child(MetadataObject.GUID) is None:
            header_ext.objects.append(MetadataObject())
        if header_ext.get_child(MetadataLibraryObject.GUID) is None:
            header_ext.objects.append(MetadataLibraryObject())

        fileobj = filething.fileobj
        # Render to file
        old_size = header.parse_size(fileobj)[0]
        data = header.render_full(self, fileobj, old_size, padding)
        size = len(data)
        resize_bytes(fileobj, old_size, size, 0)
        fileobj.seek(0)
        fileobj.write(data)

    def add_tags(self):
        raise ASFError

    @loadfile(writable=True)
    def delete(self, filething=None):
        """delete(filething=None)

        Args:
            filething (filething)
        Raises:
            mutagen.MutagenError
        """

        self.tags.clear()
        self.save(filething, padding=lambda x: 0)

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(HeaderObject.GUID) * 2

Open = ASF
