# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write Ogg bitstreams and pages.

This module reads and writes a subset of the Ogg bitstream format
version 0. It does *not* read or write Ogg Vorbis files! For that,
you should use mutagen.oggvorbis.

This implementation is based on the RFC 3533 standard found at
http://www.xiph.org/ogg/doc/rfc3533.txt.
"""

import struct
import sys
import zlib
from io import BytesIO
from typing import Type

from mutagen import FileType
from mutagen._util import cdata, resize_bytes, MutagenError, loadfile, \
    seek_end, bchr, reraise
from mutagen._file import StreamInfo
from mutagen._tags import Tags


class error(MutagenError):
    """Ogg stream parsing errors."""

    pass


class OggPage(object):
    """A single Ogg page (not necessarily a single encoded packet).

    A page is a header of 26 bytes, followed by the length of the
    data, followed by the data.

    The constructor is given a file-like object pointing to the start
    of an Ogg page. After the constructor is finished it is pointing
    to the start of the next page.

    Attributes:
        version (`int`): stream structure version (currently always 0)
        position (`int`): absolute stream position (default -1)
        serial (`int`): logical stream serial number (default 0)
        sequence (`int`): page sequence number within logical stream
            (default 0)
        offset (`int` or `None`): offset this page was read from (default None)
        complete (`bool`): if the last packet on this page is complete
            (default True)
        packets (list[bytes]): list of raw packet data (default [])

    Note that if 'complete' is false, the next page's 'continued'
    property must be true (so set both when constructing pages).

    If a file-like object is supplied to the constructor, the above
    attributes will be filled in based on it.
    """

    version = 0
    __type_flags = 0
    position = 0
    serial = 0
    sequence = 0
    offset = None
    complete = True

    def __init__(self, fileobj=None):
        """Raises error, IOError, EOFError"""

        self.packets = []

        if fileobj is None:
            return

        self.offset = fileobj.tell()

        header = fileobj.read(27)
        if len(header) == 0:
            raise EOFError

        try:
            (oggs, self.version, self.__type_flags,
             self.position, self.serial, self.sequence,
             crc, segments) = struct.unpack("<4sBBqIIiB", header)
        except struct.error:
            raise error("unable to read full header; got %r" % header)

        if oggs != b"OggS":
            raise error("read %r, expected %r, at 0x%x" % (
                oggs, b"OggS", fileobj.tell() - 27))

        if self.version != 0:
            raise error("version %r unsupported" % self.version)

        total = 0
        lacings = []
        lacing_bytes = fileobj.read(segments)
        if len(lacing_bytes) != segments:
            raise error("unable to read %r lacing bytes" % segments)
        for c in bytearray(lacing_bytes):
            total += c
            if c < 255:
                lacings.append(total)
                total = 0
        if total:
            lacings.append(total)
            self.complete = False

        self.packets = [fileobj.read(l) for l in lacings]
        if [len(p) for p in self.packets] != lacings:
            raise error("unable to read full data")

    def __eq__(self, other):
        """Two Ogg pages are the same if they write the same data."""
        try:
            return (self.write() == other.write())
        except AttributeError:
            return False

    __hash__ = object.__hash__

    def __repr__(self):
        attrs = ['version', 'position', 'serial', 'sequence', 'offset',
                 'complete', 'continued', 'first', 'last']
        values = ["%s=%r" % (attr, getattr(self, attr)) for attr in attrs]
        return "<%s %s, %d bytes in %d packets>" % (
            type(self).__name__, " ".join(values), sum(map(len, self.packets)),
            len(self.packets))

    def write(self):
        """Return a string encoding of the page header and data.

        A ValueError is raised if the data is too big to fit in a
        single page.
        """

        data = [
            struct.pack("<4sBBqIIi", b"OggS", self.version, self.__type_flags,
                        self.position, self.serial, self.sequence, 0)
        ]

        lacing_data = []
        for datum in self.packets:
            quot, rem = divmod(len(datum), 255)
            lacing_data.append(b"\xff" * quot + bchr(rem))
        lacing_data = b"".join(lacing_data)
        if not self.complete and lacing_data.endswith(b"\x00"):
            lacing_data = lacing_data[:-1]
        data.append(bchr(len(lacing_data)))
        data.append(lacing_data)
        data.extend(self.packets)
        data = b"".join(data)

        # Python's CRC is swapped relative to Ogg's needs.
        # crc32 returns uint prior to py2.6 on some platforms, so force uint
        crc = (~zlib.crc32(data.translate(cdata.bitswap), -1)) & 0xffffffff
        # Although we're using to_uint_be, this actually makes the CRC
        # a proper le integer, since Python's CRC is byteswapped.
        crc = cdata.to_uint_be(crc).translate(cdata.bitswap)
        data = data[:22] + crc + data[26:]
        return data

    @property
    def size(self) -> int:
        """Total frame size."""

        size = 27  # Initial header size
        for datum in self.packets:
            quot, rem = divmod(len(datum), 255)
            size += quot + 1
        if not self.complete and rem == 0:
            # Packet contains a multiple of 255 bytes and is not
            # terminated, so we don't have a \x00 at the end.
            size -= 1
        size += sum(map(len, self.packets))
        return size

    def __set_flag(self, bit, val):
        mask = 1 << bit
        if val:
            self.__type_flags |= mask
        else:
            self.__type_flags &= ~mask

    continued = property(
        lambda self: cdata.test_bit(self.__type_flags, 0),
        lambda self, v: self.__set_flag(0, v),
        doc="The first packet is continued from the previous page.")

    first = property(
        lambda self: cdata.test_bit(self.__type_flags, 1),
        lambda self, v: self.__set_flag(1, v),
        doc="This is the first page of a logical bitstream.")

    last = property(
        lambda self: cdata.test_bit(self.__type_flags, 2),
        lambda self, v: self.__set_flag(2, v),
        doc="This is the last page of a logical bitstream.")

    @staticmethod
    def renumber(fileobj, serial, start):
        """Renumber pages belonging to a specified logical stream.

        fileobj must be opened with mode r+b or w+b.

        Starting at page number 'start', renumber all pages belonging
        to logical stream 'serial'. Other pages will be ignored.

        fileobj must point to the start of a valid Ogg page; any
        occurring after it and part of the specified logical stream
        will be numbered. No adjustment will be made to the data in
        the pages nor the granule position; only the page number, and
        so also the CRC.

        If an error occurs (e.g. non-Ogg data is found), fileobj will
        be left pointing to the place in the stream the error occurred,
        but the invalid data will be left intact (since this function
        does not change the total file size).
        """

        number = start
        while True:
            try:
                page = OggPage(fileobj)
            except EOFError:
                break
            else:
                if page.serial != serial:
                    # Wrong stream, skip this page.
                    continue
                # Changing the number can't change the page size,
                # so seeking back based on the current size is safe.
                fileobj.seek(-page.size, 1)
            page.sequence = number
            fileobj.write(page.write())
            fileobj.seek(page.offset + page.size, 0)
            number += 1

    @staticmethod
    def to_packets(pages, strict=False):
        """Construct a list of packet data from a list of Ogg pages.

        If strict is true, the first page must start a new packet,
        and the last page must end the last packet.
        """

        serial = pages[0].serial
        sequence = pages[0].sequence
        packets = []

        if strict:
            if pages[0].continued:
                raise ValueError("first packet is continued")
            if not pages[-1].complete:
                raise ValueError("last packet does not complete")
        elif pages and pages[0].continued:
            packets.append([b""])

        for page in pages:
            if serial != page.serial:
                raise ValueError("invalid serial number in %r" % page)
            elif sequence != page.sequence:
                raise ValueError("bad sequence number in %r" % page)
            else:
                sequence += 1

            if page.packets:
                if page.continued:
                    packets[-1].append(page.packets[0])
                else:
                    packets.append([page.packets[0]])
                packets.extend([p] for p in page.packets[1:])

        return [b"".join(p) for p in packets]

    @classmethod
    def _from_packets_try_preserve(cls, packets, old_pages):
        """Like from_packets but in case the size and number of the packets
        is the same as in the given pages the layout of the pages will
        be copied (the page size and number will match).

        If the packets don't match this behaves like::

            OggPage.from_packets(packets, sequence=old_pages[0].sequence)
        """

        old_packets = cls.to_packets(old_pages)

        if [len(p) for p in packets] != [len(p) for p in old_packets]:
            # doesn't match, fall back
            return cls.from_packets(packets, old_pages[0].sequence)

        new_data = b"".join(packets)
        new_pages = []
        for old in old_pages:
            new = OggPage()
            new.sequence = old.sequence
            new.complete = old.complete
            new.continued = old.continued
            new.position = old.position
            for p in old.packets:
                data, new_data = new_data[:len(p)], new_data[len(p):]
                new.packets.append(data)
            new_pages.append(new)
        assert not new_data

        return new_pages

    @staticmethod
    def from_packets(packets, sequence=0, default_size=4096,
                     wiggle_room=2048):
        """Construct a list of Ogg pages from a list of packet data.

        The algorithm will generate pages of approximately
        default_size in size (rounded down to the nearest multiple of
        255). However, it will also allow pages to increase to
        approximately default_size + wiggle_room if allowing the
        wiggle room would finish a packet (only one packet will be
        finished in this way per page; if the next packet would fit
        into the wiggle room, it still starts on a new page).

        This method reduces packet fragmentation when packet sizes are
        slightly larger than the default page size, while still
        ensuring most pages are of the average size.

        Pages are numbered started at 'sequence'; other information is
        uninitialized.
        """

        chunk_size = (default_size // 255) * 255

        pages = []

        page = OggPage()
        page.sequence = sequence

        for packet in packets:
            page.packets.append(b"")
            while packet:
                data, packet = packet[:chunk_size], packet[chunk_size:]
                if page.size < default_size and len(page.packets) < 255:
                    page.packets[-1] += data
                else:
                    # If we've put any packet data into this page yet,
                    # we need to mark it incomplete. However, we can
                    # also have just started this packet on an already
                    # full page, in which case, just start the new
                    # page with this packet.
                    if page.packets[-1]:
                        page.complete = False
                        if len(page.packets) == 1:
                            page.position = -1
                    else:
                        page.packets.pop(-1)
                    pages.append(page)
                    page = OggPage()
                    page.continued = not pages[-1].complete
                    page.sequence = pages[-1].sequence + 1
                    page.packets.append(data)

                if len(packet) < wiggle_room:
                    page.packets[-1] += packet
                    packet = b""

        if page.packets:
            pages.append(page)

        return pages

    @classmethod
    def replace(cls, fileobj, old_pages, new_pages):
        """Replace old_pages with new_pages within fileobj.

        old_pages must have come from reading fileobj originally.
        new_pages are assumed to have the 'same' data as old_pages,
        and so the serial and sequence numbers will be copied, as will
        the flags for the first and last pages.

        fileobj will be resized and pages renumbered as necessary. As
        such, it must be opened r+b or w+b.
        """

        if not len(old_pages) or not len(new_pages):
            raise ValueError("empty pages list not allowed")

        # Number the new pages starting from the first old page.
        first = old_pages[0].sequence
        for page, seq in zip(new_pages,
                             range(first, first + len(new_pages))):
            page.sequence = seq
            page.serial = old_pages[0].serial

        new_pages[0].first = old_pages[0].first
        new_pages[0].last = old_pages[0].last
        new_pages[0].continued = old_pages[0].continued

        new_pages[-1].first = old_pages[-1].first
        new_pages[-1].last = old_pages[-1].last
        new_pages[-1].complete = old_pages[-1].complete
        if not new_pages[-1].complete and len(new_pages[-1].packets) == 1:
            new_pages[-1].position = -1

        new_data = [cls.write(p) for p in new_pages]

        # Add dummy data or merge the remaining data together so multiple
        # new pages replace an old one
        pages_diff = len(old_pages) - len(new_data)
        if pages_diff > 0:
            new_data.extend([b""] * pages_diff)
        elif pages_diff < 0:
            new_data[pages_diff - 1:] = [b"".join(new_data[pages_diff - 1:])]

        # Replace pages one by one. If the sizes match no resize happens.
        offset_adjust = 0
        new_data_end = None
        assert len(old_pages) == len(new_data)
        for old_page, data in zip(old_pages, new_data):
            offset = old_page.offset + offset_adjust
            data_size = len(data)
            resize_bytes(fileobj, old_page.size, data_size, offset)
            fileobj.seek(offset, 0)
            fileobj.write(data)
            new_data_end = offset + data_size
            offset_adjust += (data_size - old_page.size)

        # Finally, if there's any discrepancy in length, we need to
        # renumber the pages for the logical stream.
        if len(old_pages) != len(new_pages):
            fileobj.seek(new_data_end, 0)
            serial = new_pages[-1].serial
            sequence = new_pages[-1].sequence + 1
            cls.renumber(fileobj, serial, sequence)

    @staticmethod
    def find_last(fileobj, serial, finishing=False):
        """Find the last page of the stream 'serial'.

        If the file is not multiplexed this function is fast. If it is,
        it must read the whole the stream.

        This finds the last page in the actual file object, or the last
        page in the stream (with eos set), whichever comes first.

        If finishing is True it returns the last page which contains a packet
        finishing on it. If there exist pages but none with finishing packets
        returns None.

        Returns None in case no page with the serial exists.
        Raises error in case this isn't a valid ogg stream.
        Raises IOError.
        """

        # For non-muxed streams, look at the last page.
        seek_end(fileobj, 256 * 256)

        data = fileobj.read()
        try:
            index = data.rindex(b"OggS")
        except ValueError:
            raise error("unable to find final Ogg header")
        bytesobj = BytesIO(data[index:])

        def is_valid(page):
            return not finishing or page.position != -1

        best_page = None
        try:
            page = OggPage(bytesobj)
        except error:
            pass
        else:
            if page.serial == serial and is_valid(page):
                if page.last:
                    return page
                else:
                    best_page = page
            else:
                best_page = None

        # The stream is muxed, so use the slow way.
        fileobj.seek(0)
        try:
            page = OggPage(fileobj)
            while True:
                if page.serial == serial:
                    if is_valid(page):
                        best_page = page
                    if page.last:
                        break
                page = OggPage(fileobj)
            return best_page
        except error:
            return best_page
        except EOFError:
            return best_page


class OggFileType(FileType):
    """OggFileType(filething)

    An generic Ogg file.

    Arguments:
        filething (filething)
    """

    _Info: Type[StreamInfo]
    _Tags: Type[Tags]
    _Error: Type[error]
    _mimes = ["application/ogg", "application/x-ogg"]

    @loadfile()
    def load(self, filething):
        """load(filething)

        Load file information from a filename.

        Args:
            filething (filething)
        Raises:
            mutagen.MutagenError
        """

        fileobj = filething.fileobj

        try:
            self.info = self._Info(fileobj)
            self.tags = self._Tags(fileobj, self.info)
            self.info._post_tags(fileobj)
        except (error, IOError) as e:
            reraise(self._Error, e, sys.exc_info()[2])
        except EOFError:
            raise self._Error("no appropriate stream found")

    @loadfile(writable=True)
    def delete(self, filething=None):
        """delete(filething=None)

        Remove tags from a file.

        If no filename is given, the one most recently loaded is used.

        Args:
            filething (filething)
        Raises:
            mutagen.MutagenError
        """

        fileobj = filething.fileobj

        self.tags.clear()
        # TODO: we should delegate the deletion to the subclass and not through
        # _inject.
        try:
            try:
                self.tags._inject(fileobj, lambda x: 0)
            except error as e:
                reraise(self._Error, e, sys.exc_info()[2])
            except EOFError:
                raise self._Error("no appropriate stream found")
        except IOError as e:
            reraise(self._Error, e, sys.exc_info()[2])

    def add_tags(self):
        raise self._Error

    @loadfile(writable=True)
    def save(self, filething=None, padding=None):
        """save(filething=None, padding=None)

        Save a tag to a file.

        If no filename is given, the one most recently loaded is used.

        Args:
            filething (filething)
            padding (:obj:`mutagen.PaddingFunction`)
        Raises:
            mutagen.MutagenError
        """

        try:
            self.tags._inject(filething.fileobj, padding)
        except (IOError, error) as e:
            reraise(self._Error, e, sys.exc_info()[2])
        except EOFError:
            raise self._Error("no appropriate stream found")
