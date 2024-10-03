# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Standard MIDI File (SMF)"""

import struct
from typing import Tuple

from mutagen import StreamInfo, MutagenError
from mutagen._file import FileType
from mutagen._util import loadfile, endswith


class SMFError(MutagenError):
    pass


def _var_int(data: bytearray, offset: int = 0) -> Tuple[int, int]:
    val = 0
    while 1:
        try:
            x = data[offset]
        except IndexError:
            raise SMFError("Not enough data")
        offset += 1
        val = (val << 7) + (x & 0x7F)
        if not (x & 0x80):
            return val, offset


def _read_track(chunk):
    """Returns a list of midi events and tempo change events"""

    TEMPO, MIDI = range(2)

    # Deviations: The running status should be reset on non midi events, but
    # some files contain meta events in between.
    # TODO: Offset and time signature are not considered.

    tempos = []
    events = []

    chunk = bytearray(chunk)
    deltasum = 0
    status = 0
    off = 0
    while off < len(chunk):
        delta, off = _var_int(chunk, off)
        deltasum += delta
        event_type = chunk[off]
        off += 1
        if event_type == 0xFF:
            meta_type = chunk[off]
            off += 1
            num, off = _var_int(chunk, off)
            # TODO: support offset/time signature
            if meta_type == 0x51:
                data = chunk[off:off + num]
                if len(data) != 3:
                    raise SMFError
                tempo = struct.unpack(">I", b"\x00" + bytes(data))[0]
                tempos.append((deltasum, TEMPO, tempo))
            off += num
        elif event_type in (0xF0, 0xF7):
            val, off = _var_int(chunk, off)
            off += val
        else:
            if event_type < 0x80:
                # if < 0x80 take the type from the previous midi event
                off += 1
                event_type = status
            elif event_type < 0xF0:
                off += 2
                status = event_type
            else:
                raise SMFError("invalid event")

            if event_type >> 4 in (0xD, 0xC):
                off -= 1

            events.append((deltasum, MIDI, delta))

    return events, tempos


def _read_midi_length(fileobj):
    """Returns the duration in seconds. Can raise all kind of errors..."""

    TEMPO, MIDI = range(2)

    def read_chunk(fileobj):
        info = fileobj.read(8)
        if len(info) != 8:
            raise SMFError("truncated")
        chunklen = struct.unpack(">I", info[4:])[0]
        data = fileobj.read(chunklen)
        if len(data) != chunklen:
            raise SMFError("truncated")
        return info[:4], data

    identifier, chunk = read_chunk(fileobj)
    if identifier != b"MThd":
        raise SMFError("Not a MIDI file")

    if len(chunk) != 6:
        raise SMFError("truncated")

    format_, ntracks, tickdiv = struct.unpack(">HHH", chunk)
    if format_ > 1:
        raise SMFError("Not supported format %d" % format_)

    if tickdiv >> 15:
        # fps = (-(tickdiv >> 8)) & 0xFF
        # subres = tickdiv & 0xFF
        # never saw one of those
        raise SMFError("Not supported timing interval")

    # get a list of events and tempo changes for each track
    tracks = []
    first_tempos = None
    for tracknum in range(ntracks):
        identifier, chunk = read_chunk(fileobj)
        if identifier != b"MTrk":
            continue
        events, tempos = _read_track(chunk)

        # In case of format == 1, copy the first tempo list to all tracks
        first_tempos = first_tempos or tempos
        if format_ == 1:
            tempos = list(first_tempos)
        events += tempos
        events.sort()
        tracks.append(events)

    # calculate the duration of each track
    durations = []
    for events in tracks:
        tempo = 500000
        parts = []
        deltasum = 0
        for (dummy, type_, data) in events:
            if type_ == TEMPO:
                parts.append((deltasum, tempo))
                tempo = data
                deltasum = 0
            else:
                deltasum += data
        parts.append((deltasum, tempo))

        duration = 0
        for (deltasum, tempo) in parts:
            quarter, tpq = deltasum / float(tickdiv), tempo
            duration += (quarter * tpq)
        duration /= 10 ** 6

        durations.append(duration)

    # return the longest one
    return max(durations)


class SMFInfo(StreamInfo):
    """SMFInfo()

    Attributes:
        length (`float`): Length in seconds

    """

    def __init__(self, fileobj):
        """Raises SMFError"""

        self.length = _read_midi_length(fileobj)

    def pprint(self):
        return u"SMF, %.2f seconds" % self.length


class SMF(FileType):
    """SMF(filething)

    Standard MIDI File (SMF)

    Attributes:
        info (`SMFInfo`)
        tags: `None`
    """

    _mimes = ["audio/midi", "audio/x-midi"]

    @loadfile()
    def load(self, filething):
        try:
            self.info = SMFInfo(filething.fileobj)
        except IOError as e:
            raise SMFError(e)

    def add_tags(self):
        raise SMFError("doesn't support tags")

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()
        return header.startswith(b"MThd") and (
            endswith(filename, ".mid") or endswith(filename, ".midi"))


Open = SMF
error = SMFError

__all__ = ["SMF"]
