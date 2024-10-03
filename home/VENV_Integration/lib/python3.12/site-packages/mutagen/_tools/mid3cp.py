# Copyright 2014 Marcus Sundman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""A program replicating the functionality of id3lib's id3cp, using mutagen for
tag loading and saving.
"""

import sys
import os.path

import mutagen
import mutagen.id3

from ._util import SignalHandler, OptionParser


VERSION = (0, 1)
_sig = SignalHandler()


class ID3OptionParser(OptionParser):
    def __init__(self):
        mutagen_version = mutagen.version_string
        my_version = ".".join(map(str, VERSION))
        version = "mid3cp %s\nUses Mutagen %s" % (my_version, mutagen_version)
        self.disable_interspersed_args()
        OptionParser.__init__(
            self, version=version,
            usage="%prog [option(s)] <src> <dst>",
            description=("Copies ID3 tags from <src> to <dst>. Mutagen-based "
                         "replacement for id3lib's id3cp."))


def copy(src, dst, merge, write_v1=True, excluded_tags=None, verbose=False):
    """Returns 0 on success"""

    if excluded_tags is None:
        excluded_tags = []

    try:
        id3 = mutagen.id3.ID3(src, translate=False)
    except mutagen.id3.ID3NoHeaderError:
        print(u"No ID3 header found in ", src, file=sys.stderr)
        return 1
    except Exception as err:
        print(str(err), file=sys.stderr)
        return 1

    if verbose:
        print(u"File", src, u"contains:", file=sys.stderr)
        print(id3.pprint(), file=sys.stderr)

    for tag in excluded_tags:
        id3.delall(tag)

    if merge:
        try:
            target = mutagen.id3.ID3(dst, translate=False)
        except mutagen.id3.ID3NoHeaderError:
            # no need to merge
            pass
        except Exception as err:
            print(str(err), file=sys.stderr)
            return 1
        else:
            for frame in id3.values():
                target.add(frame)

            id3 = target

    # if the source is 2.3 save it as 2.3
    if id3.version < (2, 4, 0):
        id3.update_to_v23()
        v2_version = 3
    else:
        id3.update_to_v24()
        v2_version = 4

    try:
        id3.save(dst, v1=(2 if write_v1 else 0), v2_version=v2_version)
    except Exception as err:
        print(u"Error saving", dst, u":\n%s" % str(err),
              file=sys.stderr)
        return 1
    else:
        if verbose:
            print(u"Successfully saved", dst, file=sys.stderr)
        return 0


def main(argv):
    parser = ID3OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="print out saved tags", default=False)
    parser.add_option("--write-v1", action="store_true", dest="write_v1",
                      default=False, help="write id3v1 tags")
    parser.add_option("-x", "--exclude-tag", metavar="TAG", action="append",
                      dest="x", help="exclude the specified tag", default=[])
    parser.add_option("--merge", action="store_true",
                      help="Copy over frames instead of the whole ID3 tag",
                      default=False)
    (options, args) = parser.parse_args(argv[1:])

    if len(args) != 2:
        parser.print_help(file=sys.stderr)
        return 1

    (src, dst) = args

    if not os.path.isfile(src):
        print(u"File not found:", src, file=sys.stderr)
        parser.print_help(file=sys.stderr)
        return 1

    if not os.path.isfile(dst):
        print(u"File not found:", dst, file=sys.stderr)
        parser.print_help(file=sys.stderr)
        return 1

    # Strip tags - "-x FOO" adds whitespace at the beginning of the tag name
    excluded_tags = [x.strip() for x in options.x]

    with _sig.block():
        return copy(src, dst, options.merge, options.write_v1, excluded_tags,
                    options.verbose)


def entry_point():
    _sig.init()
    return main(sys.argv)
