# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Utility classes for Mutagen.

You should not rely on the interfaces here being stable. They are
intended for internal use in Mutagen only.
"""

import sys
import struct
import codecs
import errno
import decimal
from io import BytesIO
from typing import Tuple, List

from collections import namedtuple
from contextlib import contextmanager
from functools import wraps
from fnmatch import fnmatchcase


_DEFAULT_BUFFER_SIZE = 2 ** 20


def endswith(text, end):
    # useful for paths which can be both, str and bytes
    if isinstance(text, str):
        if not isinstance(end, str):
            end = end.decode("ascii")
    else:
        if not isinstance(end, bytes):
            end = end.encode("ascii")
    return text.endswith(end)


def reraise(tp, value, tb):
    raise tp(value).with_traceback(tb)


def bchr(x):
    return bytes([x])


def iterbytes(b):
    return (bytes([v]) for v in b)


def intround(value: float) -> int:
    """Given a float returns a rounded int. Should give the same result on
    both Py2/3
    """

    return int(decimal.Decimal.from_float(
        value).to_integral_value(decimal.ROUND_HALF_EVEN))


def is_fileobj(fileobj) -> bool:
    """Returns:
        bool: if an argument passed ot mutagen should be treated as a
            file object
    """

    return not (isinstance(fileobj, (str, bytes)) or
                hasattr(fileobj, "__fspath__"))


def verify_fileobj(fileobj, writable=False):
    """Verifies that the passed fileobj is a file like object which
    we can use.

    Args:
        writable (bool): verify that the file object is writable as well

    Raises:
        ValueError: In case the object is not a file object that is readable
            (or writable if required) or is not opened in bytes mode.
    """

    try:
        data = fileobj.read(0)
    except Exception:
        if not hasattr(fileobj, "read"):
            raise ValueError("%r not a valid file object" % fileobj)
        raise ValueError("Can't read from file object %r" % fileobj)

    if not isinstance(data, bytes):
        raise ValueError(
            "file object %r not opened in binary mode" % fileobj)

    if writable:
        try:
            fileobj.write(b"")
        except Exception:
            if not hasattr(fileobj, "write"):
                raise ValueError("%r not a valid file object" % fileobj)
            raise ValueError("Can't write to file object %r" % fileobj)


def verify_filename(filename):
    """Checks of the passed in filename has the correct type.

    Raises:
        ValueError: if not a filename
    """

    if is_fileobj(filename):
        raise ValueError("%r not a filename" % filename)


def fileobj_name(fileobj):
    """
    Returns:
        text: A potential filename for a file object. Always a valid
            path type, but might be empty or non-existent.
    """

    value = getattr(fileobj, "name", u"")
    if not isinstance(value, (str, bytes)):
        value = str(value)
    return value


def loadfile(method=True, writable=False, create=False):
    """A decorator for functions taking a `filething` as a first argument.

    Passes a FileThing instance as the first argument to the wrapped function.

    Args:
        method (bool): If the wrapped functions is a method
        writable (bool): If a filename is passed opens the file readwrite, if
            passed a file object verifies that it is writable.
        create (bool): If passed a filename that does not exist will create
            a new empty file.
    """

    def convert_file_args(args, kwargs):
        filething = args[0] if args else None
        filename = kwargs.pop("filename", None)
        fileobj = kwargs.pop("fileobj", None)
        return filething, filename, fileobj, args[1:], kwargs

    def wrap(func):

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            filething, filename, fileobj, args, kwargs = \
                convert_file_args(args, kwargs)
            with _openfile(self, filething, filename, fileobj,
                           writable, create) as h:
                return func(self, h, *args, **kwargs)

        @wraps(func)
        def wrapper_func(*args, **kwargs):
            filething, filename, fileobj, args, kwargs = \
                convert_file_args(args, kwargs)
            with _openfile(None, filething, filename, fileobj,
                           writable, create) as h:
                return func(h, *args, **kwargs)

        return wrapper if method else wrapper_func

    return wrap


def convert_error(exc_src, exc_dest):
    """A decorator for reraising exceptions with a different type.
    Mostly useful for IOError.

    Args:
        exc_src (type): The source exception type
        exc_dest (type): The target exception type.
    """

    def wrap(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exc_dest:
                raise
            except exc_src as err:
                reraise(exc_dest, err, sys.exc_info()[2])

        return wrapper

    return wrap


FileThing = namedtuple("FileThing", ["fileobj", "filename", "name"])
"""filename is None if the source is not a filename. name is a filename which
can be used for file type detection
"""


@contextmanager
def _openfile(instance, filething, filename, fileobj, writable, create):
    """yields a FileThing

    Args:
        filething: Either a file name, a file object or None
        filename: Either a file name or None
        fileobj: Either a file object or None
        writable (bool): if the file should be opened
        create (bool): if the file should be created if it doesn't exist.
            implies writable
    Raises:
        MutagenError: In case opening the file failed
        TypeError: in case neither a file name or a file object is passed
    """

    assert not create or writable

    # to allow stacked context managers, just pass the result through
    if isinstance(filething, FileThing):
        filename = filething.filename
        fileobj = filething.fileobj
        filething = None

    if filething is not None:
        if is_fileobj(filething):
            fileobj = filething
        elif hasattr(filething, "__fspath__"):
            filename = filething.__fspath__()
            if not isinstance(filename, (bytes, str)):
                raise TypeError("expected __fspath__() to return a filename")
        else:
            filename = filething

    if instance is not None:
        # XXX: take "not writable" as loading the file..
        if not writable:
            instance.filename = filename
        elif filename is None:
            filename = getattr(instance, "filename", None)

    if fileobj is not None:
        verify_fileobj(fileobj, writable=writable)
        yield FileThing(fileobj, filename, filename or fileobj_name(fileobj))
    elif filename is not None:
        verify_filename(filename)

        inmemory_fileobj = False
        try:
            fileobj = open(filename, "rb+" if writable else "rb")
        except IOError as e:
            if writable and e.errno == errno.EOPNOTSUPP:
                # Some file systems (gvfs over fuse) don't support opening
                # files read/write. To make things still work read the whole
                # file into an in-memory file like object and write it back
                # later.
                # https://github.com/quodlibet/mutagen/issues/300
                try:
                    with open(filename, "rb") as fileobj:
                        fileobj = BytesIO(fileobj.read())
                except IOError as e2:
                    raise MutagenError(e2)
                inmemory_fileobj = True
            elif create and e.errno == errno.ENOENT:
                assert writable
                try:
                    fileobj = open(filename, "wb+")
                except IOError as e2:
                    raise MutagenError(e2)
            else:
                raise MutagenError(e)

        with fileobj as fileobj:
            yield FileThing(fileobj, filename, filename)

            if inmemory_fileobj:
                assert writable
                data = fileobj.getvalue()
                try:
                    with open(filename, "wb") as fileobj:
                        fileobj.write(data)
                except IOError as e:
                    raise MutagenError(e)
    else:
        raise TypeError("Missing filename or fileobj argument")


class MutagenError(Exception):
    """Base class for all custom exceptions in mutagen

    .. versionadded:: 1.25
    """

    __module__ = "mutagen"


def total_ordering(cls):
    """Adds all possible ordering methods to a class.

    Needs a working __eq__ and __lt__ and will supply the rest.
    """

    assert "__eq__" in cls.__dict__
    assert "__lt__" in cls.__dict__

    cls.__le__ = lambda self, other: self == other or self < other
    cls.__gt__ = lambda self, other: not (self == other or self < other)
    cls.__ge__ = lambda self, other: not self < other
    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls


def hashable(cls):
    """Makes sure the class is hashable.

    Needs a working __eq__ and __hash__ and will add a __ne__.
    """

    assert cls.__dict__["__hash__"] is not None
    assert "__eq__" in cls.__dict__

    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls


def enum(cls):
    """A decorator for creating an int enum class.

    Makes the values a subclass of the type and implements repr/str.
    The new class will be a subclass of int.

    Args:
        cls (type): The class to convert to an enum

    Returns:
        type: A new class

    ::

        @enum
        class Foo(object):
            FOO = 1
            BAR = 2
    """

    assert cls.__bases__ == (object,)

    d = dict(cls.__dict__)
    new_type = type(cls.__name__, (int,), d)
    new_type.__module__ = cls.__module__

    map_ = {}
    for key, value in d.items():
        if key.upper() == key and isinstance(value, int):
            value_instance = new_type(value)
            setattr(new_type, key, value_instance)
            map_[value] = key

    def str_(self):
        if self in map_:
            return "%s.%s" % (type(self).__name__, map_[self])
        return "%d" % int(self)

    def repr_(self):
        if self in map_:
            return "<%s.%s: %d>" % (type(self).__name__, map_[self], int(self))
        return "%d" % int(self)

    setattr(new_type, "__repr__", repr_)
    setattr(new_type, "__str__", str_)

    return new_type


def flags(cls):
    """A decorator for creating an int flags class.

    Makes the values a subclass of the type and implements repr/str.
    The new class will be a subclass of int.

    Args:
        cls (type): The class to convert to an flags

    Returns:
        type: A new class

    ::

        @flags
        class Foo(object):
            FOO = 1
            BAR = 2
    """

    assert cls.__bases__ == (object,)

    d = dict(cls.__dict__)
    new_type = type(cls.__name__, (int,), d)
    new_type.__module__ = cls.__module__

    map_ = {}
    for key, value in d.items():
        if key.upper() == key and isinstance(value, int):
            value_instance = new_type(value)
            setattr(new_type, key, value_instance)
            map_[value] = key

    def str_(self):
        value = int(self)
        matches = []
        for k, v in map_.items():
            if value & k:
                matches.append("%s.%s" % (type(self).__name__, v))
                value &= ~k
        if value != 0 or not matches:
            matches.append(str(value))

        return " | ".join(matches)

    def repr_(self):
        return "<%s: %d>" % (str(self), int(self))

    setattr(new_type, "__repr__", repr_)
    setattr(new_type, "__str__", str_)

    return new_type


@total_ordering
class DictMixin(object):
    """Implement the dict API using keys() and __*item__ methods.

    Similar to UserDict.DictMixin, this takes a class that defines
    __getitem__, __setitem__, __delitem__, and keys(), and turns it
    into a full dict-like object.

    UserDict.DictMixin is not suitable for this purpose because it's
    an old-style class.

    This class is not optimized for very large dictionaries; many
    functions have linear memory requirements. I recommend you
    override some of these functions if speed is required.
    """

    def __iter__(self):
        return iter(self.keys())

    def __has_key(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    __contains__ = __has_key

    def values(self):
        return [self[k] for k in self.keys()]

    def items(self):
        return list(zip(self.keys(), self.values()))

    def clear(self):
        for key in list(self.keys()):
            self.__delitem__(key)

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop takes at most two arguments")
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            else:
                raise
        del self[key]
        return value

    def popitem(self):
        for key in self.keys():
            break
        else:
            raise KeyError("dictionary is empty")
        return key, self.pop(key)

    def update(self, other=None, **kwargs):
        if other is None:
            self.update(kwargs)
            other = {}

        try:
            for key, value in other.items():
                self.__setitem__(key, value)
        except AttributeError:
            for key, value in other:
                self[key] = value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return repr(dict(self.items()))

    def __eq__(self, other):
        return dict(self.items()) == other

    def __lt__(self, other):
        return dict(self.items()) < other

    __hash__ = object.__hash__

    def __len__(self):
        return len(self.keys())


class DictProxy(DictMixin):
    def __init__(self, *args, **kwargs):
        self.__dict = {}
        super(DictProxy, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        return self.__dict[key]

    def __setitem__(self, key, value):
        self.__dict[key] = value

    def __delitem__(self, key):
        del self.__dict[key]

    def keys(self):
        return self.__dict.keys()


def _fill_cdata(cls):
    """Add struct pack/unpack functions"""

    funcs = {}
    for key, name in [("b", "char"), ("h", "short"),
                      ("i", "int"), ("q", "longlong")]:
        for echar, esuffix in [("<", "le"), (">", "be")]:
            esuffix = "_" + esuffix
            for unsigned in [True, False]:
                s = struct.Struct(echar + (key.upper() if unsigned else key))
                get_wrapper = lambda f: lambda *a, **k: f(*a, **k)[0]
                unpack = get_wrapper(s.unpack)
                unpack_from = get_wrapper(s.unpack_from)

                def get_unpack_from(s):
                    def unpack_from(data, offset=0):
                        return s.unpack_from(data, offset)[0], offset + s.size
                    return unpack_from

                unpack_from = get_unpack_from(s)
                pack = s.pack

                prefix = "u" if unsigned else ""
                if s.size == 1:
                    esuffix = ""
                bits = str(s.size * 8)

                if unsigned:
                    max_ = 2 ** (s.size * 8) - 1
                    min_ = 0
                else:
                    max_ = 2 ** (s.size * 8 - 1) - 1
                    min_ = - 2 ** (s.size * 8 - 1)

                funcs["%s%s_min" % (prefix, name)] = min_
                funcs["%s%s_max" % (prefix, name)] = max_
                funcs["%sint%s_min" % (prefix, bits)] = min_
                funcs["%sint%s_max" % (prefix, bits)] = max_

                funcs["%s%s%s" % (prefix, name, esuffix)] = unpack
                funcs["%sint%s%s" % (prefix, bits, esuffix)] = unpack
                funcs["%s%s%s_from" % (prefix, name, esuffix)] = unpack_from
                funcs["%sint%s%s_from" % (prefix, bits, esuffix)] = unpack_from
                funcs["to_%s%s%s" % (prefix, name, esuffix)] = pack
                funcs["to_%sint%s%s" % (prefix, bits, esuffix)] = pack

    for key, func in funcs.items():
        setattr(cls, key, staticmethod(func))


class cdata(object):
    """C character buffer to Python numeric type conversions.

    For each size/sign/endianness:
    uint32_le(data)/to_uint32_le(num)/uint32_le_from(data, offset=0)
    """

    error = struct.error

    bitswap = b''.join(
        bchr(sum(((val >> i) & 1) << (7 - i) for i in range(8)))
        for val in range(256))

    test_bit = staticmethod(lambda value, n: bool((value >> n) & 1))


_fill_cdata(cdata)


def get_size(fileobj) -> int:
    """Returns the size of the file.
    The position when passed in will be preserved if no error occurs.

    Args:
        fileobj (fileobj)
    Returns:
        int: The size of the file
    Raises:
        IOError
    """

    old_pos = fileobj.tell()
    try:
        fileobj.seek(0, 2)
        return fileobj.tell()
    finally:
        fileobj.seek(old_pos, 0)


def read_full(fileobj, size: int) -> None:
    """Like fileobj.read but raises IOError if not all requested data is
    returned.

    If you want to distinguish IOError and the EOS case, better handle
    the error yourself instead of using this.

    Args:
        fileobj (fileobj)
        size (int): amount of bytes to read
    Raises:
        IOError: In case read fails or not enough data is read
    """

    if size < 0:
        raise ValueError("size must not be negative")

    data = fileobj.read(size)
    if len(data) != size:
        raise IOError
    return data


def seek_end(fileobj, offset: int) -> None:
    """Like fileobj.seek(-offset, 2), but will not try to go beyond the start

    Needed since file objects from BytesIO will not raise IOError and
    file objects from open() will raise IOError if going to a negative offset.
    To make things easier for custom implementations, instead of allowing
    both behaviors, we just don't do it.

    Args:
        fileobj (fileobj)
        offset (int): how many bytes away from the end backwards to seek to

    Raises:
        IOError
    """

    if offset < 0:
        raise ValueError

    if get_size(fileobj) < offset:
        fileobj.seek(0, 0)
    else:
        fileobj.seek(-offset, 2)


def resize_file(fobj, diff: int, BUFFER_SIZE: int = _DEFAULT_BUFFER_SIZE) -> None:
    """Resize a file by `diff`.

    New space will be filled with zeros.

    Args:
        fobj (fileobj)
        diff (int): amount of size to change
    Raises:
        IOError
    """

    fobj.seek(0, 2)
    filesize = fobj.tell()

    if diff < 0:
        if filesize + diff < 0:
            raise ValueError
        # truncate flushes internally
        fobj.truncate(filesize + diff)
    elif diff > 0:
        try:
            while diff:
                addsize = min(BUFFER_SIZE, diff)
                fobj.write(b"\x00" * addsize)
                diff -= addsize
            fobj.flush()
        except IOError as e:
            if e.errno == errno.ENOSPC:
                # To reduce the chance of corrupt files in case of missing
                # space try to revert the file expansion back. Of course
                # in reality every in-file-write can also fail due to COW etc.
                # Note: IOError gets also raised in flush() due to buffering
                fobj.truncate(filesize)
            raise


def move_bytes(fobj, dest: int, src: int, count: int,
               BUFFER_SIZE: int = _DEFAULT_BUFFER_SIZE) -> None:
    """Moves data around using read()/write().

    Args:
        fileobj (fileobj)
        dest (int): The destination offset
        src (int): The source offset
        count (int) The amount of data to move
    Raises:
        IOError: In case an operation on the fileobj fails
        ValueError: In case invalid parameters were given
    """

    if dest < 0 or src < 0 or count < 0:
        raise ValueError

    fobj.seek(0, 2)
    filesize = fobj.tell()

    if max(dest, src) + count > filesize:
        raise ValueError("area outside of file")

    if src > dest:
        moved = 0
        while count - moved:
            this_move = min(BUFFER_SIZE, count - moved)
            fobj.seek(src + moved)
            buf = fobj.read(this_move)
            fobj.seek(dest + moved)
            fobj.write(buf)
            moved += this_move
        fobj.flush()
    else:
        while count:
            this_move = min(BUFFER_SIZE, count)
            fobj.seek(src + count - this_move)
            buf = fobj.read(this_move)
            fobj.seek(count + dest - this_move)
            fobj.write(buf)
            count -= this_move
        fobj.flush()


def insert_bytes(fobj, size: int, offset: int,
                 BUFFER_SIZE: int = _DEFAULT_BUFFER_SIZE) -> None:
    """Insert size bytes of empty space starting at offset.

    fobj must be an open file object, open rb+ or
    equivalent.

    Args:
        fobj (fileobj)
        size (int): The amount of space to insert
        offset (int): The offset at which to insert the space
    Raises:
        IOError
    """

    if size < 0 or offset < 0:
        raise ValueError

    fobj.seek(0, 2)
    filesize = fobj.tell()
    movesize = filesize - offset

    if movesize < 0:
        raise ValueError

    resize_file(fobj, size, BUFFER_SIZE)
    move_bytes(fobj, offset + size, offset, movesize, BUFFER_SIZE)


def delete_bytes(fobj, size: int, offset: int,
                 BUFFER_SIZE: int = _DEFAULT_BUFFER_SIZE) -> None:
    """Delete size bytes of empty space starting at offset.

    fobj must be an open file object, open rb+ or
    equivalent.

    Args:
        fobj (fileobj)
        size (int): The amount of space to delete
        offset (int): The start of the space to delete
    Raises:
        IOError
    """

    if size < 0 or offset < 0:
        raise ValueError

    fobj.seek(0, 2)
    filesize = fobj.tell()
    movesize = filesize - offset - size

    if movesize < 0:
        raise ValueError

    move_bytes(fobj, offset, offset + size, movesize, BUFFER_SIZE)
    resize_file(fobj, -size, BUFFER_SIZE)


def resize_bytes(fobj, old_size: int, new_size: int, offset: int) -> None:
    """Resize an area in a file adding and deleting at the end of it.
    Does nothing if no resizing is needed.

    Args:
        fobj (fileobj)
        old_size (int): The area starting at offset
        new_size (int): The new size of the area
        offset (int): The start of the area
    Raises:
        IOError
    """

    if new_size < old_size:
        delete_size = old_size - new_size
        delete_at = offset + new_size
        delete_bytes(fobj, delete_size, delete_at)
    elif new_size > old_size:
        insert_size = new_size - old_size
        insert_at = offset + old_size
        insert_bytes(fobj, insert_size, insert_at)


def dict_match(d, key, default=None):
    """Like __getitem__ but works as if the keys() are all filename patterns.
    Returns the value of any dict key that matches the passed key.

    Args:
        d (dict): A dict with filename patterns as keys
        key (str): A key potentially matching any of the keys
        default (object): The object to return if no pattern matched the
            passed in key
    Returns:
        object: The dict value where the dict key matched the passed in key.
            Or default if there was no match.
    """

    if key in d and "[" not in key:
        return d[key]
    else:
        for pattern, value in d.items():
            if fnmatchcase(key, pattern):
                return value
    return default


def encode_endian(text: str, encoding: str,
                  errors: str = "strict", le: bool = True) -> bytes:
    """Like text.encode(encoding) but always returns little endian/big endian
    BOMs instead of the system one.

    Args:
        text (text)
        encoding (str)
        errors (str)
        le (boolean): if little endian
    Returns:
        bytes
    Raises:
        UnicodeEncodeError
        LookupError
    """

    encoding = codecs.lookup(encoding).name

    if encoding == "utf-16":
        if le:
            return codecs.BOM_UTF16_LE + text.encode("utf-16-le", errors)
        else:
            return codecs.BOM_UTF16_BE + text.encode("utf-16-be", errors)
    elif encoding == "utf-32":
        if le:
            return codecs.BOM_UTF32_LE + text.encode("utf-32-le", errors)
        else:
            return codecs.BOM_UTF32_BE + text.encode("utf-32-be", errors)
    else:
        return text.encode(encoding, errors)


def decode_terminated(data: bytes, encoding: str,
                      strict: bool = True) -> Tuple[str, bytes]:
    """Returns the decoded data until the first NULL terminator
    and all data after it.

    Args:
        data (bytes): data to decode
        encoding (str): The codec to use
        strict (bool): If True will raise ValueError in case no NULL is found
            but the available data decoded successfully.
    Returns:
        Tuple[`text`, `bytes`]: A tuple containing the decoded text and the
            remaining data after the found NULL termination.

    Raises:
        UnicodeError: In case the data can't be decoded.
        LookupError:In case the encoding is not found.
        ValueError: In case the data isn't null terminated (even if it is
            encoded correctly) except if strict is False, then the decoded
            string will be returned anyway.
    """

    codec_info = codecs.lookup(encoding)

    # normalize encoding name so we can compare by name
    encoding = codec_info.name

    # fast path
    if encoding in ("utf-8", "iso8859-1"):
        index = data.find(b"\x00")
        if index == -1:
            # make sure we raise UnicodeError first, like in the slow path
            res = data.decode(encoding), b""
            if strict:
                raise ValueError("not null terminated")
            else:
                return res
        return data[:index].decode(encoding), data[index + 1:]

    # slow path
    decoder = codec_info.incrementaldecoder()
    r: List[str] = []
    for i, b in enumerate(iterbytes(data)):
        c = decoder.decode(b)
        if c == u"\x00":
            return u"".join(r), data[i + 1:]
        r.append(c)
    else:
        # make sure the decoder is finished
        r.append(decoder.decode(b"", True))
        if strict:
            raise ValueError("not null terminated")
        return u"".join(r), b""


class BitReaderError(Exception):
    pass


class BitReader(object):

    def __init__(self, fileobj):
        self._fileobj = fileobj
        self._buffer = 0
        self._bits = 0
        self._pos = fileobj.tell()

    def bits(self, count: int) -> int:
        """Reads `count` bits and returns an uint, MSB read first.

        May raise BitReaderError if not enough data could be read or
        IOError by the underlying file object.
        """

        if count < 0:
            raise ValueError

        if count > self._bits:
            n_bytes = (count - self._bits + 7) // 8
            data = self._fileobj.read(n_bytes)
            if len(data) != n_bytes:
                raise BitReaderError("not enough data")
            for b in bytearray(data):
                self._buffer = (self._buffer << 8) | b
            self._bits += n_bytes * 8

        self._bits -= count
        value = self._buffer >> self._bits
        self._buffer &= (1 << self._bits) - 1
        assert self._bits < 8
        return value

    def bytes(self, count: int) -> bytes:
        """Returns a bytearray of length `count`. Works unaligned."""

        if count < 0:
            raise ValueError

        # fast path
        if self._bits == 0:
            data = self._fileobj.read(count)
            if len(data) != count:
                raise BitReaderError("not enough data")
            return data

        return bytes(bytearray(self.bits(8) for _ in range(count)))

    def skip(self, count: int) -> None:
        """Skip `count` bits.

        Might raise BitReaderError if there wasn't enough data to skip,
        but might also fail on the next bits() instead.
        """

        if count < 0:
            raise ValueError

        if count <= self._bits:
            self.bits(count)
        else:
            count -= self.align()
            n_bytes = count // 8
            self._fileobj.seek(n_bytes, 1)
            count -= n_bytes * 8
            self.bits(count)

    def get_position(self) -> int:
        """Returns the amount of bits read or skipped so far"""

        return (self._fileobj.tell() - self._pos) * 8 - self._bits

    def align(self) -> int:
        """Align to the next byte, returns the amount of bits skipped"""

        bits = self._bits
        self._buffer = 0
        self._bits = 0
        return bits

    def is_aligned(self) -> bool:
        """If we are currently aligned to bytes and nothing is buffered"""

        return self._bits == 0
