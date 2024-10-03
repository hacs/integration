# Copyright (C) 2005  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write FLAC Vorbis comments and stream information.

Read more about FLAC at http://flac.sourceforge.net.

FLAC supports arbitrary metadata blocks. The two most interesting ones
are the FLAC stream information block, and the Vorbis comment block;
these are also the only ones Mutagen can currently read.

This module does not handle Ogg FLAC files.

Based off documentation available at
http://flac.sourceforge.net/format.html
"""

__all__ = ["FLAC", "Open", "delete"]

import struct
from io import BytesIO
from ._vorbis import VCommentDict
import mutagen

from mutagen._util import resize_bytes, MutagenError, get_size, loadfile, \
    convert_error, bchr, endswith
from mutagen._tags import PaddingInfo
from mutagen.id3._util import BitPaddedInt
from functools import reduce


class error(MutagenError):
    pass


class FLACNoHeaderError(error):
    pass


class FLACVorbisError(ValueError, error):
    pass


def to_int_be(data):
    """Convert an arbitrarily-long string to a long using big-endian
    byte order."""
    return reduce(lambda a, b: (a << 8) + b, bytearray(data), 0)


class StrictFileObject(object):
    """Wraps a file-like object and raises an exception if the requested
    amount of data to read isn't returned."""

    def __init__(self, fileobj):
        self._fileobj = fileobj
        for m in ["close", "tell", "seek", "write", "name", "flush",
                  "truncate"]:
            if hasattr(fileobj, m):
                setattr(self, m, getattr(fileobj, m))

    def read(self, size=-1):
        data = self._fileobj.read(size)
        if size >= 0 and len(data) != size:
            raise error("file said %d bytes, read %d bytes" % (
                        size, len(data)))
        return data

    def tryread(self, *args):
        return self._fileobj.read(*args)


class MetadataBlock(object):
    """A generic block of FLAC metadata.

    This class is extended by specific used as an ancestor for more specific
    blocks, and also as a container for data blobs of unknown blocks.

    Attributes:
        data (`bytes`): raw binary data for this block
    """

    _distrust_size = False
    """For block types setting this, we don't trust the size field and
    use the size of the content instead."""

    _invalid_overflow_size = -1
    """In case the real size was bigger than what is representable by the
    24 bit size field, we save the wrong specified size here. This can
    only be set if _distrust_size is True"""

    _MAX_SIZE = 2 ** 24 - 1

    def __init__(self, data):
        """Parse the given data string or file-like as a metadata block.
        The metadata header should not be included."""
        if data is not None:
            if not isinstance(data, StrictFileObject):
                if isinstance(data, bytes):
                    data = BytesIO(data)
                elif not hasattr(data, 'read'):
                    raise TypeError(
                        "StreamInfo requires string data or a file-like")
                data = StrictFileObject(data)
            self.load(data)

    def load(self, data):
        self.data = data.read()

    def write(self):
        return self.data

    @classmethod
    def _writeblock(cls, block, is_last=False):
        """Returns the block content + header.

        Raises error.
        """

        data = bytearray()
        code = (block.code | 128) if is_last else block.code
        datum = block.write()
        size = len(datum)
        if size > cls._MAX_SIZE:
            if block._distrust_size and block._invalid_overflow_size != -1:
                # The original size of this block was (1) wrong and (2)
                # the real size doesn't allow us to save the file
                # according to the spec (too big for 24 bit uint). Instead
                # simply write back the original wrong size.. at least
                # we don't make the file more "broken" as it is.
                size = block._invalid_overflow_size
            else:
                raise error("block is too long to write")
        assert not size > cls._MAX_SIZE
        length = struct.pack(">I", size)[-3:]
        data.append(code)
        data += length
        data += datum
        return data

    @classmethod
    def _writeblocks(cls, blocks, available, cont_size, padding_func):
        """Render metadata block as a byte string."""

        # write everything except padding
        data = bytearray()
        for block in blocks:
            if isinstance(block, Padding):
                continue
            data += cls._writeblock(block)
        blockssize = len(data)

        # take the padding overhead into account. we always add one
        # to make things simple.
        padding_block = Padding()
        blockssize += len(cls._writeblock(padding_block))

        # finally add a padding block
        info = PaddingInfo(available - blockssize, cont_size)
        padding_block.length = min(info._get_padding(padding_func),
                                   cls._MAX_SIZE)
        data += cls._writeblock(padding_block, is_last=True)

        return data


