# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Pretend to be /usr/bin/id3v2 from id3lib, sort of."""

import os
import sys
import codecs
import mimetypes
import warnings

from optparse import SUPPRESS_HELP

import mutagen
import mutagen.id3
from mutagen.id3 import Encoding, PictureType

from ._util import split_escape, SignalHandler, OptionParser


VERSION = (1, 3)
_sig = SignalHandler()

global verbose
verbose = True


class ID3OptionParser(OptionParser):
    def __init__(self):
        mutagen_version = ".".join(map(str, mutagen.version))
        my_version = ".".join(map(str, VERSION))
        version = "mid3v2 %s\nUses Mutagen %s" % (my_version, mutagen_version)
        self.edits = []
        OptionParser.__init__(
            self, version=version,
            usage="%prog [OPTION] [FILE]...",
            description="Mutagen-based replacement for id3lib's id3v2.")

    def format_help(self, *args, **kwargs):
        text = OptionParser.format_help(self, *args, **kwargs)
        return text + """\
You can set the value for any ID3v2 frame by using '--' and then a frame ID.
For example:
        mid3v2 --TIT3 "Monkey!" file.mp3
would set the "Subtitle/Description" frame to "Monkey!".

Any editing operation will cause the ID3 tag to be upgraded to ID3v2.4.
"""


def list_frames(option, opt, value, parser):
    items = mutagen.id3.Frames.items()
    for name, frame in sorted(items):
        print(u"    --%s    %s" % (name, frame.__doc__.split("\n")[0]))
    raise SystemExit


def list_frames_2_2(option, opt, value, parser):
    items = mutagen.id3.Frames_2_2.items()
    items.sort()
    for name, frame in items:
        print(u"    --%s    %s" % (name, frame.__doc__.split("\n")[0]))
    raise SystemExit


def list_genres(option, opt, value, parser):
    for i, genre in enumerate(mutagen.id3.TCON.GENRES):
        print(u"%3d: %s" % (i, genre))
    raise SystemExit


def delete_tags(filenames, v1, v2):
    for filename in filenames:
        with _sig.block():
            if verbose:
                print(u"deleting ID3 tag info in", filename, file=sys.stderr)
            mutagen.id3.delete(filename, v1, v2)


def delete_frames(deletes, filenames):

    try:
        deletes = frame_from_fsnative(deletes)
    except ValueError as err:
        print(str(err), file=sys.stderr)

    frames = deletes.split(",")

    for filename in filenames:
        with _sig.block():
            if verbose:
                print("deleting %s from" % deletes, filename,
                      file=sys.stderr)
            try:
                id3 = mutagen.id3.ID3(filename)
            except mutagen.id3.ID3NoHeaderError:
                if verbose:
                    print(u"No ID3 header found; skipping.", file=sys.stderr)
            except Exception as err:
                print(str(err), file=sys.stderr)
                raise SystemExit(1)
            else:
                for frame in frames:
                    id3.delall(frame)
                id3.save()


def frame_from_fsnative(arg):
    """Takes item from argv and returns ascii native str
    or raises ValueError.
    """

    assert isinstance(arg, str)
    return arg.encode("ascii").decode("ascii")


def value_from_fsnative(arg, escape):
    """Takes an item from argv and returns a str value without
    surrogate escapes or raises ValueError.
    """

    assert isinstance(arg, str)

    if escape:
        bytes_ = os.fsencode(arg)
        # With py3.7 this has started to warn for invalid escapes, but we
        # don't control the input so ignore it.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            bytes_ = codecs.escape_decode(bytes_)[0]
        arg = os.fsdecode(bytes_)

    text = arg.encode("utf-8").decode("utf-8")
    return text


def error(*args):
    print(*args, file=sys.stderr)
    raise SystemExit(1)


