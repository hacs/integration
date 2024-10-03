# Copyright 2005  Michael Urman
# Copyright 2016  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import struct
from itertools import zip_longest

from mutagen._tags import Tags
from mutagen._util import DictProxy, convert_error, read_full

from ._util import BitPaddedInt, unsynch, ID3JunkFrameError, \
    ID3EncryptionUnsupportedError, is_valid_frame_id, error, \
    ID3NoHeaderError, ID3UnsupportedVersionError, ID3SaveConfig
from ._frames import TDRC, APIC, TDOR, TIME, TIPL, TORY, TDAT, Frames_2_2, \
    TextFrame, TYER, Frame, IPLS, Frames


class ID3Header(object):

    _V24 = (2, 4, 0)
    _V23 = (2, 3, 0)
    _V22 = (2, 2, 0)
    _V11 = (1, 1)

    f_unsynch = property(lambda s: bool(s._flags & 0x80))
    f_extended = property(lambda s: bool(s._flags & 0x40))
    f_experimental = property(lambda s: bool(s._flags & 0x20))
    f_footer = property(lambda s: bool(s._flags & 0x10))

    _known_frames = None

    @property
    def known_frames(self):
        if self._known_frames is not None:
            return self._known_frames
        elif self.version >= ID3Header._V23:
            return Frames
        elif self.version >= ID3Header._V22:
            return Frames_2_2

    @convert_error(IOError, error)
    def __init__(self, fileobj=None):
        """Raises ID3NoHeaderError, ID3UnsupportedVersionError or error"""

        if fileobj is None:
            # for testing
            self._flags = 0
            return

        fn = getattr(fileobj, "name", "<unknown>")
        data = fileobj.read(10)
        if len(data) != 10:
            raise ID3NoHeaderError("%s: too small" % fn)

        id3, vmaj, vrev, flags, size = struct.unpack('>3sBBB4s', data)
        self._flags = flags
        self.size = BitPaddedInt(size) + 10
        self.version = (2, vmaj, vrev)

        if id3 != b'ID3':
            raise ID3NoHeaderError("%r doesn't start with an ID3 tag" % fn)

        if vmaj not in [2, 3, 4]:
            raise ID3UnsupportedVersionError("%r ID3v2.%d not supported"
                                             % (fn, vmaj))

        if not BitPaddedInt.has_valid_padding(size):
            raise error("Header size not synchsafe")

        if (self.version >= self._V24) and (flags & 0x0f):
            raise error(
                "%r has invalid flags %#02x" % (fn, flags))
        elif (self._V23 <= self.version < self._V24) and (flags & 0x1f):
            raise error(
                "%r has invalid flags %#02x" % (fn, flags))

        if self.f_extended:
            extsize_data = read_full(fileobj, 4)

            frame_id = extsize_data.decode("ascii", "replace")

            if frame_id in Frames:
                # Some tagger sets the extended header flag but
                # doesn't write an extended header; in this case, the
                # ID3 data follows immediately. Since no extended
                # header is going to be long enough to actually match
                # a frame, and if it's *not* a frame we're going to be
                # completely lost anyway, this seems to be the most
                # correct check.
                # https://github.com/quodlibet/quodlibet/issues/126
                self._flags ^= 0x40
                extsize = 0
                fileobj.seek(-4, 1)
            elif self.version >= self._V24:
                # "Where the 'Extended header size' is the size of the whole
                # extended header, stored as a 32 bit synchsafe integer."
                extsize = BitPaddedInt(extsize_data) - 4
                if not BitPaddedInt.has_valid_padding(extsize_data):
                    raise error(
                        "Extended header size not synchsafe")
            else:
                # "Where the 'Extended header size', currently 6 or 10 bytes,
                # excludes itself."
                extsize = struct.unpack('>L', extsize_data)[0]

            if extsize < 0:
                raise error("invalid extended header size")

            self._extdata = read_full(fileobj, extsize)


def determine_bpi(data, frames, EMPTY=b"\x00" * 10):
    """Takes id3v2.4 frame data and determines if ints or bitpaddedints
    should be used for parsing. Needed because iTunes used to write
    normal ints for frame sizes.
    """

    # count number of tags found as BitPaddedInt and how far past
    o = 0
    asbpi = 0
    while o < len(data) - 10:
        part = data[o:o + 10]
        if part == EMPTY:
            bpioff = -((len(data) - o) % 10)
            break
        name, size, flags = struct.unpack('>4sLH', part)
        size = BitPaddedInt(size)
        o += 10 + size
        try:
            name = name.decode("ascii")
        except UnicodeDecodeError:
            continue
        if name in frames:
            asbpi += 1
    else:
        bpioff = o - len(data)

    # count number of tags found as int and how far past
    o = 0
    asint = 0
    while o < len(data) - 10:
        part = data[o:o + 10]
        if part == EMPTY:
            intoff = -((len(data) - o) % 10)
            break
        name, size, flags = struct.unpack('>4sLH', part)
        o += 10 + size
        try:
            name = name.decode("ascii")
        except UnicodeDecodeError:
            continue
        if name in frames:
            asint += 1
    else:
        intoff = o - len(data)

    # if more tags as int, or equal and bpi is past and int is not
    if asint > asbpi or (asint == asbpi and (bpioff >= 1 and intoff <= 1)):
        return int
    return BitPaddedInt


