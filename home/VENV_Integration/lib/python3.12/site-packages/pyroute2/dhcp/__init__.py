'''
DHCP protocol
=============

The DHCP implementation here is far from complete, but
already provides some basic functionality. Later it will
be extended with IPv6 support and more DHCP options
will be added.

Right now it can be interesting mostly to developers,
but not users and/or system administrators. So, the
development hints first.

The packet structure description is intentionally
implemented as for netlink packets. Later these two
parsers, netlink and generic, can be merged, so the
syntax is more or less compatible.

Packet fields
-------------

There are two big groups of items within any DHCP packet.
First, there are BOOTP/DHCP packet fields, they're defined
with the `fields` attribute::

    class dhcp4msg(msg):
        fields = ((name, format, policy),
                  (name, format, policy),
                  ...
                  (name, format, policy))

The `name` can be any literal. Format should be specified
as for the struct module, like `B` for `uint8`, or `i` for
`int32`, or `>Q` for big-endian uint64. There are also
aliases defined, so one can write `uint8` or `be16`, or
like that. Possible aliases can be seen in the
`pyroute2.protocols` module.

The `policy` is a bit complicated. It can be a number or
literal, and it will mean that it is a default value, that
should be encoded if no other value is given.

But when the `policy` is a dictionary, it can contain keys
as follows::

    'l2addr': {'format': '6B',
               'decode': ...,
               'encode': ...}

Keys `encode` and `decode` should contain filters to be used
in decoding and encoding procedures. The encoding filter
should accept the value from user's definition and should
return a value that can be packed using `format`. The decoding
filter should accept a value, decoded according to `format`,
and should return value that can be used by a user.

The `struct` module can not decode IP addresses etc, so they
should be decoded as `4s`, e.g. Further transformation from
4 bytes string to a string like '10.0.0.1' performs the filter.

DHCP options
------------

DHCP options are described in a similar way::

    options = ((code, name, format),
               (code, name, format),
               ...
               (code, name, format))

Code is a `uint8` value, name can be any string literal. Format
is a string, that must have a corresponding class, inherited from
`pyroute2.dhcp.option`. One can find these classes in
`pyroute2.dhcp` (more generic) or in `pyroute2.dhcp.dhcp4msg`
(IPv4-specific). The option class must reside within dhcp message
class.

Every option class can be decoded in two ways. If it has fixed
width fields, it can be decoded with ordinary `msg` routines, and
in this case it can look like that::

    class client_id(option):
        fields = (('type', 'uint8'),
                  ('key', 'l2addr'))

If it must be decoded by some custom rules, one can define the
policy just like for the fields above::

    class array8(option):
        policy = {'format': 'string',
                  'encode': lambda x: array('B', x).tobytes(),
                  'decode': lambda x: array('B', x).tolist()}

In the corresponding modules, like in `pyroute2.dhcp.dhcp4msg`,
one can define as many custom DHCP options, as one need. Just
be sure, that they are compatible with the DHCP server and all
fit into 1..254 (`uint8`) -- the 0 code is used for padding and
the code 255 is the end of options code.
'''

import struct
import sys
from array import array

from pyroute2.common import basestring
from pyroute2.protocols import msg

BOOTREQUEST = 1
BOOTREPLY = 2

DHCPDISCOVER = 1
DHCPOFFER = 2
DHCPREQUEST = 3
DHCPDECLINE = 4
DHCPACK = 5
DHCPNAK = 6
DHCPRELEASE = 7
DHCPINFORM = 8


if not hasattr(array, 'tobytes'):
    # Python2 and Python3 versions of array differ,
    # but we need here a consistent API w/o warnings
    class array(array):
        tobytes = array.tostring


