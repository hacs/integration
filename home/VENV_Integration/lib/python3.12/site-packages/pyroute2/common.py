# -*- coding: utf-8 -*-
'''
Common utilities
'''
import errno
import io
import logging
import os
import re
import socket
import struct
import sys
import threading
import time
import types

log = logging.getLogger(__name__)

try:
    #
    # Python2 section
    #
    basestring = basestring
    reduce = reduce
    file = file

except NameError:
    #
    # Python3 section
    #
    basestring = (str, bytes)
    from functools import reduce

    reduce = reduce
    file = io.BytesIO

AF_MPLS = 28
AF_PIPE = 255  # Right now AF_MAX == 40
DEFAULT_RCVBUF = 65536
_uuid32 = 0  # (singleton) the last uuid32 value saved to avoid collisions
_uuid32_lock = threading.Lock()

size_suffixes = {
    'b': 1,
    'k': 1024,
    'kb': 1024,
    'm': 1024 * 1024,
    'mb': 1024 * 1024,
    'g': 1024 * 1024 * 1024,
    'gb': 1024 * 1024 * 1024,
    'kbit': 1024 / 8,
    'mbit': 1024 * 1024 / 8,
    'gbit': 1024 * 1024 * 1024 / 8,
}


time_suffixes = {
    's': 1,
    'sec': 1,
    'secs': 1,
    'ms': 1000,
    'msec': 1000,
    'msecs': 1000,
    'us': 1000000,
    'usec': 1000000,
    'usecs': 1000000,
}

rate_suffixes = {
    'bit': 1,
    'Kibit': 1024,
    'kbit': 1000,
    'mibit': 1024 * 1024,
    'mbit': 1000000,
    'gibit': 1024 * 1024 * 1024,
    'gbit': 1000000000,
    'tibit': 1024 * 1024 * 1024 * 1024,
    'tbit': 1000000000000,
    'Bps': 8,
    'KiBps': 8 * 1024,
    'KBps': 8000,
    'MiBps': 8 * 1024 * 1024,
    'MBps': 8000000,
    'GiBps': 8 * 1024 * 1024 * 1024,
    'GBps': 8000000000,
    'TiBps': 8 * 1024 * 1024 * 1024 * 1024,
    'TBps': 8000000000000,
}


##
# General purpose
#
class View(object):
    '''
    A read-only view of a dictionary object.
    '''

    def __init__(self, src=None, path=None, constraint=lambda k, v: True):
        self.src = src if src is not None else {}
        if path is not None:
            path = path.split('/')
            for step in path:
                self.src = getattr(self.src, step)
        self.constraint = constraint

    def __getitem__(self, key):
        if key in self.keys():
            return self.src[key]
        raise KeyError()

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _filter(self):
        ret = []
        for key, value in tuple(self.src.items()):
            try:
                if self.constraint(key, value):
                    ret.append((key, value))
            except Exception as e:
                log.error("view filter error: %s", e)
        return ret

    def keys(self):
        return [x[0] for x in self._filter()]

    def values(self):
        return [x[1] for x in self._filter()]

    def items(self):
        return self._filter()

    def __iter__(self):
        for key in self.keys():
            yield key

    def __repr__(self):
        return repr(dict(self._filter()))


class Namespace(object):
    def __init__(self, parent, override=None):
        self.parent = parent
        self.override = override or {}

    def __getattr__(self, key):
        if key in ('parent', 'override'):
            return object.__getattr__(self, key)
        elif key in self.override:
            return self.override[key]
        else:
            ret = getattr(self.parent, key)
            # ACHTUNG
            #
            # if the attribute we got with `getattr`
            # is a method, rebind it to the Namespace
            # object, so all subsequent getattrs will
            # go through the Namespace also.
            #
            if isinstance(ret, types.MethodType):
                ret = type(ret)(ret.__func__, self)
            return ret

    def __setattr__(self, key, value):
        if key in ('parent', 'override'):
            object.__setattr__(self, key, value)
        elif key in self.override:
            self.override[key] = value
        else:
            setattr(self.parent, key, value)