class StreamInfo(MetadataBlock, mutagen.StreamInfo):
    """StreamInfo()

    FLAC stream information.

    This contains information about the audio data in the FLAC file.
    Unlike most stream information objects in Mutagen, changes to this
    one will rewritten to the file when it is saved. Unless you are
    actually changing the audio stream itself, don't change any
    attributes of this block.

    Attributes:
        min_blocksize (`int`): minimum audio block size
        max_blocksize (`int`): maximum audio block size
        sample_rate (`int`): audio sample rate in Hz
        channels (`int`): audio channels (1 for mono, 2 for stereo)
        bits_per_sample (`int`): bits per sample
        total_samples (`int`): total samples in file
        length (`float`): audio length in seconds
        bitrate (`int`): bitrate in bits per second, as an int
    """

    code = 0
    bitrate = 0

    def __eq__(self, other):
        try:
            return (self.min_blocksize == other.min_blocksize and
                    self.max_blocksize == other.max_blocksize and
                    self.sample_rate == other.sample_rate and
                    self.channels == other.channels and
                    self.bits_per_sample == other.bits_per_sample and
                    self.total_samples == other.total_samples)
        except Exception:
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        self.min_blocksize = int(to_int_be(data.read(2)))
        self.max_blocksize = int(to_int_be(data.read(2)))
        self.min_framesize = int(to_int_be(data.read(3)))
        self.max_framesize = int(to_int_be(data.read(3)))
        # first 16 bits of sample rate
        sample_first = to_int_be(data.read(2))
        # last 4 bits of sample rate, 3 of channels, first 1 of bits/sample
        sample_channels_bps = to_int_be(data.read(1))
        # last 4 of bits/sample, 36 of total samples
        bps_total = to_int_be(data.read(5))

        sample_tail = sample_channels_bps >> 4
        self.sample_rate = int((sample_first << 4) + sample_tail)
        if not self.sample_rate:
            raise error("A sample rate value of 0 is invalid")
        self.channels = int(((sample_channels_bps >> 1) & 7) + 1)
        bps_tail = bps_total >> 36
        bps_head = (sample_channels_bps & 1) << 4
        self.bits_per_sample = int(bps_head + bps_tail + 1)
        self.total_samples = bps_total & 0xFFFFFFFFF
        self.length = self.total_samples / float(self.sample_rate)

        self.md5_signature = to_int_be(data.read(16))

    def write(self):
        f = BytesIO()
        f.write(struct.pack(">I", self.min_blocksize)[-2:])
        f.write(struct.pack(">I", self.max_blocksize)[-2:])
        f.write(struct.pack(">I", self.min_framesize)[-3:])
        f.write(struct.pack(">I", self.max_framesize)[-3:])

        # first 16 bits of sample rate
        f.write(struct.pack(">I", self.sample_rate >> 4)[-2:])
        # 4 bits sample, 3 channel, 1 bps
        byte = (self.sample_rate & 0xF) << 4
        byte += ((self.channels - 1) & 7) << 1
        byte += ((self.bits_per_sample - 1) >> 4) & 1
        f.write(bchr(byte))
        # 4 bits of bps, 4 of sample count
        byte = ((self.bits_per_sample - 1) & 0xF) << 4
        byte += (self.total_samples >> 32) & 0xF
        f.write(bchr(byte))
        # last 32 of sample count
        f.write(struct.pack(">I", self.total_samples & 0xFFFFFFFF))
        # MD5 signature
        sig = self.md5_signature
        f.write(struct.pack(
            ">4I", (sig >> 96) & 0xFFFFFFFF, (sig >> 64) & 0xFFFFFFFF,
            (sig >> 32) & 0xFFFFFFFF, sig & 0xFFFFFFFF))
        return f.getvalue()

    def pprint(self):
        return u"FLAC, %.2f seconds, %d Hz" % (self.length, self.sample_rate)


