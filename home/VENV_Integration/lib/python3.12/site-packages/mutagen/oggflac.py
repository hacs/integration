# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Read and write Ogg FLAC comments.

This module handles FLAC files wrapped in an Ogg bitstream. The first
FLAC stream found is used. For 'naked' FLACs, see mutagen.flac.

This module is based off the specification at
http://flac.sourceforge.net/ogg_mapping.html.
"""

__all__ = ["OggFLAC", "Open", "delete"]

import struct
from io import BytesIO

from mutagen import StreamInfo
from mutagen.flac import StreamInfo as FLACStreamInfo, error as FLACError
from mutagen._vorbis import VCommentDict
from mutagen._util import loadfile, convert_error
from mutagen.ogg import OggPage, OggFileType, error as OggError


class error(OggError):
    pass


class OggFLACHeaderError(error):
    pass


class OggFLACStreamInfo(StreamInfo):
    """OggFLACStreamInfo()

    Ogg FLAC stream info.

    Attributes:
        length (`float`): File length in seconds, as a float
        channels (`float`): Number of channels
        sample_rate (`int`): Sample rate in Hz"
    """

    length = 0
    channels = 0
    sample_rate = 0

    def __init__(self, fileobj):
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"\x7FFLAC"):
            page = OggPage(fileobj)
        major, minor, self.packets, flac = struct.unpack(
            ">BBH4s", page.packets[0][5:13])
        if flac != b"fLaC":
            raise OggFLACHeaderError("invalid FLAC marker (%r)" % flac)
        elif (major, minor) != (1, 0):
            raise OggFLACHeaderError(
                "unknown mapping version: %d.%d" % (major, minor))
        self.serial = page.serial

        # Skip over the block header.
        stringobj = BytesIO(page.packets[0][17:])

        try:
            flac_info = FLACStreamInfo(stringobj)
        except FLACError as e:
            raise OggFLACHeaderError(e)

        for attr in ["min_blocksize", "max_blocksize", "sample_rate",
                     "channels", "bits_per_sample", "total_samples", "length"]:
            setattr(self, attr, getattr(flac_info, attr))

    def _post_tags(self, fileobj):
        if self.length:
            return
        page = OggPage.find_last(fileobj, self.serial, finishing=True)
        if page is None:
            raise OggFLACHeaderError
        self.length = page.position / float(self.sample_rate)

    def pprint(self):
        return u"Ogg FLAC, %.2f seconds, %d Hz" % (
            self.length, self.sample_rate)


class OggFLACVComment(VCommentDict):

    def __init__(self, fileobj, info):
        # data should be pointing at the start of an Ogg page, after
        # the first FLAC page.
        pages = []
        complete = False
        while not complete:
            page = OggPage(fileobj)
            if page.serial == info.serial:
                pages.append(page)
                complete = page.complete or (len(page.packets) > 1)
        comment = BytesIO(OggPage.to_packets(pages)[0][4:])
        super(OggFLACVComment, self).__init__(comment, framing=False)

    def _inject(self, fileobj, padding_func):
        """Write tag data into the FLAC Vorbis comment packet/page."""

        # Ogg FLAC has no convenient data marker like Vorbis, but the
        # second packet - and second page - must be the comment data.
        fileobj.seek(0)
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"\x7FFLAC"):
            page = OggPage(fileobj)

        first_page = page
        while not (page.sequence == 1 and page.serial == first_page.serial):
            page = OggPage(fileobj)

        old_pages = [page]
        while not (old_pages[-1].complete or len(old_pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == first_page.serial:
                old_pages.append(page)

        packets = OggPage.to_packets(old_pages, strict=False)

        # Set the new comment block.
        data = self.write(framing=False)
        data = packets[0][:1] + struct.pack(">I", len(data))[-3:] + data
        packets[0] = data

        new_pages = OggPage.from_packets(packets, old_pages[0].sequence)
        OggPage.replace(fileobj, old_pages, new_pages)


class OggFLAC(OggFileType):
    """OggFLAC(filething)

    An Ogg FLAC file.

    Arguments:
        filething (filething)

    Attributes:
        info (`OggFLACStreamInfo`)
        tags (`mutagen._vorbis.VCommentDict`)
    """

    _Info = OggFLACStreamInfo
    _Tags = OggFLACVComment
    _Error = OggFLACHeaderError
    _mimes = ["audio/x-oggflac"]

    info = None
    tags = None

    @staticmethod
    def score(filename, fileobj, header):
        return (header.startswith(b"OggS") * (
            (b"FLAC" in header) + (b"fLaC" in header)))


Open = OggFLAC


@convert_error(IOError, error)
@loadfile(method=False, writable=True)
def delete(filething):
    """ delete(filething)

    Arguments:
        filething (filething)
    Raises:
        mutagen.MutagenError

    Remove tags from a file.
    """

    t = OggFLAC(filething)
    filething.fileobj.seek(0)
    t.delete(filething)