class option(msg):
    code = 0
    data_length = 0
    policy = None
    value = None

    def __init__(self, content=None, buf=b'', offset=0, value=None, code=0):
        msg.__init__(
            self, content=content, buf=buf, offset=offset, value=value
        )
        self.code = code

    @property
    def length(self):
        if self.data_length is None:
            return None
        if self.data_length == 0:
            return 1
        else:
            return self.data_length + 2

    def encode(self):
        # pack code
        self.buf += struct.pack('B', self.code)
        if self.code in (0, 255):
            return self
        # save buf
        save = self.buf
        self.buf = b''
        # pack data into the new buf
        if self.policy is not None:
            value = self.policy.get('encode', lambda x: x)(self.value)
            if self.policy['format'] == 'string':
                fmt = '%is' % len(value)
            else:
                fmt = self.policy['format']
            if sys.version_info[0] == 3 and isinstance(value, str):
                value = value.encode('utf-8')
            self.buf = struct.pack(fmt, value)
        else:
            msg.encode(self)
        # get the length
        data = self.buf
        self.buf = save
        self.buf += struct.pack('B', len(data))
        # attach the packed data
        self.buf += data
        return self

    def decode(self):
        self.data_length = struct.unpack(
            'B', self.buf[self.offset + 1 : self.offset + 2]
        )[0]
        if self.policy is not None:
            if self.policy['format'] == 'string':
                fmt = '%is' % self.data_length
            else:
                fmt = self.policy['format']
            value = struct.unpack(
                fmt,
                self.buf[self.offset + 2 : self.offset + 2 + self.data_length],
            )
            if len(value) == 1:
                value = value[0]
            value = self.policy.get('decode', lambda x: x)(value)
            if (
                isinstance(value, basestring)
                and self.policy['format'] == 'string'
            ):
                value = value[: value.find(b'\x00')]
            self.value = value
        else:
            # remember current offset as msg.decode() will advance it
            offset = self.offset
            # move past the code and option length bytes so that msg.decode()
            # starts parsing at the right location
            self.offset += 2
            msg.decode(self)
            # restore offset so that dhcpmsg.decode() advances it correctly
            self.offset = offset

        return self


class dhcpmsg(msg):
    options = ()
    l2addr = None
    _encode_map = {}
    _decode_map = {}

    def _register_options(self):
        for option in self.options:
            code, name, fmt = option[:3]
            self._decode_map[code] = self._encode_map[name] = {
                'name': name,
                'code': code,
                'format': fmt,
            }

    def decode(self):
        msg.decode(self)
        self._register_options()
        self['options'] = {}
        while self.offset < len(self.buf):
            code = struct.unpack('B', self.buf[self.offset : self.offset + 1])[
                0
            ]
            if code == 0:
                self.offset += 1
                continue
            if code == 255:
                return self
            # code is unknown -- bypass it
            if code not in self._decode_map:
                length = struct.unpack(
                    'B', self.buf[self.offset + 1 : self.offset + 2]
                )[0]
                self.offset += length + 2
                continue

            # code is known, work on it
            option_class = getattr(self, self._decode_map[code]['format'])
            option = option_class(buf=self.buf, offset=self.offset)
            option.decode()
            self.offset += option.length
            if option.value is not None:
                value = option.value
            else:
                value = option
            self['options'][self._decode_map[code]['name']] = value
        return self

    def encode(self):
        msg.encode(self)
        self._register_options()
        # put message type
        options = self.get('options') or {
            'message_type': DHCPDISCOVER,
            'parameter_list': [1, 3, 6, 12, 15, 28],
        }

        self.buf += (
            self.uint8(code=53, value=options['message_type']).encode().buf
        )
        self.buf += (
            self.client_id({'type': 1, 'key': self['chaddr']}, code=61)
            .encode()
            .buf
        )
        self.buf += self.string(code=60, value='pyroute2').encode().buf

        for name, value in options.items():
            if name in ('message_type', 'client_id', 'vendor_id'):
                continue
            fmt = self._encode_map.get(name, {'format': None})['format']
            if fmt is None:
                continue
            # name is known, ok
            option_class = getattr(self, fmt)
            if isinstance(value, dict):
                option = option_class(
                    value, code=self._encode_map[name]['code']
                )
            else:
                option = option_class(
                    code=self._encode_map[name]['code'], value=value
                )
            self.buf += option.encode().buf

        self.buf += self.none(code=255).encode().buf
        return self

    class none(option):
        pass

    class be16(option):
        policy = {'format': '>H'}

    class be32(option):
        policy = {'format': '>I'}

    class uint8(option):
        policy = {'format': 'B'}

    class string(option):
        policy = {'format': 'string'}

    class array8(option):
        policy = {
            'format': 'string',
            'encode': lambda x: array('B', x).tobytes(),
            'decode': lambda x: array('B', x).tolist(),
        }

    class client_id(option):
        fields = (('type', 'uint8'), ('key', 'l2addr'))