class SeekPoint(tuple):
    """SeekPoint()

    A single seek point in a FLAC file.

    Placeholder seek points have first_sample of 0xFFFFFFFFFFFFFFFFL,
    and byte_offset and num_samples undefined. Seek points must be
    sorted in ascending order by first_sample number. Seek points must
    be unique by first_sample number, except for placeholder
    points. Placeholder points must occur last in the table and there
    may be any number of them.

    Attributes:
        first_sample (`int`): sample number of first sample in the target frame
        byte_offset (`int`): offset from first frame to target frame
        num_samples (`int`): number of samples in target frame
    """

    def __new__(cls, first_sample, byte_offset, num_samples):
        return super(SeekPoint, cls).__new__(
            cls, (first_sample, byte_offset, num_samples))

    def __getnewargs__(self):
        return self.first_sample, self.byte_offset, self.num_samples

    first_sample = property(lambda self: self[0])
    byte_offset = property(lambda self: self[1])
    num_samples = property(lambda self: self[2])


class SeekTable(MetadataBlock):
    """Read and write FLAC seek tables.

    Attributes:
        seekpoints: list of SeekPoint objects
    """

    __SEEKPOINT_FORMAT = '>QQH'
    __SEEKPOINT_SIZE = struct.calcsize(__SEEKPOINT_FORMAT)

    code = 3

    def __init__(self, data):
        self.seekpoints = []
        super(SeekTable, self).__init__(data)

    def __eq__(self, other):
        try:
            return (self.seekpoints == other.seekpoints)
        except (AttributeError, TypeError):
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        self.seekpoints = []
        sp = data.tryread(self.__SEEKPOINT_SIZE)
        while len(sp) == self.__SEEKPOINT_SIZE:
            self.seekpoints.append(SeekPoint(
                *struct.unpack(self.__SEEKPOINT_FORMAT, sp)))
            sp = data.tryread(self.__SEEKPOINT_SIZE)

    def write(self):
        f = BytesIO()
        for seekpoint in self.seekpoints:
            packed = struct.pack(
                self.__SEEKPOINT_FORMAT,
                seekpoint.first_sample, seekpoint.byte_offset,
                seekpoint.num_samples)
            f.write(packed)
        return f.getvalue()

    def __repr__(self):
        return "<%s seekpoints=%r>" % (type(self).__name__, self.seekpoints)


class VCFLACDict(VCommentDict):
    """VCFLACDict()

    Read and write FLAC Vorbis comments.

    FLACs don't use the framing bit at the end of the comment block.
    So this extends VCommentDict to not use the framing bit.
    """

    code = 4
    _distrust_size = True

    def load(self, data, errors='replace', framing=False):
        super(VCFLACDict, self).load(data, errors=errors, framing=framing)

    def write(self, framing=False):
        return super(VCFLACDict, self).write(framing=framing)


class CueSheetTrackIndex(tuple):
    """CueSheetTrackIndex(index_number, index_offset)

    Index for a track in a cuesheet.

    For CD-DA, an index_number of 0 corresponds to the track
    pre-gap. The first index in a track must have a number of 0 or 1,
    and subsequently, index_numbers must increase by 1. Index_numbers
    must be unique within a track. And index_offset must be evenly
    divisible by 588 samples.

    Attributes:
        index_number (`int`): index point number
        index_offset (`int`): offset in samples from track start
    """

    def __new__(cls, index_number, index_offset):
        return super(CueSheetTrackIndex, cls).__new__(
            cls, (index_number, index_offset))

    index_number = property(lambda self: self[0])
    index_offset = property(lambda self: self[1])