class ID3Tags(DictProxy, Tags):

    __module__ = "mutagen.id3"

    def __init__(self, *args, **kwargs):
        self.unknown_frames = []
        self._unknown_v2_version = 4
        super(ID3Tags, self).__init__(*args, **kwargs)

    def _read(self, header, data):
        frames, unknown_frames, data = read_frames(
            header, data, header.known_frames)
        for frame in frames:
            self._add(frame, False)
        self.unknown_frames = unknown_frames
        self._unknown_v2_version = header.version[1]
        return data

    def _write(self, config):
        # Sort frames by 'importance', then reverse frame size and then frame
        # hash to get a stable result
        order = ["TIT2", "TPE1", "TRCK", "TALB", "TPOS", "TDRC", "TCON"]

        framedata = [
            (f, save_frame(f, config=config)) for f in self.values()]

        def get_prio(frame):
            try:
                return order.index(frame.FrameID)
            except ValueError:
                return len(order)

        def sort_key(items):
            frame, data = items
            return (get_prio(frame), len(data), frame.HashKey)

        framedata = [d for (f, d) in sorted(framedata, key=sort_key)]

        # only write unknown frames if they were loaded from the version
        # we are saving with. Theoretically we could upgrade frames
        # but some frames can be nested like CHAP, so there is a chance
        # we create a mixed frame mess.
        if self._unknown_v2_version == config.v2_version:
            framedata.extend(data for data in self.unknown_frames
                             if len(data) > 10)

        return bytearray().join(framedata)

    def getall(self, key):
        """Return all frames with a given name (the list may be empty).

        Args:
            key (text): key for frames to get

        This is best explained by examples::

            id3.getall('TIT2') == [id3['TIT2']]
            id3.getall('TTTT') == []
            id3.getall('TXXX') == [TXXX(desc='woo', text='bar'),
                                   TXXX(desc='baz', text='quuuux'), ...]

        Since this is based on the frame's HashKey, which is
        colon-separated, you can use it to do things like
        ``getall('COMM:MusicMatch')`` or ``getall('TXXX:QuodLibet:')``.
        """
        if key in self:
            return [self[key]]
        else:
            key = key + ":"
            return [v for s, v in self.items() if s.startswith(key)]

    def setall(self, key, values):
        """Delete frames of the given type and add frames in 'values'.

        Args:
            key (text): key for frames to delete
            values (list[Frame]): frames to add
        """

        self.delall(key)
        for tag in values:
            self[tag.HashKey] = tag

    def delall(self, key):
        """Delete all tags of a given kind; see getall.

        Args:
            key (text): key for frames to delete
        """

        if key in self:
            del self[key]
        else:
            key = key + ":"
            for k in list(self.keys()):
                if k.startswith(key):
                    del self[k]

    def pprint(self):
        """
        Returns:
            text: tags in a human-readable format.

        "Human-readable" is used loosely here. The format is intended
        to mirror that used for Vorbis or APEv2 output, e.g.

            ``TIT2=My Title``

        However, ID3 frames can have multiple keys:

            ``POPM=user@example.org=3 128/255``
        """

        frames = sorted(Frame.pprint(s) for s in self.values())
        return "\n".join(frames)

    def _add(self, frame, strict):
        """Add a frame.

        Args:
            frame (Frame): the frame to add
            strict (bool): if this should raise in case it can't be added
                and frames shouldn't be merged.
        """

        if not isinstance(frame, Frame):
            raise TypeError("%r not a Frame instance" % frame)

        orig_frame = frame
        frame = frame._upgrade_frame()
        if frame is None:
            if not strict:
                return
            raise TypeError(
                "Can't upgrade %r frame" % type(orig_frame).__name__)

        hash_key = frame.HashKey
        if strict or hash_key not in self:
            self[hash_key] = frame
            return

        # Try to merge frames, or change the new one. Since changing
        # the new one can lead to new conflicts, try until everything is
        # either merged or added.
        while True:
            old_frame = self[hash_key]
            new_frame = old_frame._merge_frame(frame)
            new_hash = new_frame.HashKey
            if new_hash == hash_key:
                self[hash_key] = new_frame
                break
            else:
                assert new_frame is frame
                if new_hash not in self:
                    self[new_hash] = new_frame
                    break
                hash_key = new_hash

    def loaded_frame(self, tag):
        """Deprecated; use the add method."""

        self._add(tag, True)

    def add(self, frame):
        """Add a frame to the tag."""

        # add = loaded_frame (and vice versa) break applications that
        # expect to be able to override loaded_frame (e.g. Quod Libet),
        # as does making loaded_frame call add.
        self.loaded_frame(frame)

    def __setitem__(self, key, tag):
        if not isinstance(tag, Frame):
            raise TypeError("%r not a Frame instance" % tag)
        super(ID3Tags, self).__setitem__(key, tag)

    def __update_common(self):
        """Updates done by both v23 and v24 update"""

        if "TCON" in self:
            # Get rid of "(xx)Foobr" format.
            self["TCON"].genres = self["TCON"].genres

        mimes = {"PNG": "image/png", "JPG": "image/jpeg"}
        for pic in self.getall("APIC"):
            if pic.mime in mimes:
                newpic = APIC(
                    encoding=pic.encoding, mime=mimes[pic.mime],
                    type=pic.type, desc=pic.desc, data=pic.data)
                self.add(newpic)

    def update_to_v24(self):
        """Convert older tags into an ID3v2.4 tag.

        This updates old ID3v2 frames to ID3v2.4 ones (e.g. TYER to
        TDRC). If you intend to save tags, you must call this function
        at some point; it is called by default when loading the tag.
        """

        self.__update_common()

        # TDAT, TYER, and TIME have been turned into TDRC.
        timestamps = []
        old_frames = [self.pop(n, []) for n in ["TYER", "TDAT", "TIME"]]
        for tyer, tdat, time in zip_longest(*old_frames, fillvalue=""):
            ym = re.match(r"([0-9]{4})(-[0-9]{2}-[0-9]{2})?\Z", tyer)
            dm = re.match(r"([0-9]{2})([0-9]{2})\Z", tdat)
            tm = re.match(r"([0-9]{2})([0-9]{2})\Z", time)
            timestamp = ""
            if ym:
                (year, month_day) = ym.groups()
                timestamp += "%s" % year
                if dm:
                    month_day = "-%s-%s" % dm.groups()[::-1]
                if month_day:
                    timestamp += month_day
                    if tm:
                        timestamp += "T%s:%s:00" % tm.groups()
            if timestamp:
                timestamps.append(timestamp)
        if timestamps and "TDRC" not in self:
            self.add(TDRC(encoding=0, text=timestamps))

        # TORY can be the first part of a TDOR.
        if "TORY" in self:
            f = self.pop("TORY")
            if "TDOR" not in self:
                try:
                    self.add(TDOR(encoding=0, text=str(f)))
                except UnicodeDecodeError:
                    pass

        # IPLS is now TIPL.
        if "IPLS" in self:
            f = self.pop("IPLS")
            if "TIPL" not in self:
                self.add(TIPL(encoding=f.encoding, people=f.people))

        # These can't be trivially translated to any ID3v2.4 tags, or
        # should have been removed already.
        for key in ["RVAD", "EQUA", "TRDA", "TSIZ", "TDAT", "TIME"]:
            if key in self:
                del self[key]

        # Recurse into chapters
        for f in self.getall("CHAP"):
            f.sub_frames.update_to_v24()
        for f in self.getall("CTOC"):
            f.sub_frames.update_to_v24()

    def update_to_v23(self):
        """Convert older (and newer) tags into an ID3v2.3 tag.

        This updates incompatible ID3v2 frames to ID3v2.3 ones. If you
        intend to save tags as ID3v2.3, you must call this function
        at some point.

        If you want to to go off spec and include some v2.4 frames
        in v2.3, remove them before calling this and add them back afterwards.
        """

        self.__update_common()

        # TMCL, TIPL -> TIPL
        if "TIPL" in self or "TMCL" in self:
            people = []
            if "TIPL" in self:
                f = self.pop("TIPL")
                people.extend(f.people)
            if "TMCL" in self:
                f = self.pop("TMCL")
                people.extend(f.people)
            if "IPLS" not in self:
                self.add(IPLS(encoding=f.encoding, people=people))

        # TDOR -> TORY
        if "TDOR" in self:
            f = self.pop("TDOR")
            if f.text:
                d = f.text[0]
                if d.year and "TORY" not in self:
                    self.add(TORY(encoding=f.encoding, text="%04d" % d.year))

        # TDRC -> TYER, TDAT, TIME
        if "TDRC" in self:
            f = self.pop("TDRC")
            if f.text:
                d = f.text[0]
                if d.year and "TYER" not in self:
                    self.add(TYER(encoding=f.encoding, text="%04d" % d.year))
                if d.month and d.day and "TDAT" not in self:
                    self.add(TDAT(encoding=f.encoding,
                                  text="%02d%02d" % (d.day, d.month)))
                if d.hour and d.minute and "TIME" not in self:
                    self.add(TIME(encoding=f.encoding,
                                  text="%02d%02d" % (d.hour, d.minute)))

        # New frames added in v2.4
        v24_frames = [
            'ASPI', 'EQU2', 'RVA2', 'SEEK', 'SIGN', 'TDEN', 'TDOR',
            'TDRC', 'TDRL', 'TDTG', 'TIPL', 'TMCL', 'TMOO', 'TPRO',
            'TSOA', 'TSOP', 'TSOT', 'TSST',
        ]

        for key in v24_frames:
            if key in self:
                del self[key]

        # Recurse into chapters
        for f in self.getall("CHAP"):
            f.sub_frames.update_to_v23()
        for f in self.getall("CTOC"):
            f.sub_frames.update_to_v23()

    def _copy(self):
        """Creates a shallow copy of all tags"""

        items = self.items()
        subs = {}
        for f in (self.getall("CHAP") + self.getall("CTOC")):
            subs[f.HashKey] = f.sub_frames._copy()
        return (items, subs)

    def _restore(self, value):
        """Restores the state copied with _copy()"""

        items, subs = value
        self.clear()
        for key, value in items:
            self[key] = value
            if key in subs:
                value.sub_frames._restore(subs[key])