def get_frame_encoding(frame_id, value):
    if frame_id == "APIC":
        # See https://github.com/beetbox/beets/issues/899#issuecomment-62437773
        return Encoding.UTF16 if value else Encoding.LATIN1
    else:
        return Encoding.UTF8


def write_files(edits, filenames, escape):
    # unescape escape sequences and decode values
    encoded_edits = []
    for frame, value in edits:
        if not value:
            continue

        try:
            frame = frame_from_fsnative(frame)
        except ValueError as err:
            print(str(err), file=sys.stderr)

        assert isinstance(frame, str)

        # strip "--"
        frame = frame[2:]

        try:
            value = value_from_fsnative(value, escape)
        except ValueError as err:
            error(u"%s: %s" % (frame, str(err)))

        assert isinstance(value, str)

        encoded_edits.append((frame, value))
    edits = encoded_edits

    # preprocess:
    #   for all [frame,value] pairs in the edits list
    #      gather values for identical frames into a list
    tmp = {}
    for frame, value in edits:
        if frame in tmp:
            tmp[frame].append(value)
        else:
            tmp[frame] = [value]
    # edits is now a dictionary of frame -> [list of values]
    edits = tmp

    # escape also enables escaping of the split separator
    if escape:
        string_split = split_escape
    else:
        string_split = lambda s, *args, **kwargs: s.split(*args, **kwargs)

    for filename in filenames:
        with _sig.block():
            if verbose:
                print(u"Writing", filename, file=sys.stderr)
            try:
                id3 = mutagen.id3.ID3(filename)
            except mutagen.id3.ID3NoHeaderError:
                if verbose:
                    print(u"No ID3 header found; creating a new tag",
                          file=sys.stderr)
                id3 = mutagen.id3.ID3()
            except Exception as err:
                print(str(err), file=sys.stderr)
                continue
            for (frame, vlist) in edits.items():
                if frame == "POPM":
                    for value in vlist:
                        values = string_split(value, ":")
                        if len(values) == 1:
                            email, rating, count = values[0], 0, 0
                        elif len(values) == 2:
                            email, rating, count = values[0], values[1], 0
                        else:
                            email, rating, count = values

                        frame = mutagen.id3.POPM(
                            email=email, rating=int(rating), count=int(count))
                        id3.add(frame)
                elif frame == "APIC":
                    for value in vlist:
                        values = string_split(value, ":")
                        # FIXME: doesn't support filenames with an invalid
                        # encoding since we have already decoded at that point
                        fn = values[0]

                        if len(values) >= 2:
                            desc = values[1]
                        else:
                            desc = u"cover"

                        if len(values) >= 3:
                            try:
                                picture_type = int(values[2])
                            except ValueError:
                                error(u"Invalid picture type: %r" % values[1])
                        else:
                            picture_type = PictureType.COVER_FRONT

                        if len(values) >= 4:
                            mime = values[3]
                        else:
                            mime = mimetypes.guess_type(fn)[0] or "image/jpeg"

                        if len(values) >= 5:
                            error("APIC: Invalid format")

                        encoding = get_frame_encoding(frame, desc)

                        try:
                            with open(fn, "rb") as h:
                                data = h.read()
                        except IOError as e:
                            error(str(e))

                        frame = mutagen.id3.APIC(encoding=encoding, mime=mime,
                            desc=desc, type=picture_type, data=data)

                        id3.add(frame)
                elif frame == "COMM":
                    for value in vlist:
                        values = string_split(value, ":")
                        if len(values) == 1:
                            value, desc, lang = values[0], "", "eng"
                        elif len(values) == 2:
                            desc, value, lang = values[0], values[1], "eng"
                        else:
                            value = ":".join(values[1:-1])
                            desc, lang = values[0], values[-1]
                        frame = mutagen.id3.COMM(
                            encoding=3, text=value, lang=lang, desc=desc)
                        id3.add(frame)
                elif frame == "USLT":
                    for value in vlist:
                        values = string_split(value, ":")
                        if len(values) == 1:
                            value, desc, lang = values[0], "", "eng"
                        elif len(values) == 2:
                            desc, value, lang = values[0], values[1], "eng"
                        else:
                            value = ":".join(values[1:-1])
                            desc, lang = values[0], values[-1]
                        frame = mutagen.id3.USLT(
                            encoding=3, text=value, lang=lang, desc=desc)
                        id3.add(frame)
                elif frame == "UFID":
                    for value in vlist:
                        values = string_split(value, ":")
                        if len(values) != 2:
                            error(u"Invalid value: %r" % values)
                        owner = values[0]
                        data = values[1].encode("utf-8")
                        frame = mutagen.id3.UFID(owner=owner, data=data)
                        id3.add(frame)
                elif frame == "TXXX":
                    for value in vlist:
                        values = string_split(value, ":", 1)
                        if len(values) == 1:
                            desc, value = "", values[0]
                        else:
                            desc, value = values[0], values[1]
                        frame = mutagen.id3.TXXX(
                            encoding=3, text=value, desc=desc)
                        id3.add(frame)
                elif frame == "WXXX":
                    for value in vlist:
                        values = string_split(value, ":", 1)
                        if len(values) == 1:
                            desc, value = "", values[0]
                        else:
                            desc, value = values[0], values[1]
                        frame = mutagen.id3.WXXX(
                            encoding=3, url=value, desc=desc)
                        id3.add(frame)
                elif issubclass(mutagen.id3.Frames[frame],
                                mutagen.id3.UrlFrame):
                    frame = mutagen.id3.Frames[frame](
                        encoding=3, url=vlist[-1])
                    id3.add(frame)
                else:
                    frame = mutagen.id3.Frames[frame](encoding=3, text=vlist)
                    id3.add(frame)
            id3.save(filename)