class CueSheetTrack(object):
    """CueSheetTrack()

    A track in a cuesheet.

    For CD-DA, track_numbers must be 1-99, or 170 for the
    lead-out. Track_numbers must be unique within a cue sheet. There
    must be at least one index in every track except the lead-out track
    which must have none.

    Attributes:
        track_number (`int`): track number
        start_offset (`int`): track offset in samples from start of FLAC stream
        isrc (`mutagen.text`): ISRC code, exactly 12 characters
        type (`int`): 0 for audio, 1 for digital data
        pre_emphasis (`bool`): true if the track is recorded with pre-emphasis
        indexes (list[CueSheetTrackIndex]):
            list of CueSheetTrackIndex objects
    """

    def __init__(self, track_number, start_offset, isrc='', type_=0,
                 pre_emphasis=False):
        self.track_number = track_number
        self.start_offset = start_offset
        self.isrc = isrc
        self.type = type_
        self.pre_emphasis = pre_emphasis
        self.indexes = []

    def __eq__(self, other):
        try:
            return (self.track_number == other.track_number and
                    self.start_offset == other.start_offset and
                    self.isrc == other.isrc and
                    self.type == other.type and
                    self.pre_emphasis == other.pre_emphasis and
                    self.indexes == other.indexes)
        except (AttributeError, TypeError):
            return False

    __hash__ = object.__hash__

    def __repr__(self):
        return (("<%s number=%r, offset=%d, isrc=%r, type=%r, "
                "pre_emphasis=%r, indexes=%r)>") %
                (type(self).__name__, self.track_number, self.start_offset,
                 self.isrc, self.type, self.pre_emphasis, self.indexes))


class CueSheet(MetadataBlock):
    """CueSheet()

    Read and write FLAC embedded cue sheets.

    Number of tracks should be from 1 to 100. There should always be
    exactly one lead-out track and that track must be the last track
    in the cue sheet.

    Attributes:
        media_catalog_number (`mutagen.text`): media catalog number in ASCII,
            up to 128 characters
        lead_in_samples (`int`): number of lead-in samples
        compact_disc (`bool`): true if the cuesheet corresponds to a
            compact disc
        tracks (list[CueSheetTrack]):
            list of CueSheetTrack objects
        lead_out (`CueSheetTrack` or `None`):
            lead-out as CueSheetTrack or None if lead-out was not found
    """

    __CUESHEET_FORMAT = '>128sQB258xB'
    __CUESHEET_SIZE = struct.calcsize(__CUESHEET_FORMAT)
    __CUESHEET_TRACK_FORMAT = '>QB12sB13xB'
    __CUESHEET_TRACK_SIZE = struct.calcsize(__CUESHEET_TRACK_FORMAT)
    __CUESHEET_TRACKINDEX_FORMAT = '>QB3x'
    __CUESHEET_TRACKINDEX_SIZE = struct.calcsize(__CUESHEET_TRACKINDEX_FORMAT)

    code = 5

    media_catalog_number = b''
    lead_in_samples = 88200
    compact_disc = True

    def __init__(self, data):
        self.tracks = []
        super(CueSheet, self).__init__(data)

    def __eq__(self, other):
        try:
            return (self.media_catalog_number == other.media_catalog_number and
                    self.lead_in_samples == other.lead_in_samples and
                    self.compact_disc == other.compact_disc and
                    self.tracks == other.tracks)
        except (AttributeError, TypeError):
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        header = data.read(self.__CUESHEET_SIZE)
        media_catalog_number, lead_in_samples, flags, num_tracks = \
            struct.unpack(self.__CUESHEET_FORMAT, header)
        self.media_catalog_number = media_catalog_number.rstrip(b'\0')
        self.lead_in_samples = lead_in_samples
        self.compact_disc = bool(flags & 0x80)
        self.tracks = []
        for i in range(num_tracks):
            track = data.read(self.__CUESHEET_TRACK_SIZE)
            start_offset, track_number, isrc_padded, flags, num_indexes = \
                struct.unpack(self.__CUESHEET_TRACK_FORMAT, track)
            isrc = isrc_padded.rstrip(b'\0')
            type_ = (flags & 0x80) >> 7
            pre_emphasis = bool(flags & 0x40)
            val = CueSheetTrack(
                track_number, start_offset, isrc, type_, pre_emphasis)
            for j in range(num_indexes):
                index = data.read(self.__CUESHEET_TRACKINDEX_SIZE)
                index_offset, index_number = struct.unpack(
                    self.__CUESHEET_TRACKINDEX_FORMAT, index)
                val.indexes.append(
                    CueSheetTrackIndex(index_number, index_offset))
            self.tracks.append(val)

    def write(self):
        f = BytesIO()
        flags = 0
        if self.compact_disc:
            flags |= 0x80
        packed = struct.pack(
            self.__CUESHEET_FORMAT, self.media_catalog_number,
            self.lead_in_samples, flags, len(self.tracks))
        f.write(packed)
        for track in self.tracks:
            track_flags = 0
            track_flags |= (track.type & 1) << 7
            if track.pre_emphasis:
                track_flags |= 0x40
            track_packed = struct.pack(
                self.__CUESHEET_TRACK_FORMAT, track.start_offset,
                track.track_number, track.isrc or b"\0", track_flags,
                len(track.indexes))
            f.write(track_packed)
            for index in track.indexes:
                index_packed = struct.pack(
                    self.__CUESHEET_TRACKINDEX_FORMAT,
                    index.index_offset, index.index_number)
                f.write(index_packed)
        return f.getvalue()

    def __repr__(self):
        return (("<%s media_catalog_number=%r, lead_in=%r, compact_disc=%r, "
                 "tracks=%r>") %
                (type(self).__name__, self.media_catalog_number,
                 self.lead_in_samples, self.compact_disc, self.tracks))


