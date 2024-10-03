# Copyright (C) 2005  Michael Urman
#               2006  Lukas Lalinsky
#               2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import errno
from struct import error as StructError, unpack

from mutagen._util import bchr

from ._frames import TCON, TRCK, COMM, TDRC, TYER, TALB, TPE1, TIT2


def find_id3v1(fileobj, v2_version=4, known_frames=None):
    """Returns a tuple of (id3tag, offset_to_end) or (None, 0)

    offset mainly because we used to write too short tags in some cases and
    we need the offset to delete them.

    v2_version: Decides whether ID3v2.3 or ID3v2.4 tags
                should be returned. Must be 3 or 4.

    known_frames (Dict[`mutagen.text`, `Frame`]): dict mapping frame
        IDs to Frame objects
    """

    if v2_version not in (3, 4):
        raise ValueError("Only 3 and 4 possible for v2_version")

    # id3v1 is always at the end (after apev2)

    extra_read = b"APETAGEX".index(b"TAG")

    old_pos = fileobj.tell()
    try:
        fileobj.seek(-128 - extra_read, 2)
    except IOError as e:
        if e.errno == errno.EINVAL:
            # If the file is too small, might be ok since we wrote too small
            # tags at some point. let's see how the parsing goes..
            fileobj.seek(0, 0)
        else:
            raise

    data = fileobj.read(128 + extra_read)
    fileobj.seek(old_pos, 0)
    try:
        idx = data.index(b"TAG")
    except ValueError:
        return (None, 0)
    else:
        # FIXME: make use of the apev2 parser here
        # if TAG is part of APETAGEX assume this is an APEv2 tag
        try:
            ape_idx = data.index(b"APETAGEX")
        except ValueError:
            pass
        else:
            if idx == ape_idx + extra_read:
                return (None, 0)

        tag = ParseID3v1(data[idx:], v2_version, known_frames)
        if tag is None:
            return (None, 0)

        offset = idx - len(data)
        return (tag, offset)


# ID3v1.1 support.
def ParseID3v1(data, v2_version=4, known_frames=None):
    """Parse an ID3v1 tag, returning a list of ID3v2 frames

    Returns a {frame_name: frame} dict or None.

    v2_version: Decides whether ID3v2.3 or ID3v2.4 tags
                should be returned. Must be 3 or 4.

    known_frames (Dict[`mutagen.text`, `Frame`]): dict mapping frame
        IDs to Frame objects
    """

    if v2_version not in (3, 4):
        raise ValueError("Only 3 and 4 possible for v2_version")

    try:
        data = data[data.index(b"TAG"):]
    except ValueError:
        return None
    if 128 < len(data) or len(data) < 124:
        return None

    # Issue #69 - Previous versions of Mutagen, when encountering
    # out-of-spec TDRC and TYER frames of less than four characters,
    # wrote only the characters available - e.g. "1" or "" - into the
    # year field. To parse those, reduce the size of the year field.
    # Amazingly, "0s" works as a struct format string.
    unpack_fmt = "3s30s30s30s%ds29sBB" % (len(data) - 124)

    try:
        tag, title, artist, album, year, comment, track, genre = unpack(
            unpack_fmt, data)
    except StructError:
        return None

    if tag != b"TAG":
        return None

    def fix(data):
        return data.split(b"\x00")[0].strip().decode('latin1')

    title, artist, album, year, comment = map(
        fix, [title, artist, album, year, comment])

    frame_class = {
        "TIT2": TIT2,
        "TPE1": TPE1,
        "TALB": TALB,
        "TYER": TYER,
        "TDRC": TDRC,
        "COMM": COMM,
        "TRCK": TRCK,
        "TCON": TCON,
    }
    for key in frame_class:
        if known_frames is not None:
            if key in known_frames:
                frame_class[key] = known_frames[key]
            else:
                frame_class[key] = None

    frames = {}
    if title and frame_class["TIT2"]:
        frames["TIT2"] = frame_class["TIT2"](encoding=0, text=title)
    if artist and frame_class["TPE1"]:
        frames["TPE1"] = frame_class["TPE1"](encoding=0, text=[artist])
    if album and frame_class["TALB"]:
        frames["TALB"] = frame_class["TALB"](encoding=0, text=album)
    if year:
        if v2_version == 3 and frame_class["TYER"]:
            frames["TYER"] = frame_class["TYER"](encoding=0, text=year)
        elif frame_class["TDRC"]:
            frames["TDRC"] = frame_class["TDRC"](encoding=0, text=year)
    if comment and frame_class["COMM"]:
        frames["COMM"] = frame_class["COMM"](
            encoding=0, lang="eng", desc="ID3v1 Comment", text=comment)

    # Don't read a track number if it looks like the comment was
    # padded with spaces instead of nulls (thanks, WinAmp).
    if (track and frame_class["TRCK"] and
            ((track != 32) or (data[-3] == b'\x00'[0]))):
        frames["TRCK"] = TRCK(encoding=0, text=str(track))
    if genre != 255 and frame_class["TCON"]:
        frames["TCON"] = TCON(encoding=0, text=str(genre))
    return frames


def MakeID3v1(id3):
    """Return an ID3v1.1 tag string from a dict of ID3v2.4 frames."""

    v1 = {}

    for v2id, name in {"TIT2": "title", "TPE1": "artist",
                       "TALB": "album"}.items():
        if v2id in id3:
            text = id3[v2id].text[0].encode('latin1', 'replace')[:30]
        else:
            text = b""
        v1[name] = text + (b"\x00" * (30 - len(text)))

    if "COMM" in id3:
        cmnt = id3["COMM"].text[0].encode('latin1', 'replace')[:28]
    else:
        cmnt = b""
    v1["comment"] = cmnt + (b"\x00" * (29 - len(cmnt)))

    if "TRCK" in id3:
        try:
            v1["track"] = bchr(+id3["TRCK"])
        except ValueError:
            v1["track"] = b"\x00"
    else:
        v1["track"] = b"\x00"

    if "TCON" in id3:
        try:
            genre = id3["TCON"].genres[0]
        except IndexError:
            pass
        else:
            if genre in TCON.GENRES:
                v1["genre"] = bchr(TCON.GENRES.index(genre))
    if "genre" not in v1:
        v1["genre"] = b"\xff"

    if "TDRC" in id3:
        year = str(id3["TDRC"]).encode('ascii')
    elif "TYER" in id3:
        year = str(id3["TYER"]).encode('ascii')
    else:
        year = b""
    v1["year"] = (year + b"\x00\x00\x00\x00")[:4]

    return (
        b"TAG" +
        v1["title"] +
        v1["artist"] +
        v1["album"] +
        v1["year"] +
        v1["comment"] +
        v1["track"] +
        v1["genre"]
    )