def save_frame(frame, name=None, config=None):
    if config is None:
        config = ID3SaveConfig()

    flags = 0
    if isinstance(frame, TextFrame):
        if len(str(frame)) == 0:
            return b''

    framedata = frame._writeData(config)

    usize = len(framedata)
    if usize > 2048:
        # Disabled as this causes iTunes and other programs
        # to fail to find these frames, which usually includes
        # e.g. APIC.
        # framedata = BitPaddedInt.to_str(usize) + framedata.encode('zlib')
        # flags |= Frame.FLAG24_COMPRESS | Frame.FLAG24_DATALEN
        pass

    if config.v2_version == 4:
        bits = 7
    elif config.v2_version == 3:
        bits = 8
    else:
        raise ValueError

    datasize = BitPaddedInt.to_str(len(framedata), width=4, bits=bits)

    if name is not None:
        assert isinstance(name, bytes)
        frame_name = name
    else:
        frame_name = type(frame).__name__
        frame_name = frame_name.encode("ascii")

    header = struct.pack('>4s4sH', frame_name, datasize, flags)
    return header + framedata


def read_frames(id3, data, frames):
    """Does not error out"""

    assert id3.version >= ID3Header._V22

    result = []
    unsupported_frames = []

    if id3.version < ID3Header._V24 and id3.f_unsynch:
        try:
            data = unsynch.decode(data)
        except ValueError:
            pass

    if id3.version >= ID3Header._V23:
        if id3.version < ID3Header._V24:
            bpi = int
        else:
            bpi = determine_bpi(data, frames)

        while data:
            header = data[:10]
            try:
                name, size, flags = struct.unpack('>4sLH', header)
            except struct.error:
                break  # not enough header
            if name.strip(b'\x00') == b'':
                break

            size = bpi(size)
            framedata = data[10:10 + size]
            data = data[10 + size:]
            if size == 0:
                continue  # drop empty frames

            try:
                name = name.decode('ascii')
            except UnicodeDecodeError:
                continue

            try:
                # someone writes 2.3 frames with 2.2 names
                if name[-1] == "\x00":
                    tag = Frames_2_2[name[:-1]]
                    name = tag.__base__.__name__

                tag = frames[name]
            except KeyError:
                if is_valid_frame_id(name):
                    unsupported_frames.append(header + framedata)
            else:
                try:
                    result.append(tag._fromData(id3, flags, framedata))
                except NotImplementedError:
                    unsupported_frames.append(header + framedata)
                except ID3JunkFrameError:
                    pass
    elif id3.version >= ID3Header._V22:
        while data:
            header = data[0:6]
            try:
                name, size = struct.unpack('>3s3s', header)
            except struct.error:
                break  # not enough header
            size, = struct.unpack('>L', b'\x00' + size)
            if name.strip(b'\x00') == b'':
                break

            framedata = data[6:6 + size]
            data = data[6 + size:]
            if size == 0:
                continue  # drop empty frames

            try:
                name = name.decode('ascii')
            except UnicodeDecodeError:
                continue

            try:
                tag = frames[name]
            except KeyError:
                if is_valid_frame_id(name):
                    unsupported_frames.append(header + framedata)
            else:
                try:
                    result.append(
                        tag._fromData(id3, 0, framedata))
                except (ID3EncryptionUnsupportedError,
                        NotImplementedError):
                    unsupported_frames.append(header + framedata)
                except ID3JunkFrameError:
                    pass

    return result, unsupported_frames, data