class Picture(MetadataBlock):
    """Picture()

    Read and write FLAC embed pictures.

    .. currentmodule:: mutagen

    Attributes:
        type (`id3.PictureType`): picture type
            (same as types for ID3 APIC frames)
        mime (`text`): MIME type of the picture
        desc (`text`): picture's description
        width (`int`): width in pixels
        height (`int`): height in pixels
        depth (`int`): color depth in bits-per-pixel
        colors (`int`): number of colors for indexed palettes (like GIF),
            0 for non-indexed
        data (`bytes`): picture data

    To create a picture from file (in order to add to a FLAC file),
    instantiate this object without passing anything to the constructor and
    then set the properties manually::

        p = Picture()

        with open("Folder.jpg", "rb") as f:
            pic.data = f.read()

        pic.type = id3.PictureType.COVER_FRONT
        pic.mime = u"image/jpeg"
        pic.width = 500
        pic.height = 500
        pic.depth = 16 # color depth
    """

    code = 6
    _distrust_size = True

    def __init__(self, data=None):
        self.type = 0
        self.mime = u''
        self.desc = u''
        self.width = 0
        self.height = 0
        self.depth = 0
        self.colors = 0
        self.data = b''
        super(Picture, self).__init__(data)

    def __eq__(self, other):
        try:
            return (self.type == other.type and
                    self.mime == other.mime and
                    self.desc == other.desc and
                    self.width == other.width and
                    self.height == other.height and
                    self.depth == other.depth and
                    self.colors == other.colors and
                    self.data == other.data)
        except (AttributeError, TypeError):
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        self.type, length = struct.unpack('>2I', data.read(8))
        self.mime = data.read(length).decode('UTF-8', 'replace')
        length, = struct.unpack('>I', data.read(4))
        self.desc = data.read(length).decode('UTF-8', 'replace')
        (self.width, self.height, self.depth,
         self.colors, length) = struct.unpack('>5I', data.read(20))
        self.data = data.read(length)

    def write(self):
        f = BytesIO()
        mime = self.mime.encode('UTF-8')
        f.write(struct.pack('>2I', self.type, len(mime)))
        f.write(mime)
        desc = self.desc.encode('UTF-8')
        f.write(struct.pack('>I', len(desc)))
        f.write(desc)
        f.write(struct.pack('>5I', self.width, self.height, self.depth,
                            self.colors, len(self.data)))
        f.write(self.data)
        return f.getvalue()

    def __repr__(self):
        return "<%s '%s' (%d bytes)>" % (type(self).__name__, self.mime,
                                         len(self.data))


class Padding(MetadataBlock):
    """Padding()

    Empty padding space for metadata blocks.

    To avoid rewriting the entire FLAC file when editing comments,
    metadata is often padded. Padding should occur at the end, and no
    more than one padding block should be in any FLAC file.

    Attributes:
        length (`int`): length
    """

    code = 1

    def __init__(self, data=b""):
        super(Padding, self).__init__(data)

    def load(self, data):
        self.length = len(data.read())

    def write(self):
        try:
            return b"\x00" * self.length
        # On some 64 bit platforms this won't generate a MemoryError
        # or OverflowError since you might have enough RAM, but it
        # still generates a ValueError. On other 64 bit platforms,
        # this will still succeed for extremely large values.
        # Those should never happen in the real world, and if they
        # do, writeblocks will catch it.
        except (OverflowError, ValueError, MemoryError):
            raise error("cannot write %d bytes" % self.length)

    def __eq__(self, other):
        return isinstance(other, Padding) and self.length == other.length

    __hash__ = MetadataBlock.__hash__

    def __repr__(self):
        return "<%s (%d bytes)>" % (type(self).__name__, self.length)


