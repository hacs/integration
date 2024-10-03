# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Full tag list for any given file."""

import sys

from ._util import SignalHandler, OptionParser


_sig = SignalHandler()


def main(argv):
    from mutagen import File

    parser = OptionParser(usage="usage: %prog [options] FILE [FILE...]")
    parser.add_option("--no-flac", help="Compatibility; does nothing.")
    parser.add_option("--no-mp3", help="Compatibility; does nothing.")
    parser.add_option("--no-apev2", help="Compatibility; does nothing.")

    (options, args) = parser.parse_args(argv[1:])
    if not args:
        raise SystemExit(parser.print_help() or 1)

    for filename in args:
        print(u"--", filename)
        try:
            print(u"-", File(filename).pprint())
        except AttributeError:
            print(u"- Unknown file type")
        except Exception as err:
            print(str(err))
        print(u"")


def entry_point():
    _sig.init()
    return main(sys.argv)
