# Copyright 2006 Emfox Zhou <EmfoxZhou@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
ID3iconv is a Java based ID3 encoding converter, here's the Python version.
"""

import sys
import locale

import mutagen
import mutagen.id3

from ._util import SignalHandler, OptionParser


VERSION = (0, 3)
_sig = SignalHandler()


def getpreferredencoding():
    return locale.getpreferredencoding() or "utf-8"


def isascii(string):
    """Checks whether a unicode string is non-empty and contains only ASCII
    characters.
    """
    if not string:
        return False

    try:
        string.encode('ascii')
    except UnicodeEncodeError:
        return False

    return True


class ID3OptionParser(OptionParser):
    def __init__(self):
        mutagen_version = ".".join(map(str, mutagen.version))
        my_version = ".".join(map(str, VERSION))
        version = "mid3iconv %s\nUses Mutagen %s" % (
            my_version, mutagen_version)
        return OptionParser.__init__(
            self, version=version,
            usage="%prog [OPTION] [FILE]...",
            description=("Mutagen-based replacement the id3iconv utility, "
                         "which converts ID3 tags from legacy encodings "
                         "to Unicode and stores them using the ID3v2 format."))

    def format_help(self, *args, **kwargs):
        text = OptionParser.format_help(self, *args, **kwargs)
        return text + "\nFiles are updated in-place, so use --dry-run first.\n"


def update(options, filenames):
    encoding = options.encoding or getpreferredencoding()
    verbose = options.verbose
    noupdate = options.noupdate
    force_v1 = options.force_v1
    remove_v1 = options.remove_v1

    def conv(uni):
        return uni.encode('iso-8859-1').decode(encoding)

    for filename in filenames:
        with _sig.block():
            if verbose != "quiet":
                print(u"Updating", filename)

            if has_id3v1(filename) and not noupdate and force_v1:
                mutagen.id3.delete(filename, False, True)

            try:
                id3 = mutagen.id3.ID3(filename)
            except mutagen.id3.ID3NoHeaderError:
                if verbose != "quiet":
                    print(u"No ID3 header found; skipping...")
                continue
            except Exception as err:
                print(str(err), file=sys.stderr)
                continue

            for tag in filter(lambda t: t.startswith(("T", "COMM")), id3):
                frame = id3[tag]
                if isinstance(frame, mutagen.id3.TimeStampTextFrame):
                    # non-unicode fields
                    continue
                try:
                    text = frame.text
                except AttributeError:
                    continue
                try:
                    text = [conv(x) for x in frame.text]
                except (UnicodeError, LookupError):
                    continue
                else:
                    frame.text = text
                    if not text or min(map(isascii, text)):
                        frame.encoding = 3
                    else:
                        frame.encoding = 1

            if verbose == "debug":
                print(id3.pprint())

            if not noupdate:
                if remove_v1:
                    id3.save(filename, v1=False)
                else:
                    id3.save(filename)


def has_id3v1(filename):
    try:
        with open(filename, 'rb') as f:
            f.seek(-128, 2)
            return f.read(3) == b"TAG"
    except IOError:
        return False


def main(argv):
    parser = ID3OptionParser()
    parser.add_option(
        "-e", "--encoding", metavar="ENCODING", action="store",
        type="string", dest="encoding",
        help=("Specify original tag encoding (default is %s)" % (
              getpreferredencoding())))
    parser.add_option(
        "-p", "--dry-run", action="store_true", dest="noupdate",
        help="Do not actually modify files")
    parser.add_option(
        "--force-v1", action="store_true", dest="force_v1",
        help="Use an ID3v1 tag even if an ID3v2 tag is present")
    parser.add_option(
        "--remove-v1", action="store_true", dest="remove_v1",
        help="Remove v1 tag after processing the files")
    parser.add_option(
        "-q", "--quiet", action="store_const", dest="verbose",
        const="quiet", help="Only output errors")
    parser.add_option(
        "-d", "--debug", action="store_const", dest="verbose",
        const="debug", help="Output updated tags")

    for i, arg in enumerate(argv):
        if arg == "-v1":
            argv[i] = "--force-v1"
        elif arg == "-removev1":
            argv[i] = "--remove-v1"

    (options, args) = parser.parse_args(argv[1:])

    if args:
        update(options, args)
    else:
        parser.print_help()


def entry_point():
    _sig.init()
    return main(sys.argv)