class FLAC(mutagen.FileType):
    """FLAC(filething)

    A FLAC audio file.

    Args:
        filething (filething)

    Attributes:
        cuesheet (`CueSheet`): if any or `None`
        seektable (`SeekTable`): if any or `None`
        pictures (list[Picture]): list of embedded pictures
        info (`StreamInfo`)
        tags (`mutagen._vorbis.VCommentDict`)
    """

    _mimes = ["audio/flac", "audio/x-flac", "application/x-flac"]

    tags = None

    METADATA_BLOCKS = [StreamInfo, Padding, None, SeekTable, VCFLACDict,
                       CueSheet, Picture]
    """Known metadata block types, indexed by ID."""

    @staticmethod
    def score(filename, fileobj, header_data):
        return (header_data.startswith(b"fLaC") +
                endswith(filename.lower(), ".flac") * 3)

    def __read_metadata_block(self, fileobj):
        byte = ord(fileobj.read(1))
        size = to_int_be(fileobj.read(3))
        code = byte & 0x7F
        last_block = bool(byte & 0x80)

        try:
            block_type = self.METADATA_BLOCKS[code] or MetadataBlock
        except IndexError:
            block_type = MetadataBlock

        if block_type._distrust_size:
            # Some jackass is writing broken Metadata block length
            # for Vorbis comment blocks, and the FLAC reference
            # implementation can parse them (mostly by accident),
            # so we have to too.  Instead of parsing the size
            # given, parse an actual Vorbis comment, leaving
            # fileobj in the right position.
            # https://github.com/quodlibet/mutagen/issues/52
            # ..same for the Picture block:
            # https://github.com/quodlibet/mutagen/issues/106
            start = fileobj.tell()
            block = block_type(fileobj)
            real_size = fileobj.tell() - start
            if real_size > MetadataBlock._MAX_SIZE:
                block._invalid_overflow_size = size
        else:
            data = fileobj.read(size)
            block = block_type(data)
        block.code = code

        if block.code == VCFLACDict.code:
            if self.tags is None:
                self.tags = block
            else:
                # https://github.com/quodlibet/mutagen/issues/377
                # Something writes multiple and metaflac doesn't care
                pass
        elif block.code == CueSheet.code:
            if self.cuesheet is None:
                self.cuesheet = block
            else:
                raise error("> 1 CueSheet block found")
        elif block.code == SeekTable.code:
            if self.seektable is None:
                self.seektable = block
            else:
                raise error("> 1 SeekTable block found")
        self.metadata_blocks.append(block)
        return not last_block

    def add_tags(self):
        """Add a Vorbis comment block to the file."""
        if self.tags is None:
            self.tags = VCFLACDict()
            self.metadata_blocks.append(self.tags)
        else:
            raise FLACVorbisError("a Vorbis comment already exists")

    add_vorbiscomment = add_tags

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def delete(self, filething=None):
        """Remove Vorbis comments from a file.

        If no filename is given, the one most recently loaded is used.
        """

        if self.tags is not None:
            temp_blocks = [
                b for b in self.metadata_blocks if b.code != VCFLACDict.code]
            self._save(filething, temp_blocks, False, padding=lambda x: 0)
            self.metadata_blocks[:] = [
                b for b in self.metadata_blocks
                if b.code != VCFLACDict.code or b is self.tags]
            self.tags.clear()

    vc = property(lambda s: s.tags, doc="Alias for tags; don't use this.")

    @convert_error(IOError, error)
    @loadfile()
    def load(self, filething):
        """Load file information from a filename."""

        fileobj = filething.fileobj

        self.metadata_blocks = []
        self.tags = None
        self.cuesheet = None
        self.seektable = None

        fileobj = StrictFileObject(fileobj)
        self.__check_header(fileobj, filething.name)
        while self.__read_metadata_block(fileobj):
            pass

        try:
            self.info.length
        except (AttributeError, IndexError):
            raise FLACNoHeaderError("Stream info block not found")

        if self.info.length:
            start = fileobj.tell()
            fileobj.seek(0, 2)
            self.info.bitrate = int(
                float(fileobj.tell() - start) * 8 / self.info.length)
        else:
            self.info.bitrate = 0

    @property
    def info(self):
        streaminfo_blocks = [
            block for block in self.metadata_blocks
            if block.code == StreamInfo.code
        ]
        return streaminfo_blocks[0]

    def add_picture(self, picture):
        """Add a new picture to the file.

        Args:
            picture (Picture)
        """
        self.metadata_blocks.append(picture)

    def clear_pictures(self):
        """Delete all pictures from the file."""

        blocks = [b for b in self.metadata_blocks if b.code != Picture.code]
        self.metadata_blocks = blocks

    @property
    def pictures(self):
        return [b for b in self.metadata_blocks if b.code == Picture.code]

    @convert_error(IOError, error)
    @loadfile(writable=True)
    def save(self, filething=None, deleteid3=False, padding=None):
        """Save metadata blocks to a file.

        Args:
            filething (filething)
            deleteid3 (bool): delete id3 tags while at it
            padding (:obj:`mutagen.PaddingFunction`)

        If no filename is given, the one most recently loaded is used.
        """
        # add new cuesheet and seektable
        if self.cuesheet and self.cuesheet not in self.metadata_blocks:
            if not isinstance(self.cuesheet, CueSheet):
                raise ValueError("Invalid cuesheet object type!")
            self.metadata_blocks.append(self.cuesheet)
        if self.seektable and self.seektable not in self.metadata_blocks:
            if not isinstance(self.seektable, SeekTable):
                raise ValueError("Invalid seektable object type!")
            self.metadata_blocks.append(self.seektable)

        self._save(filething, self.metadata_blocks, deleteid3, padding)

    def _save(self, filething, metadata_blocks, deleteid3, padding):
        f = StrictFileObject(filething.fileobj)
        header = self.__check_header(f, filething.name)
        audio_offset = self.__find_audio_offset(f)
        # "fLaC" and maybe ID3
        available = audio_offset - header

        # Delete ID3v2
        if deleteid3 and header > 4:
            available += header - 4
            header = 4

        content_size = get_size(f) - audio_offset
        assert content_size >= 0
        data = MetadataBlock._writeblocks(
            metadata_blocks, available, content_size, padding)
        data_size = len(data)

        resize_bytes(filething.fileobj, available, data_size, header)
        f.seek(header - 4)
        f.write(b"fLaC")
        f.write(data)

        # Delete ID3v1
        if deleteid3:
            try:
                f.seek(-128, 2)
            except IOError:
                pass
            else:
                if f.read(3) == b"TAG":
                    f.seek(-128, 2)
                    f.truncate()

    def __find_audio_offset(self, fileobj):
        byte = 0x00
        while not (byte & 0x80):
            byte = ord(fileobj.read(1))
            size = to_int_be(fileobj.read(3))
            try:
                block_type = self.METADATA_BLOCKS[byte & 0x7F]
            except IndexError:
                block_type = None

            if block_type and block_type._distrust_size:
                # See comments in read_metadata_block; the size can't
                # be trusted for Vorbis comment blocks and Picture block
                block_type(fileobj)
            else:
                fileobj.read(size)
        return fileobj.tell()

    def __check_header(self, fileobj, name):
        """Returns the offset of the flac block start
        (skipping id3 tags if found). The passed fileobj will be advanced to
        that offset as well.
        """

        size = 4
        header = fileobj.read(4)
        if header != b"fLaC":
            size = None
            if header[:3] == b"ID3":
                size = 14 + BitPaddedInt(fileobj.read(6)[2:])
                fileobj.seek(size - 4)
                if fileobj.read(4) != b"fLaC":
                    size = None
        if size is None:
            raise FLACNoHeaderError(
                "%r is not a valid FLAC file" % name)
        return size


Open = FLAC


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """Remove tags from a file.

    Args:
        filething (filething)
    Raises:
        mutagen.MutagenError
    """

    f = FLAC(filething)
    filething.fileobj.seek(0)
    f.delete(filething)
