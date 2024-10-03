# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Split a multiplex/chained Ogg file into its component parts."""

import os
import sys

import mutagen.ogg

from ._util import SignalHandler, OptionParser


_sig = SignalHandler()


def main(argv):
    from mutagen.ogg import OggPage
    parser = OptionParser(
        usage="%prog [options] filename.ogg ...",
        description="Split Ogg logical streams using Mutagen.",
        version="Mutagen %s" % ".".join(map(str, mutagen.version))
    )

    parser.add_option(
        "--extension", dest="extension", default="ogg", metavar='ext',
        help="use this extension (default 'ogg')")
    parser.add_option(
        "--pattern", dest="pattern", default="%(base)s-%(stream)d.%(ext)s",
        metavar='pattern', help="name files using this pattern")
    parser.add_option(
        "--m3u", dest="m3u", action="store_true", default=False,
        help="generate an m3u (playlist) file")

    (options, args) = parser.parse_args(argv[1:])
    if not args:
        raise SystemExit(parser.print_help() or 1)

    format = {'ext': options.extension}
    for filename in args:
        with _sig.block():
            fileobjs = {}
            format["base"] = os.path.splitext(os.path.basename(filename))[0]
            with open(filename, "rb") as fileobj:
                if options.m3u:
                    m3u = open(format["base"] + ".m3u", "w")
                    fileobjs["m3u"] = m3u
                else:
                    m3u = None
                while True:
                    try:
                        page = OggPage(fileobj)
                    except EOFError:
                        break
                    else:
                        format["stream"] = page.serial
                        if page.serial not in fileobjs:
                            new_filename = options.pattern % format
                            new_fileobj = open(new_filename, "wb")
                            fileobjs[page.serial] = new_fileobj
                            if m3u:
                                m3u.write(new_filename + "\r\n")
                        fileobjs[page.serial].write(page.write())
                for f in fileobjs.values():
                    f.close()


def entry_point():
    _sig.init()
    return main(sys.argv)