class Dotkeys(dict):
    '''
    This is a sick-minded hack of dict, intended to be an eye-candy.
    It allows to get dict's items by dot reference:

    ipdb["lo"] == ipdb.lo
    ipdb["eth0"] == ipdb.eth0

    Obviously, it will not work for some cases, like unicode names
    of interfaces and so on. Beside of that, it introduces some
    complexity.

    But it simplifies live for old-school admins, who works with good
    old "lo", "eth0", and like that naming schemes.
    '''

    __var_name = re.compile('^[a-zA-Z_]+[a-zA-Z_0-9]*$')

    def __dir__(self):
        return [
            i for i in self if isinstance(i, str) and self.__var_name.match(i)
        ]

    def __getattribute__(self, key, *argv):
        try:
            return dict.__getattribute__(self, key)
        except AttributeError as e:
            if key == '__deepcopy__':
                raise e
            elif key[:4] == 'set_':

                def set_value(value):
                    self[key[4:]] = value
                    return self

                return set_value
            elif key in self:
                return self[key]
            else:
                raise e

    def __setattr__(self, key, value):
        if key in self:
            self[key] = value
        else:
            dict.__setattr__(self, key, value)

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            dict.__delattr__(self, key)


def map_namespace(prefix, ns, normalize=None):
    '''
    Take the namespace prefix, list all constants and build two
    dictionaries -- straight and reverse mappings. E.g.:

    ## neighbor attributes
    NDA_UNSPEC = 0
    NDA_DST = 1
    NDA_LLADDR = 2
    NDA_CACHEINFO = 3
    NDA_PROBES = 4
    (NDA_NAMES, NDA_VALUES) = map_namespace('NDA', globals())

    Will lead to::

        NDA_NAMES = {'NDA_UNSPEC': 0,
                     ...
                     'NDA_PROBES': 4}
        NDA_VALUES = {0: 'NDA_UNSPEC',
                      ...
                      4: 'NDA_PROBES'}

    The `normalize` parameter can be:

        - None — no name transformation will be done
        - True — cut the prefix and `lower()` the rest
        - lambda x: … — apply the function to every name
    '''
    nmap = {None: lambda x: x, True: lambda x: x[len(prefix) :].lower()}

    if not isinstance(normalize, types.FunctionType):
        normalize = nmap[normalize]

    by_name = dict(
        [(normalize(i), ns[i]) for i in ns.keys() if i.startswith(prefix)]
    )
    by_value = dict(
        [(ns[i], normalize(i)) for i in ns.keys() if i.startswith(prefix)]
    )
    return (by_name, by_value)


def getbroadcast(addr, mask, family=socket.AF_INET):
    # 1. convert addr to int
    i = socket.inet_pton(family, addr)
    if family == socket.AF_INET:
        i = struct.unpack('>I', i)[0]
        a = 0xFFFFFFFF
        length = 32
    elif family == socket.AF_INET6:
        i = struct.unpack('>QQ', i)
        i = i[0] << 64 | i[1]
        a = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        length = 128
    else:
        raise NotImplementedError('family not supported')
    # 2. calculate mask
    m = (a << length - mask) & a
    # 3. calculate default broadcast
    n = (i & m) | a >> mask
    # 4. convert it back to the normal address form
    if family == socket.AF_INET:
        n = struct.pack('>I', n)
    else:
        n = struct.pack('>QQ', n >> 64, n & (a >> 64))
    return socket.inet_ntop(family, n)


