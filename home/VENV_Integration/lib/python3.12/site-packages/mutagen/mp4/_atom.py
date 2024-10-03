# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import struct

from mutagen._util import convert_error

# This is not an exhaustive list of container atoms, but just the
# ones this module needs to peek inside.
_CONTAINERS = [b"moov", b"udta", b"trak", b"mdia", b"meta", b"ilst",
               b"stbl", b"minf", b"moof", b"traf"]
_SKIP_SIZE = {b"meta": 4}


class AtomError(Exception):
    pass


class Atom(object):
    """An individual atom.

    Attributes:
    children -- list child atoms (or None for non-container atoms)
    length -- length of this atom, including length and name
    datalength = -- length of this atom without length, name
    name -- four byte name of the atom, as a str
    offset -- location in the constructor-given fileobj of this atom

    This structure should only be used internally by Mutagen.
    """

    children = None

    @convert_error(IOError, AtomError)
    def __init__(self, fileobj, level=0):
        """May raise AtomError"""

        self.offset = fileobj.tell()
        try:
            self.length, self.name = struct.unpack(">I4s", fileobj.read(8))
        except struct.error:
            raise AtomError("truncated data")
        self._dataoffset = self.offset + 8
        if self.length == 1:
            try:
                self.length, = struct.unpack(">Q", fileobj.read(8))
            except struct.error:
                raise AtomError("truncated data")
            self._dataoffset += 8
            if self.length < 16:
                raise AtomError(
                    "64 bit atom length can only be 16 and higher")
        elif self.length == 0:
            if level != 0:
                raise AtomError(
                    "only a top-level atom can have zero length")
            # Only the last atom is supposed to have a zero-length, meaning it
            # extends to the end of file.
            fileobj.seek(0, 2)
            self.length = fileobj.tell() - self.offset
            fileobj.seek(self.offset + 8, 0)
        elif self.length < 8:
            raise AtomError(
                "atom length can only be 0, 1 or 8 and higher")

        if self.name in _CONTAINERS:
            self.children = []
            fileobj.seek(_SKIP_SIZE.get(self.name, 0), 1)
            while fileobj.tell() < self.offset + self.length:
                self.children.append(Atom(fileobj, level + 1))
        else:
            fileobj.seek(self.offset + self.length, 0)

    @property
    def datalength(self):
        return self.length - (self._dataoffset - self.offset)

    def read(self, fileobj):
        """Return if all data could be read and the atom payload"""

        fileobj.seek(self._dataoffset, 0)
        data = fileobj.read(self.datalength)
        return len(data) == self.datalength, data

    @staticmethod
    def render(name, data):
        """Render raw atom data."""
        # this raises OverflowError if Py_ssize_t can't handle the atom data
        size = len(data) + 8
        if size <= 0xFFFFFFFF:
            return struct.pack(">I4s", size, name) + data
        else:
            return struct.pack(">I4sQ", 1, name, size + 8) + data

    def findall(self, name, recursive=False):
        """Recursively find all child atoms by specified name."""
        if self.children is not None:
            for child in self.children:
                if child.name == name:
                    yield child
                if recursive:
                    for atom in child.findall(name, True):
                        yield atom

    def __getitem__(self, remaining):
        """Look up a child atom, potentially recursively.

        e.g. atom['udta', 'meta'] => <Atom name='meta' ...>
        """
        if not remaining:
            return self
        elif self.children is None:
            raise KeyError("%r is not a container" % self.name)
        for child in self.children:
            if child.name == remaining[0]:
                return child[remaining[1:]]
        else:
            raise KeyError("%r not found" % remaining[0])

    def __repr__(self):
        cls = self.__class__.__name__
        if self.children is None:
            return "<%s name=%r length=%r offset=%r>" % (
                cls, self.name, self.length, self.offset)
        else:
            children = "\n".join([" " + line for child in self.children
                                  for line in repr(child).splitlines()])
            return "<%s name=%r length=%r offset=%r\n%s>" % (
                cls, self.name, self.length, self.offset, children)


class Atoms(object):
    """Root atoms in a given file.

    Attributes:
    atoms -- a list of top-level atoms as Atom objects

    This structure should only be used internally by Mutagen.
    """

    @convert_error(IOError, AtomError)
    def __init__(self, fileobj):
        self.atoms = []
        fileobj.seek(0, 2)
        end = fileobj.tell()
        fileobj.seek(0)
        while fileobj.tell() + 8 <= end:
            self.atoms.append(Atom(fileobj))

    def path(self, *names):
        """Look up and return the complete path of an atom.

        For example, atoms.path('moov', 'udta', 'meta') will return a
        list of three atoms, corresponding to the moov, udta, and meta
        atoms.
        """

        path = [self]
        for name in names:
            path.append(path[-1][name, ])
        return path[1:]

    def __contains__(self, names):
        try:
            self[names]
        except KeyError:
            return False
        return True

    def __getitem__(self, names):
        """Look up a child atom.

        'names' may be a list of atoms (['moov', 'udta']) or a string
        specifying the complete path ('moov.udta').
        """

        if isinstance(names, bytes):
            names = names.split(b".")

        for child in self.atoms:
            if child.name == names[0]:
                return child[names[1:]]
        else:
            raise KeyError("%r not found" % names[0])

    def __repr__(self):
        return "\n".join([repr(child) for child in self.atoms])