def list_tags(filenames):
    for filename in filenames:
        print("IDv2 tag info for", filename)
        try:
            id3 = mutagen.id3.ID3(filename, translate=False)
        except mutagen.id3.ID3NoHeaderError:
            print(u"No ID3 header found; skipping.")
        except Exception as err:
            print(str(err), file=sys.stderr)
            raise SystemExit(1)
        else:
            print(id3.pprint())


def list_tags_raw(filenames):
    for filename in filenames:
        print("Raw IDv2 tag info for", filename)
        try:
            id3 = mutagen.id3.ID3(filename, translate=False)
        except mutagen.id3.ID3NoHeaderError:
            print(u"No ID3 header found; skipping.")
        except Exception as err:
            print(str(err), file=sys.stderr)
            raise SystemExit(1)
        else:
            for frame in id3.values():
                print(str(repr(frame)))


def main(argv):
    parser = ID3OptionParser()
    parser.add_option(
        "-v", "--verbose", action="store_true", dest="verbose", default=False,
        help="be verbose")
    parser.add_option(
        "-q", "--quiet", action="store_false", dest="verbose",
        help="be quiet (the default)")
    parser.add_option(
        "-e", "--escape", action="store_true", default=False,
        help="enable interpretation of backslash escapes")
    parser.add_option(
        "-f", "--list-frames", action="callback", callback=list_frames,
        help="Display all possible frames for ID3v2.3 / ID3v2.4")
    parser.add_option(
        "--list-frames-v2.2", action="callback", callback=list_frames_2_2,
        help="Display all possible frames for ID3v2.2")
    parser.add_option(
        "-L", "--list-genres", action="callback", callback=list_genres,
        help="Lists all ID3v1 genres")
    parser.add_option(
        "-l", "--list", action="store_const", dest="action", const="list",
        help="Lists the tag(s) on the open(s)")
    parser.add_option(
        "--list-raw", action="store_const", dest="action", const="list-raw",
        help="Lists the tag(s) on the open(s) in Python format")
    parser.add_option(
        "-d", "--delete-v2", action="store_const", dest="action",
        const="delete-v2", help="Deletes ID3v2 tags")
    parser.add_option(
        "-s", "--delete-v1", action="store_const", dest="action",
        const="delete-v1", help="Deletes ID3v1 tags")
    parser.add_option(
        "-D", "--delete-all", action="store_const", dest="action",
        const="delete-v1-v2", help="Deletes ID3v1 and ID3v2 tags")
    parser.add_option(
        '--delete-frames', metavar='FID1,FID2,...', action='store',
        dest='deletes', default='', help="Delete the given frames")
    parser.add_option(
        "-C", "--convert", action="store_const", dest="action",
        const="convert",
        help="Convert tags to ID3v2.4 (any editing will do this)")

    parser.add_option(
        "-a", "--artist", metavar='"ARTIST"', action="callback",
        help="Set the artist information", type="string",
        callback=lambda *args: args[3].edits.append(("--TPE1",
                                                     args[2])))
    parser.add_option(
        "-A", "--album", metavar='"ALBUM"', action="callback",
        help="Set the album title information", type="string",
        callback=lambda *args: args[3].edits.append(("--TALB",
                                                     args[2])))
    parser.add_option(
        "-t", "--song", metavar='"SONG"', action="callback",
        help="Set the song title information", type="string",
        callback=lambda *args: args[3].edits.append(("--TIT2",
                                                     args[2])))
    parser.add_option(
        "-c", "--comment", metavar='"DESCRIPTION":"COMMENT":"LANGUAGE"',
        action="callback", help="Set the comment information", type="string",
        callback=lambda *args: args[3].edits.append(("--COMM",
                                                     args[2])))
    parser.add_option(
        "-p", "--picture",
        metavar='"FILENAME":"DESCRIPTION":"IMAGE-TYPE":"MIME-TYPE"',
        action="callback", help="Set the picture", type="string",
        callback=lambda *args: args[3].edits.append(("--APIC",
                                                     args[2])))
    parser.add_option(
        "-g", "--genre", metavar='"GENRE"', action="callback",
        help="Set the genre or genre number", type="string",
        callback=lambda *args: args[3].edits.append(("--TCON",
                                                     args[2])))
    parser.add_option(
        "-y", "--year", "--date", metavar='YYYY[-MM-DD]', action="callback",
        help="Set the year/date", type="string",
        callback=lambda *args: args[3].edits.append(("--TDRC",
                                                     args[2])))
    parser.add_option(
        "-T", "--track", metavar='"num/num"', action="callback",
        help="Set the track number/(optional) total tracks", type="string",
        callback=lambda *args: args[3].edits.append(("--TRCK",
                                                     args[2])))

    for key, frame in mutagen.id3.Frames.items():
        if (issubclass(frame, mutagen.id3.TextFrame)
                or issubclass(frame, mutagen.id3.UrlFrame)
                or issubclass(frame, mutagen.id3.POPM)
                or frame in (mutagen.id3.APIC, mutagen.id3.UFID,
                             mutagen.id3.USLT)):
            parser.add_option(
                "--" + key, action="callback", help=SUPPRESS_HELP,
                type='string', metavar="value",  # optparse blows up with this
                callback=lambda *args: args[3].edits.append(args[1:3]))

    (options, args) = parser.parse_args(argv[1:])
    global verbose
    verbose = options.verbose

    if args:
        if parser.edits or options.deletes:
            if options.deletes:
                delete_frames(options.deletes, args)
            if parser.edits:
                write_files(parser.edits, args, options.escape)
        elif options.action in [None, 'list']:
            list_tags(args)
        elif options.action == "list-raw":
            list_tags_raw(args)
        elif options.action == "convert":
            write_files([], args, options.escape)
        elif options.action.startswith("delete"):
            delete_tags(args, "v1" in options.action, "v2" in options.action)
        else:
            parser.print_help()
    else:
        parser.print_help()


def entry_point():
    _sig.init()
    return main(sys.argv)