def dqn2int(mask, family=socket.AF_INET):
    '''
    IPv4 dotted quad notation to int mask conversion
    '''
    ret = 0
    binary = socket.inet_pton(family, mask)
    for offset in range(len(binary) // 4):
        ret += bin(
            struct.unpack('I', binary[offset * 4 : offset * 4 + 4])[0]
        ).count('1')
    return ret


def get_address_family(address):
    if address.find(':') > -1:
        return socket.AF_INET6
    else:
        return socket.AF_INET


def hexdump(payload, length=0):
    '''
    Represent byte string as hex -- for debug purposes
    '''
    return ':'.join('{0:02x}'.format(c) for c in payload[:length] or payload)


def hexload(data):
    return bytes(bytearray((int(x, 16) for x in data.split(':'))))


def load_dump(f, meta=None):
    '''
    Load a packet dump from an open file-like object or a string.

    Supported dump formats:

    * strace hex dump (\\x00\\x00...)
    * pyroute2 hex dump (00:00:...)

    Simple markup is also supported. Any data from # or ;
    till the end of the string is a comment and ignored.
    Any data after . till EOF is ignored as well.

    With #! starts an optional code block. All the data
    in the code block will be read and returned via
    metadata dictionary.
    '''
    data = ''
    code = None
    meta_data = None
    meta_label = None
    if isinstance(f, str):
        io_obj = io.StringIO()
        io_obj.write(f)
        io_obj.seek(0)
    else:
        io_obj = f

    for a in io_obj.readlines():
        if code is not None:
            code += a
            continue

        if meta_data is not None:
            meta_data += a
            continue

        offset = 0
        length = len(a)
        while offset < length:
            if a[offset] in (' ', '\t', '\n'):
                offset += 1
            elif a[offset] == '#':
                if a[offset : offset + 2] == '#!':
                    # read the code block until EOF
                    code = ''
                elif a[offset : offset + 2] == '#:':
                    # read data block until EOF
                    meta_label = a.split(':')[1].strip()
                    meta_data = ''
                break
            elif a[offset] == '.':
                return data
            elif a[offset] == '\\':
                # strace hex format
                data += chr(int(a[offset + 2 : offset + 4], 16))
                offset += 4
            else:
                # pyroute2 hex format
                data += chr(int(a[offset : offset + 2], 16))
                offset += 3

    if isinstance(meta, dict):
        if code is not None:
            meta['code'] = code
        if meta_data is not None:
            meta[meta_label] = meta_data

    if sys.version[0] == '3':
        return bytes(data, 'iso8859-1')
    else:
        return data


class AddrPool(object):
    '''
    Address pool
    '''

    cell = 0xFFFFFFFFFFFFFFFF

    def __init__(
        self, minaddr=0xF, maxaddr=0xFFFFFF, reverse=False, release=False
    ):
        self.cell_size = 0  # in bits
        mx = self.cell
        self.reverse = reverse
        self.release = release
        self.allocated = 0
        if self.release and not isinstance(self.release, int):
            raise TypeError()
        self.ban = []
        while mx:
            mx >>= 8
            self.cell_size += 1
        self.cell_size *= 8
        # calculate, how many ints we need to bitmap all addresses
        self.cells = int((maxaddr - minaddr) / self.cell_size + 1)
        # initial array
        self.addr_map = [self.cell]
        self.minaddr = minaddr
        self.maxaddr = maxaddr
        self.lock = threading.RLock()

    def alloc(self):
        with self.lock:
            # gc self.ban:
            for item in tuple(self.ban):
                if item['counter'] == 0:
                    self.free(item['addr'])
                    self.ban.remove(item)
                else:
                    item['counter'] -= 1

            # iterate through addr_map
            base = 0
            for cell in self.addr_map:
                if cell:
                    # not allocated addr
                    bit = 0
                    while True:
                        if (1 << bit) & self.addr_map[base]:
                            self.addr_map[base] ^= 1 << bit
                            break
                        bit += 1
                    ret = base * self.cell_size + bit

                    if self.reverse:
                        ret = self.maxaddr - ret
                    else:
                        ret = ret + self.minaddr

                    if self.minaddr <= ret <= self.maxaddr:
                        if self.release:
                            self.free(ret, ban=self.release)
                        self.allocated += 1
                        return ret
                    else:
                        self.free(ret)
                        raise KeyError('no free address available')

                base += 1
            # no free address available
            if len(self.addr_map) < self.cells:
                # create new cell to allocate address from
                self.addr_map.append(self.cell)
                return self.alloc()
            else:
                raise KeyError('no free address available')

    def alloc_multi(self, count):
        with self.lock:
            addresses = []
            raised = False
            try:
                for _ in range(count):
                    addr = self.alloc()
                    try:
                        addresses.append(addr)
                    except:
                        # In case of a MemoryError during appending,
                        # the finally block would not free the address.
                        self.free(addr)
                return addresses
            except:
                raised = True
                raise
            finally:
                if raised:
                    for addr in addresses:
                        self.free(addr)

    def locate(self, addr):
        if self.reverse:
            addr = self.maxaddr - addr
        else:
            addr -= self.minaddr
        base = addr // self.cell_size
        bit = addr % self.cell_size
        try:
            is_allocated = not self.addr_map[base] & (1 << bit)
        except IndexError:
            is_allocated = False
        return (base, bit, is_allocated)

    def setaddr(self, addr, value):
        if value not in ('free', 'allocated'):
            raise TypeError()
        with self.lock:
            base, bit, is_allocated = self.locate(addr)
            if value == 'free' and is_allocated:
                self.allocated -= 1
                self.addr_map[base] |= 1 << bit
            elif value == 'allocated' and not is_allocated:
                self.allocated += 1
                self.addr_map[base] &= ~(1 << bit)

    def free(self, addr, ban=0):
        with self.lock:
            if ban != 0:
                self.ban.append({'addr': addr, 'counter': ban})
            else:
                base, bit, is_allocated = self.locate(addr)
                if len(self.addr_map) <= base:
                    raise KeyError('address is not allocated')
                if self.addr_map[base] & (1 << bit):
                    raise KeyError('address is not allocated')
                self.allocated -= 1
                self.addr_map[base] ^= 1 << bit


def _fnv1_python2(data):
    '''
    FNV1 -- 32bit hash, python2 version

    @param data: input
    @type data: bytes

    @return: 32bit int hash
    @rtype: int

    See: http://www.isthe.com/chongo/tech/comp/fnv/index.html
    '''
    hval = 0x811C9DC5
    for i in range(len(data)):
        hval *= 0x01000193
        hval ^= struct.unpack('B', data[i])[0]
    return hval & 0xFFFFFFFF


def _fnv1_python3(data):
    '''
    FNV1 -- 32bit hash, python3 version

    @param data: input
    @type data: bytes

    @return: 32bit int hash
    @rtype: int

    See: http://www.isthe.com/chongo/tech/comp/fnv/index.html
    '''
    hval = 0x811C9DC5
    for i in range(len(data)):
        hval *= 0x01000193
        hval ^= data[i]
    return hval & 0xFFFFFFFF


if sys.version[0] == '3':
    fnv1 = _fnv1_python3
else:
    fnv1 = _fnv1_python2


def uuid32():
    '''
    Return 32bit UUID, based on the current time and pid.

    @return: 32bit int uuid
    @rtype: int

    The uuid is guaranteed to be unique within one process.
    '''
    global _uuid32
    global _uuid32_lock

    with _uuid32_lock:
        candidate = _uuid32
        while candidate == _uuid32:
            candidate = fnv1(
                struct.pack('QQ', int(time.time() * 1000000), os.getpid())
            )
        _uuid32 = candidate
        return candidate


def uifname():
    '''
    Return a unique interface name based on a prime function

    @return: interface name
    @rtype: str
    '''
    return 'pr%x' % uuid32()


def map_exception(match, subst):
    '''
    Decorator to map exception types
    '''

    def wrapper(f):
        def decorated(*argv, **kwarg):
            try:
                f(*argv, **kwarg)
            except Exception as e:
                if match(e):
                    raise subst(e)
                raise

        return decorated

    return wrapper


def map_enoent(f):
    '''
    Shortcut to map OSError(2) -> OSError(95)
    '''
    return map_exception(
        lambda x: (isinstance(x, OSError) and x.errno == errno.ENOENT),
        lambda x: OSError(errno.EOPNOTSUPP, 'Operation not supported'),
    )(f)


def metaclass(mc):
    def wrapped(cls):
        nvars = {}
        skip = ['__dict__', '__weakref__']
        slots = cls.__dict__.get('__slots__')
        if not isinstance(slots, (list, tuple)):
            slots = [slots]
        for k in slots:
            skip.append(k)
        for k, v in cls.__dict__.items():
            if k not in skip:
                nvars[k] = v
        return mc(cls.__name__, cls.__bases__, nvars)

    return wrapped


def failed_class(message):
    class FailedClass(object):
        def __init__(self, *argv, **kwarg):
            ret = RuntimeError(message)
            ret.feature_supported = False
            raise ret

    return FailedClass
