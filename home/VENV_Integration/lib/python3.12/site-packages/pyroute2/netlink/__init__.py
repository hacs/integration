'''
Netlink
-------

basics
======

General netlink packet structure::

    nlmsg packet:
        header
        data

Generic netlink message header::

    nlmsg header:
        uint32 length
        uint16 type
        uint16 flags
        uint32 sequence number
        uint32 pid

The `length` field is the length of all the packet, including
data and header. The `type` field is used to distinguish different
message types, commands etc. Please note, that there is no
explicit protocol field -- you choose a netlink protocol, when
you create a socket.

The `sequence number` is very important. Netlink is an asynchronous
protocol -- it means, that the packet order doesn't matter and is
not guaranteed. But responses to a request are always marked with
the same sequence number, so you can treat it as a cookie.

Please keep in mind, that a netlink request can initiate a
cascade of events, and netlink messages from these events can
carry sequence number == 0. E.g., it is so when you remove a
primary IP addr from an interface, when `promote_secondaries`
sysctl is set.

Beside of incapsulated headers and other protocol-specific data,
netlink messages can carry NLA (netlink attributes). NLA
structure is as follows::

    NLA header:
        uint16 length
        uint16 type
    NLA data:
        data-specific struct
        # optional:
        NLA
        NLA
        ...

So, NLA structures can be nested, forming a tree.

Complete structure of a netlink packet::

    nlmsg header:
        uint32 length
        uint16 type
        uint16 flags
        uint32 sequence number
        uint32 pid
    [ optional protocol-specific data ]
    [ optional NLA tree ]

More information about netlink protocol you can find in
the man pages.

pyroute2 and netlink
====================

packets
~~~~~~~

To simplify the development, pyroute2 provides an easy way to
describe packet structure. As an example, you can take the
ifaddrmsg description -- `pyroute2/netlink/rtnl/ifaddrmsg.py`.

To describe a packet, you need to inherit from `nlmsg` class::

    from pyroute2.netlink import nlmsg

    class foo_msg(nlmsg):
        fields = ( ... )
        nla_map = ( ... )

NLA are described in the same way, but the parent class should be
`nla`, instead of `nlmsg`. And yes, it is important to use the
proper parent class -- it affects the header structure.

fields attribute
~~~~~~~~~~~~~~~~

The `fields` attribute describes the structure of the
protocol-specific data. It is a tuple of tuples, where each
member contains a field name and its data format.

Field data format should be specified as for Python `struct`
module. E.g., ifaddrmsg structure::

    struct ifaddrmsg {
        __u8  ifa_family;
        __u8  ifa_prefixlen;
        __u8  ifa_flags;
        __u8  ifa_scope;
        __u32 ifa_index;
    };

should be described as follows::

    class ifaddrmsg(nlmsg):
        fields = (('family', 'B'),
                  ('prefixlen', 'B'),
                  ('flags', 'B'),
                  ('scope', 'B'),
                  ('index', 'I'))

Format strings are passed directly to the `struct` module,
so you can use all the notations like `>I`, `16s` etc. All
fields are parsed from the stream separately, so if you
want to explicitly fix alignemt, as if it were C struct,
use the `pack` attribute::

    class tstats(nla):
        pack = 'struct'
        fields = (('version', 'H'),
                  ('ac_exitcode', 'I'),
                  ('ac_flag', 'B'),
                  ...)

Explicit padding bytes also can be used, when struct
packing doesn't work well::

    class ipq_mode_msg(nlmsg):
        pack = 'struct'
        fields = (('value', 'B'),
                  ('__pad', '7x'),
                  ('range', 'I'),
                  ('__pad', '12x'))


nla_map attribute
~~~~~~~~~~~~~~~~~

The `nla_map` attribute is a tuple of NLA descriptions. Each
description is also a tuple in two different forms: either
two fields, name and format, or three fields: type, name and
format.

Please notice, that the format field is a string name of
corresponding NLA class::

    class ifaddrmsg(nlmsg):
        ...
        nla_map = (('IFA_UNSPEC',  'hex'),
                   ('IFA_ADDRESS', 'ipaddr'),
                   ('IFA_LOCAL', 'ipaddr'),
                   ...)

This code will create mapping, where IFA_ADDRESS NLA will be of
type 1 and IFA_LOCAL -- of type 2, etc. Both NLA will be decoded
as IP addresses (class `ipaddr`). IFA_UNSPEC will be of type 0,
and if it will be in the NLA tree, it will be just dumped in hex.

NLA class names are should be specified as strings, since they
are resolved in runtime.

There are several pre-defined NLA types, that you will get with
`nla` class:

    - `none` -- ignore this NLA
    - `flag` -- boolean flag NLA (no payload; NLA exists = True)
    - `uint8`, `uint16`, `uint32`, `uint64` -- unsigned int
    - `be8`, `be16`, `be32`, `be64` -- big-endian unsigned int
    - `ipaddr` -- IP address, IPv4 or IPv6
    - `ip4addr` -- only IPv4 address type
    - `ip6addr` -- only IPv6 address type
    - `target` -- a univeral target (IPv4, IPv6, MPLS)
    - `l2addr` -- MAC address
    - `lladdr` -- link layer address (MAC, IPv4, IPv6)
    - `hex` -- hex dump as a string -- useful for debugging
    - `cdata` -- a binary data
    - `string` -- UTF-8 string
    - `asciiz` -- zero-terminated ASCII string, no decoding
    - `array` -- array of simple types (uint8, uint16 etc.)

Please refer to `pyroute2/netlink/__init__.py` for details.

You can also make your own NLA descriptions::

    class ifaddrmsg(nlmsg):
        ...
        nla_map = (...
                   ('IFA_CACHEINFO', 'cacheinfo'),
                   ...)

        class cacheinfo(nla):
            fields = (('ifa_preferred', 'I'),
                      ('ifa_valid', 'I'),
                      ('cstamp', 'I'),
                      ('tstamp', 'I'))

Custom NLA descriptions should be defined in the same class,
where they are used.

explicit NLA type ids
~~~~~~~~~~~~~~~~~~~~~

Also, it is possible to use not autogenerated type numbers, as
for ifaddrmsg, but specify them explicitly::

    class iw_event(nla):
        ...
        nla_map = ((0x8B00, 'SIOCSIWCOMMIT', 'hex'),
                   (0x8B01, 'SIOCGIWNAME', 'hex'),
                   (0x8B02, 'SIOCSIWNWID', 'hex'),
                   (0x8B03, 'SIOCGIWNWID', 'hex'),
                   ...)

Here you can see custom NLA type numbers -- 0x8B00, 0x8B01 etc.
It is not permitted to mix these two forms in one class: you should
use ether autogenerated type numbers (two fields tuples), or
explicit numbers (three fields typles).

nla map adapters
~~~~~~~~~~~~~~~~

If the default declarative NLA map is not flexible enough, one
can use a custom map adapter. In order to do so, one should define
at least one function to return `pyroute2.netlink.NlaSpec()`, and
one optional function to tell the parser if the attribute is supported.
The simplest definition only to decode packets:

.. code-block:: python

    from pyroute2.netlink import NlaMapAdapter, NlaSpec, nlmsg


    def my_flexible_nla_spec(key):
        return NlaSpec(nlmsg_atoms.hex, key, f'NLA_CLASS_{key}')


    class my_msg(nlmsg):

        nla_map = NlaMapAdapter(my_flexible_nla_spec)

    # example result
    [
        {
            'attrs': [
                ('NLA_CLASS_1', '00:00:00:00'),
                ('NLA_CLASS_5', '00:00:00:00'),
            ],
            'header': {
                ...
            },
        },
    ]

In this example the same routine is used both for decoding and encoding
workflows, but the workflows are not equal, thus the example will fail on
encoding. Still the example may be useful if you don't plan to encode
packets of this type.

The decoding workflow will pass an integer as the `key` for NLA type, while
the encoding workflow passes a string as the `key` for NLA name. To correctly
handle both workflows, you can use either the `key` type discrimination, or
the explicit declaration syntax:

.. code-block:: python

    # discriminate workflows by the key type
    def my_flexible_nla_spec(key):
        if isinstance(key, int):
            # decoding workflow
            ...
        else:
            # encoding workflow
            ...


    class my_msg(nlmsg):

        nla_map = NlaMapAdapter(my_flexible_nla_spec)

.. code-block:: python

    # declarate separate workflows
    def my_flexible_nla_spec_encode(key):
        # receives a string -- nla type name
        ...


    def my_flexible_nla_spec_decode(key):
        # receives an int -- nla type id
        ...


    class my_msg(nlmsg):

        nla_map = {
            'decode': NlaMapAdapter(my_flexible_nla_spec_decode),
            'encode': NlaMapAdapter(my_flexible_nla_spec_encode),
        }

array types
~~~~~~~~~~~

There are different array-like NLA types in the kernel, and
some of them are covered by pyroute2. An array of simple type
elements::

    # declaration
    nla_map = (('NLA_TYPE', 'array(uint8)'), ...)

    # data layout
    +======+======+----------------------------
    | len  | type | uint8 | uint8 | uint 8 | ...
    +======+======+----------------------------

    # decoded
    {'attrs': [['NLA_TYPE', (2, 3, 4, 5, ...)], ...], ...}

An array of NLAs::

    # declaration
    nla_map = (('NLA_TYPE', '*type'), ...)

    # data layout
    +=======+=======+-----------------------+-----------------------+--
    | len   | type* | len  | type | payload | len  | type | payload | ...
    +=======+=======+-----------------------+-----------------------+--
    # type* -- in that case the type is OR'ed with NLA_F_NESTED

    # decoded
    {'attrs': [['NLA_TYPE', [payload, payload, ...]], ...], ...}

parsed netlink message
~~~~~~~~~~~~~~~~~~~~~~

Netlink messages are represented by pyroute2 as dictionaries
as follows::

    {'header': {'pid': ...,
                'length: ...,
                'flags': ...,
                'error': None,  # if you are lucky
                'type': ...,
                'sequence_number': ...},

     # fields attributes
     'field_name1': value,
     ...
     'field_nameX': value,

     # nla tree
     'attrs': [['NLA_NAME1', value],
               ...
               ['NLA_NAMEX', value],
               ['NLA_NAMEY', {'field_name1': value,
                              ...
                              'field_nameX': value,
                              'attrs': [['NLA_NAME.... ]]}]]}

As an example, a message from the wireless subsystem about new
scan event::

    {'index': 4,
     'family': 0,
     '__align': 0,
     'header': {'pid': 0,
                'length': 64,
                'flags': 0,
                'error': None,
                'type': 16,
                'sequence_number': 0},
     'flags': 69699,
     'ifi_type': 1,
     'event': 'RTM_NEWLINK',
     'change': 0,
     'attrs': [['IFLA_IFNAME', 'wlp3s0'],
               ['IFLA_WIRELESS',
                {'attrs': [['SIOCGIWSCAN',
                            '00:00:00:00:00:00:00:00:00:00:00:00']]}]]}

One important detail is that NLA chain is represented as a list of
elements `['NLA_TYPE', value]`, not as a dictionary. The reason is that
though in the kernel *usually* NLA chain is a dictionary, the netlink
protocol by itself doesn't require elements of each type to be unique.
In a message there may be several NLA of the same type.

encoding and decoding algo
~~~~~~~~~~~~~~~~~~~~~~~~~~

The message encoding works as follows:

1. Reserve space for the message header (if there is)
2. Iterate defined `fields`, encoding values with `struct.pack()`
3. Iterate NLA from the `attrs` field, looking up types in `nla_map`
4. Encode the header

Since every NLA is also an `nlmsg` object, there is a recursion.

The decoding process is a bit simpler:

1. Decode the header
2. Iterate `fields`, decoding values with `struct.unpack()`
3. Iterate NLA until the message ends

If the `fields` attribute is an empty list, the step 2 will be skipped.
The step 3 will be skipped in the case of the empty `nla_map`. If both
attributes are empty lists, only the header will be encoded/decoded.

create and send messages
~~~~~~~~~~~~~~~~~~~~~~~~

Using high-level interfaces like `IPRoute` or `IPDB`, you will never
need to manually construct and send netlink messages. But in the case
you really need it, it is simple as well.

Having a description class, like `ifaddrmsg` from above, you need to:

    - instantiate it
    - fill the fields
    - encode the packet
    - send the encoded data

The code::

    from pyroute2.netlink import NLM_F_REQUEST
    from pyroute2.netlink import NLM_F_ACK
    from pyroute2.netlink import NLM_F_CREATE
    from pyroute2.netlink import NLM_F_EXCL
    from pyroute2.iproute import RTM_NEWADDR
    from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg

    ##
    # add an addr to an interface
    #

    # create the message
    msg = ifaddrmsg()

    # fill the protocol-specific fields
    msg['index'] = index  # index of the interface
    msg['family'] = AF_INET  # address family
    msg['prefixlen'] = 24  # the address mask
    msg['scope'] = scope  # see /etc/iproute2/rt_scopes

    # attach NLA -- it MUST be a list / mutable
    msg['attrs'] = [['IFA_LOCAL', '192.168.0.1'],
                    ['IFA_ADDRESS', '192.162.0.1']]

    # fill generic netlink fields
    msg['header']['sequence_number'] = nonce  # an unique seq number
    msg['header']['pid'] = os.getpid()
    msg['header']['type'] = RTM_NEWADDR
    msg['header']['flags'] = NLM_F_REQUEST |\\
                             NLM_F_ACK |\\
                             NLM_F_CREATE |\\
                             NLM_F_EXCL

    # encode the packet
    msg.encode()

    # send the buffer
    nlsock.sendto(msg.data, (0, 0))

Please notice, that NLA list *MUST* be mutable.

'''

import io
import logging
import struct
import sys
import threading
import traceback
import types
import weakref
from collections import OrderedDict
from socket import AF_INET, AF_INET6, AF_UNSPEC, inet_ntop, inet_pton

from pyroute2.common import AF_MPLS, basestring, hexdump
from pyroute2.netlink.exceptions import (
    NetlinkDecodeError,
    NetlinkError,
    NetlinkNLADecodeError,
)

log = logging.getLogger(__name__)
# make pep8 happy
_ne = NetlinkError  # reexport for compatibility
_de = NetlinkDecodeError  #


class NotInitialized(Exception):
    pass


##
# That's a hack for the code linter, which works under
# Python3, see unicode reference in the code below
if sys.version[0] == '3':
    unicode = str

NLMSG_MIN_TYPE = 0x10

GENL_NAMSIZ = 16  # length of family name
GENL_MIN_ID = NLMSG_MIN_TYPE
GENL_MAX_ID = 1023

GENL_ADMIN_PERM = 0x01
GENL_CMD_CAP_DO = 0x02
GENL_CMD_CAP_DUMP = 0x04
GENL_CMD_CAP_HASPOL = 0x08

#
# List of reserved static generic netlink identifiers:
#
GENL_ID_GENERATE = 0
GENL_ID_CTRL = NLMSG_MIN_TYPE

#
# Controller
#

CTRL_CMD_UNSPEC = 0x0
CTRL_CMD_NEWFAMILY = 0x1
CTRL_CMD_DELFAMILY = 0x2
CTRL_CMD_GETFAMILY = 0x3
CTRL_CMD_NEWOPS = 0x4
CTRL_CMD_DELOPS = 0x5
CTRL_CMD_GETOPS = 0x6
CTRL_CMD_NEWMCAST_GRP = 0x7
CTRL_CMD_DELMCAST_GRP = 0x8
CTRL_CMD_GETMCAST_GRP = 0x9  # unused
CTRL_CMD_GETPOLICY = 0xA


CTRL_ATTR_UNSPEC = 0x0
CTRL_ATTR_FAMILY_ID = 0x1
CTRL_ATTR_FAMILY_NAME = 0x2
CTRL_ATTR_VERSION = 0x3
CTRL_ATTR_HDRSIZE = 0x4
CTRL_ATTR_MAXATTR = 0x5
CTRL_ATTR_OPS = 0x6
CTRL_ATTR_MCAST_GROUPS = 0x7
CTRL_ATTR_POLICY = 0x8
CTRL_ATTR_OP_POLICY = 0x9
CTRL_ATTR_OP = 0xA

CTRL_ATTR_OP_UNSPEC = 0x0
CTRL_ATTR_OP_ID = 0x1
CTRL_ATTR_OP_FLAGS = 0x2

CTRL_ATTR_MCAST_GRP_UNSPEC = 0x0
CTRL_ATTR_MCAST_GRP_NAME = 0x1
CTRL_ATTR_MCAST_GRP_ID = 0x2

NL_ATTR_TYPE_INVALID = 0
NL_ATTR_TYPE_FLAG = 1
NL_ATTR_TYPE_U8 = 2
NL_ATTR_TYPE_U16 = 3
NL_ATTR_TYPE_U32 = 4
NL_ATTR_TYPE_U64 = 5
NL_ATTR_TYPE_S8 = 6
NL_ATTR_TYPE_S16 = 7
NL_ATTR_TYPE_S32 = 8
NL_ATTR_TYPE_S64 = 9
NL_ATTR_TYPE_BINARY = 10
NL_ATTR_TYPE_STRING = 11
NL_ATTR_TYPE_NUL_STRING = 12
NL_ATTR_TYPE_NESTED = 13
NL_ATTR_TYPE_NESTED_ARRAY = 14
NL_ATTR_TYPE_BITFIELD32 = 15

NL_POLICY_TYPE_ATTR_UNSPEC = 0
NL_POLICY_TYPE_ATTR_TYPE = 1
NL_POLICY_TYPE_ATTR_MIN_VALUE_S = 2
NL_POLICY_TYPE_ATTR_MAX_VALUE_S = 3
NL_POLICY_TYPE_ATTR_MIN_VALUE_U = 4
NL_POLICY_TYPE_ATTR_MAX_VALUE_U = 5
NL_POLICY_TYPE_ATTR_MIN_LENGTH = 6
NL_POLICY_TYPE_ATTR_MAX_LENGTH = 7
NL_POLICY_TYPE_ATTR_POLICY_IDX = 8
NL_POLICY_TYPE_ATTR_POLICY_MAXTYPE = 9
NL_POLICY_TYPE_ATTR_BITFIELD32_MASK = 10
NL_POLICY_TYPE_ATTR_PAD = 11
NL_POLICY_TYPE_ATTR_MASK = 12

#  Different Netlink families
#
NETLINK_ROUTE = 0  # Routing/device hook
NETLINK_UNUSED = 1  # Unused number
NETLINK_USERSOCK = 2  # Reserved for user mode socket protocols
NETLINK_FIREWALL = 3  # Firewalling hook
NETLINK_SOCK_DIAG = 4  # INET socket monitoring
NETLINK_NFLOG = 5  # netfilter/iptables ULOG
NETLINK_XFRM = 6  # ipsec
NETLINK_SELINUX = 7  # SELinux event notifications
NETLINK_ISCSI = 8  # Open-iSCSI
NETLINK_AUDIT = 9  # auditing
NETLINK_FIB_LOOKUP = 10
NETLINK_CONNECTOR = 11
NETLINK_NETFILTER = 12  # netfilter subsystem
NETLINK_IP6_FW = 13
NETLINK_DNRTMSG = 14  # DECnet routing messages
NETLINK_KOBJECT_UEVENT = 15  # Kernel messages to userspace
NETLINK_GENERIC = 16
# leave room for NETLINK_DM (DM Events)
NETLINK_SCSITRANSPORT = 18  # SCSI Transports

# NLA flags
NLA_F_NESTED = 1 << 15
NLA_F_NET_BYTEORDER = 1 << 14


# Netlink message flags values (nlmsghdr.flags)
#
NLM_F_REQUEST = 1  # It is request message.
NLM_F_MULTI = 2  # Multipart message, terminated by NLMSG_DONE
NLM_F_ACK = 4  # Reply with ack, with zero or error code
NLM_F_ECHO = 8  # Echo this request
NLM_F_DUMP_INTR = 0x10  # Dump was inconsistent due to sequence change
NLM_F_DUMP_FILTERED = 0x20  # Dump was filtered as requested

# Modifiers to GET request
NLM_F_ROOT = 0x100  # specify tree    root
NLM_F_MATCH = 0x200  # return all matching
NLM_F_ATOMIC = 0x400  # atomic GET
NLM_F_DUMP = NLM_F_ROOT | NLM_F_MATCH
# Modifiers to NEW request
NLM_F_REPLACE = 0x100  # Override existing
NLM_F_EXCL = 0x200  # Do not touch, if it exists
NLM_F_CREATE = 0x400  # Create, if it does not exist
NLM_F_APPEND = 0x800  # Add to end of list

NLM_F_CAPPED = 0x100
NLM_F_ACK_TLVS = 0x200

NLMSG_NOOP = 0x1  # Nothing
NLMSG_ERROR = 0x2  # Error
NLMSG_DONE = 0x3  # End of a dump
NLMSG_OVERRUN = 0x4  # Data lost
NLMSG_CONTROL = 0xE  # Custom message type for messaging control
NLMSG_TRANSPORT = 0xF  # Custom message type for NL as a transport
NLMSG_MIN_TYPE = 0x10  # < 0x10: reserved control messages
NLMSG_MAX_LEN = 0xFFFF  # Max message length

mtypes = {
    1: 'NLMSG_NOOP',
    2: 'NLMSG_ERROR',
    3: 'NLMSG_DONE',
    4: 'NLMSG_OVERRUN',
}

IPRCMD_NOOP = 0
IPRCMD_STOP = 1
IPRCMD_ACK = 2
IPRCMD_ERR = 3
IPRCMD_REGISTER = 4
IPRCMD_RELOAD = 5
IPRCMD_ROUTE = 6
IPRCMD_CONNECT = 7
IPRCMD_DISCONNECT = 8
IPRCMD_SERVE = 9
IPRCMD_SHUTDOWN = 10
IPRCMD_SUBSCRIBE = 11
IPRCMD_UNSUBSCRIBE = 12
IPRCMD_PROVIDE = 13
IPRCMD_REMOVE = 14
IPRCMD_DISCOVER = 15
IPRCMD_UNREGISTER = 16

SOL_NETLINK = 270

NETLINK_ADD_MEMBERSHIP = 1
NETLINK_DROP_MEMBERSHIP = 2
NETLINK_PKTINFO = 3
NETLINK_BROADCAST_ERROR = 4
NETLINK_NO_ENOBUFS = 5
NETLINK_RX_RING = 6
NETLINK_TX_RING = 7

NETLINK_LISTEN_ALL_NSID = 8
NETLINK_EXT_ACK = 11
NETLINK_GET_STRICT_CHK = 12

clean_cbs = threading.local()

# Cached results for some struct operations.
# No cache invalidation required.
cache_fmt = {}
cache_hdr = {}
cache_jit = {}


class NlaSpec(dict):
    def __init__(
        self,
        nla_class,
        nla_type,
        nla_name,
        nla_flags=0,
        nla_array=False,
        init=None,
    ):
        self.update(
            {
                'class': nla_class,
                'type': nla_type,
                'name': nla_name,
                'nla_flags': nla_flags,
                'nla_array': nla_array,
                'init': init,
            }
        )


class NlaMapAdapter:
    def __init__(self, api_get, api_contains=lambda x: True):
        self.api_get = api_get
        self.api_contains = api_contains
        self.types = None

    def __contains__(self, key):
        return self.api_contains(key)

    def __getitem__(self, key):
        ret = self.api_get(key)
        if isinstance(ret['class'], str):
            ret['class'] = getattr(self.types, ret['class'])
        return ret


class SQLSchema:
    def __init__(self, cls):
        ret = []
        for field in cls.fields:
            if field[0][0] != '_':
                ret.append(
                    (
                        (field[0],),
                        ' '.join(
                            ('BIGINT', cls.sql_constraints.get(field[0], ''))
                        ),
                    )
                )
        for nla_tuple in cls.nla_map:
            if isinstance(nla_tuple[0], basestring):
                nla_name = nla_tuple[0]
                nla_type = nla_tuple[1]
            else:
                nla_name = nla_tuple[1]
                nla_type = nla_tuple[2]
            nla_type = getattr(cls, nla_type, None)
            sql_type = getattr(nla_type, 'sql_type', None)
            if sql_type:
                sql_type = ' '.join(
                    (sql_type, cls.sql_constraints.get(nla_name, ''))
                )
                ret.append(((nla_name,), sql_type))

        for fname, ftype in cls.sql_extra_fields:
            if isinstance(fname, basestring):
                fname = (fname,)
            ret.append((fname, ftype))

        for dcls, prefix in cls.sql_extend:
            for fname, ftype in dcls.sql_schema():
                ret.append(((prefix,) + fname, ftype))

        self.spec = ret
        self.index = []
        self.foreign_keys = []

    def unique_index(self, *index):
        self.index = index
        return self

    def constraint(self, name, spec):
        idx = 0
        for field, tspec in self.spec:
            if field[0] == name:
                break
            idx += 1
        else:
            raise KeyError()
        self.spec[idx] = (field, f'{tspec} {spec}')
        return self

    def foreign_key(self, parent, fields, parent_fields):
        self.foreign_keys.append(
            {
                'fields': fields,
                'parent_fields': parent_fields,
                'parent': parent,
            }
        )
        return self

    def push(self, *spec):
        f_type = spec[-1]
        f_name = spec[:-1]
        self.spec.append((f_name, f_type))
        return self

    def __iter__(self):
        return iter(self.spec)

    def as_dict(self):
        return OrderedDict(self.spec)


class nlmsg_base(dict):
    '''
    Netlink base class. You do not need to inherit it directly, unless
    you're inventing completely new protocol structure.

    Use nlmsg or nla classes.

    The class provides several methods, but often one need to customize
    only `decode()` and `encode()`.
    '''

    fields = ()
    header = ()
    pack = None  # pack pragma
    cell_header = None
    align = 4
    nla_map = {}  # NLA mapping
    sql_constraints = {}
    sql_extra_fields = ()
    sql_extend = ()
    lookup_fallbacks = {}
    nla_flags = 0  # NLA flags
    value_map = {}
    is_nla = False
    prefix = None
    own_parent = False
    header_type = None
    # caches
    __compiled_nla = False
    __compiled_ft = False
    __t_nla_map = None
    __r_nla_map = None
    # schema
    __schema = None

    __slots__ = (
        "_buf",
        "data",
        "chain",
        "offset",
        "length",
        "parent",
        "decoded",
        "_nla_init",
        "_nla_array",
        "_nla_flags",
        "value",
        "_r_value_map",
        "__weakref__",
    )

    def msg_align(self, length):
        return (length + self.align - 1) & ~(self.align - 1)

    def __init__(
        self, data=None, offset=0, length=None, parent=None, init=None
    ):
        global cache_jit
        dict.__init__(self)
        for i in self.fields:
            self[i[0]] = 0  # FIXME: only for number values
        self._buf = None
        self.data = data or bytearray()
        self.offset = offset
        self.length = length or 0
        self.chain = [self]
        if parent is not None:
            # some structures use parents, some not,
            # so don't create cycles without need
            self.parent = parent if self.own_parent else weakref.proxy(parent)
        else:
            self.parent = None
        self.decoded = False
        self._nla_init = init
        self._nla_array = False
        self._nla_flags = self.nla_flags
        self['attrs'] = []
        self.value = NotInitialized
        # work only on non-empty mappings
        if self.nla_map and not self.__class__.__compiled_nla:
            self.compile_nla()
        if self.header:
            self['header'] = {}

    @classmethod
    def sql_schema(cls):
        return SQLSchema(cls)

    @property
    def buf(self):
        logging.error(
            'nlmsg.buf is deprecated:\n%s', ''.join(traceback.format_stack())
        )
        if self._buf is None:
            self._buf = io.BytesIO()
            self._buf.write(self.data[self.offset : self.length or None])
            self._buf.seek(0)
        return self._buf

    def copy(self):
        '''
        Return a decoded copy of the netlink message. Works
        correctly only if the message was encoded, or is
        received from the socket.
        '''
        ret = type(self)(data=self.data, offset=self.offset)
        ret.decode()
        return ret

    def reset(self, buf=None):
        self.data = bytearray()
        self.offset = 0
        self.decoded = False

    def register_clean_cb(self, cb):
        global clean_cbs
        if self.parent is not None:
            return self.parent.register_clean_cb(cb)
        else:
            # get the msg_seq -- if applicable
            seq = self.get('header', {}).get('sequence_number', None)
            if seq is not None and seq not in clean_cbs.__dict__:
                clean_cbs.__dict__[seq] = []
            # attach the callback
            clean_cbs.__dict__[seq].append(cb)

    def unregister_clean_cb(self):
        global clean_cbs
        seq = self.get('header', {}).get('sequence_number', None)
        msf = self.get('header', {}).get('flags', 0)
        if (
            (seq is not None)
            and (not msf & NLM_F_REQUEST)
            and seq in clean_cbs.__dict__
        ):
            for cb in clean_cbs.__dict__[seq]:
                try:
                    cb()
                except:
                    log.error('Cleanup callback fail: %s' % (cb))
                    log.error(traceback.format_exc())
            del clean_cbs.__dict__[seq]

    def _strip_one(self, name):
        for i in tuple(self['attrs']):
            if i[0] == name:
                self['attrs'].remove(i)
        return self

    def strip(self, attrs):
        '''
        Remove an NLA from the attrs chain. The `attrs`
        parameter can be either string, or iterable. In
        the latter case, will be stripped NLAs, specified
        in the provided list.
        '''
        if isinstance(attrs, basestring):
            self._strip_one(attrs)
        else:
            for name in attrs:
                self._strip_one(name)
        return self

    def __ops(self, rvalue, op0, op1):
        if rvalue is None:
            return None
        lvalue = self.getvalue()
        res = self.__class__()
        for key, _ in res.fields:
            del res[key]
        if 'header' in res:
            del res['header']
        if 'value' in res:
            del res['value']
        for key in lvalue:
            if key not in ('header', 'attrs', '__align'):
                if op0 == '__sub__':
                    # operator -, complement
                    if (key not in rvalue) or (lvalue[key] != rvalue[key]):
                        res[key] = lvalue[key]
                elif op0 == '__and__':
                    # operator &, intersection
                    if (key in rvalue) and (lvalue[key] == rvalue[key]):
                        res[key] = lvalue[key]
        if 'attrs' in lvalue:
            res['attrs'] = []
            for attr in lvalue['attrs']:
                if isinstance(attr[1], nlmsg_base):
                    print("recursion")
                    diff = getattr(attr[1], op0)(rvalue.get_attr(attr[0]))
                    if diff is not None:
                        res['attrs'].append([attr[0], diff])
                else:
                    print("fail", type(attr[1]))
                    if op0 == '__sub__':
                        # operator -, complement
                        if rvalue.get_attr(attr[0]) != attr[1]:
                            res['attrs'].append(attr)
                    elif op0 == '__and__':
                        # operator &, intersection
                        if rvalue.get_attr(attr[0]) == attr[1]:
                            res['attrs'].append(attr)
        if 'attrs' in res and not res['attrs']:
            del res['attrs']
        if not res:
            return None
        print(res)
        return res

    def __bool__(self):
        return len(self.keys()) > 0

    def __sub__(self, rvalue):
        '''
        Subjunction operation.
        '''
        return self.__ops(rvalue, '__sub__', '__ne__')

    def __and__(self, rvalue):
        '''
        Conjunction operation.
        '''
        return self.__ops(rvalue, '__and__', '__eq__')

    def __ne__(self, rvalue):
        return not self.__eq__(rvalue)

    def __eq__(self, rvalue):
        '''
        Having nla, we are able to use it in operations like::

            if nla == 'some value':
                ...
        '''
        lvalue = self.getvalue()
        if lvalue is self:
            if isinstance(rvalue, type(self)):
                return (self - rvalue) is None
            if isinstance(rvalue, dict):
                return dict(self) == rvalue
            return False
        return lvalue == rvalue

    @classmethod
    def get_size(self):
        size = 0
        for field in self.fields:
            size += struct.calcsize(field[1])
        return size

    @classmethod
    def nla2name(self, name):
        '''
        Convert NLA name into human-friendly name

        Example: IFLA_ADDRESS -> address

        Requires self.prefix to be set
        '''
        return name[(name.find(self.prefix) + 1) * len(self.prefix) :].lower()

    @classmethod
    def name2nla(self, name):
        '''
        Convert human-friendly name into NLA name

        Example: address -> IFLA_ADDRESS

        Requires self.prefix to be set
        '''
        name = name.upper()
        if name.find(self.prefix) == -1:
            name = "%s%s" % (self.prefix, name)
        return name

    def decode(self):
        '''
        Decode the message. The message should have the `buf`
        attribute initialized. e.g.::

            data = sock.recv(16384)
            msg = ifinfmsg(data)

        If you want to customize the decoding process, override
        the method, but don't forget to call parent's `decode()`::

            class CustomMessage(nlmsg):

                def decode(self):
                    nlmsg.decode(self)
                    ...  # do some custom data tuning
        '''
        offset = self.offset
        global cache_hdr
        global clean_cbs
        # Decode the header
        if self.header is not None:
            ##
            # ~~ self['header'][name] = struct.unpack_from(...)
            #
            # Instead of `struct.unpack()` all the NLA headers, it is
            # much cheaper to cache decoded values. The resulting dict
            # will be not much bigger than some hundreds ov values.
            #
            # The code might look ugly, but line_profiler shows here
            # a notable performance gain.
            #
            # The chain is:
            # dict.get(key, None) or dict.set(unpack(key, ...)) or dict[key]
            #
            # If there is no such key in the dict, get() returns None, and
            # Python executes __setitem__(), which always return None, and
            # then dict[key] is returned.
            #
            # If the key exists, the statement after the first `or` is not
            # executed.
            if self.is_nla:
                key = tuple(self.data[offset : offset + 4])
                self['header'] = (
                    cache_hdr.get(key, None)
                    or (
                        cache_hdr.__setitem__(
                            key,
                            dict(
                                zip(
                                    ('length', 'type'),
                                    struct.unpack_from(
                                        'HH', self.data, offset
                                    ),
                                )
                            ),
                        )
                    )
                    or cache_hdr[key]
                )
                ##
                offset += 4
                self.length = self['header']['length']
            else:
                for name, fmt in self.header:
                    self['header'][name] = struct.unpack_from(
                        fmt, self.data, offset
                    )[0]
                    offset += struct.calcsize(fmt)
                # update length from header
                # it can not be less than 4
                if 'header' in self:
                    self.length = max(self['header']['length'], 4)
        # handle the array case
        if self._nla_array:
            self.setvalue([])
            while offset < self.offset + self.length:
                cell = type(self)(data=self.data, offset=offset, parent=self)
                cell._nla_array = False
                if cell.cell_header is not None:
                    cell.header = cell.cell_header
                cell.decode()
                self.value.append(cell)
                offset += (cell.length + 4 - 1) & ~(4 - 1)
        else:
            self.ft_decode(offset)

        if clean_cbs.__dict__:
            self.unregister_clean_cb()
        self.decoded = True

    def encode(self):
        '''
        Encode the message into the binary buffer::

            msg.encode()
            sock.send(msg.data)

        If you want to customize the encoding process, override
        the method::

            class CustomMessage(nlmsg):

                def encode(self):
                    ...  # do some custom data tuning
                    nlmsg.encode(self)
        '''
        offset = self.offset
        diff = 0
        # reserve space for the header
        if self.header is not None:
            hsize = struct.calcsize(''.join([x[1] for x in self.header]))
            self.data.extend([0] * hsize)
            offset += hsize

        # handle the array case
        if self._nla_array:
            header_type = 1
            for value in self.getvalue():
                cell = type(self)(data=self.data, offset=offset, parent=self)
                cell._nla_array = False

                if cell.cell_header is not None:
                    cell.header = cell.cell_header
                cell.setvalue(value)
                # overwrite header type after calling setvalue
                cell['header']['type'] = self.header_type or (
                    header_type | self._nla_flags
                )
                header_type += 1
                cell.encode()
                offset += (cell.length + 4 - 1) & ~(4 - 1)
        elif self.getvalue() is not None:
            offset, diff = self.ft_encode(offset)
        # write NLA chain
        if self.nla_map:
            offset = self.encode_nlas(offset)
        # calculate the size and write it
        if 'header' in self and self.header is not None:
            self.length = self['header']['length'] = (
                offset - self.offset - diff
            )
            offset = self.offset
            for name, fmt in self.header:
                struct.pack_into(
                    fmt, self.data, offset, self['header'].get(name, 0)
                )
                offset += struct.calcsize(fmt)

    def setvalue(self, value):
        if isinstance(value, dict):
            self.update(value)
            if 'attrs' in value:
                self['attrs'] = []
                for nla_tuple in value['attrs']:
                    nlv = nlmsg_base()
                    nlv.setvalue(nla_tuple[1])
                    self['attrs'].append([nla_tuple[0], nlv.getvalue()])
        else:
            try:
                if value in self.value_map.values():
                    reverse_map = dict(
                        [(x[1], x[0]) for x in self.value_map.items()]
                    )
                    value = reverse_map.get(value, value)
            except TypeError:
                pass
            self['value'] = value
            self.value = value
        return self

    def get_encoded(self, attr, default=None):
        '''
        Return the first encoded NLA by name
        '''
        cells = [i[1] for i in self['attrs'] if i[0] == attr]
        if cells:
            return cells[0]

    def get(self, key, default=None):
        '''
        Universal get() for a netlink message.
        '''
        if isinstance(key, str):
            key = (key,)
        ret = self.get_nested(*key)
        return ret if ret is not None else default

    def get_nested(self, *keys):
        '''
        Return nested NLA or None
        '''
        pointer = self
        for attr in keys:
            if isinstance(pointer, nlmsg_base):
                # descendant nodes: NLA or fields
                #
                nla = attr
                if pointer.prefix:
                    nla = pointer.name2nla(attr)
                else:
                    nla = attr.upper()
                # try to descend to NLA
                value = pointer.get_attr(nla)
                # try to descend to a field
                if value is None and attr in pointer:
                    value = pointer[attr]
                # replace pointer
                pointer = value
            elif isinstance(pointer, dict):
                # descendant nodes: dict values
                #
                pointer = pointer.get(attr)
            else:
                # stop descending; search failed
                return
        return pointer

    def get_attr(self, attr, default=None):
        '''
        Return the first NLA with that name or None
        '''
        try:
            attrs = self.get_attrs(attr)
        except KeyError:
            return default
        if attrs:
            return attrs[0]
        else:
            return default

    def get_attrs(self, attr):
        '''
        Return attrs by name or an empty list
        '''
        return [i[1] for i in self['attrs'] if i[0] == attr]

    def nla(self, attr=None, default=NotInitialized):
        ''' '''
        if default is NotInitialized:
            response = nlmsg_base()
            del response['value']
            del response['attrs']
            response.value = None
        chain = self.get('attrs', [])
        if attr is not None:
            chain = [i.nla for i in chain if i.name == attr]
        else:
            chain = [i.nla for i in chain]
        if chain:
            for link in chain:
                link.chain = chain
            response = chain[0]
        return response

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.chain[key]
        if key == 'value' and key not in self:
            return NotInitialized
        return dict.__getitem__(self, key)

    def __delitem__(self, key):
        if key == 'value' and key not in self:
            return
        return dict.__delitem__(self, key)

    def __setstate__(self, state):
        return self.load(state)

    def __reduce__(self):
        return (type(self), (), self.dump())

    def load(self, dump):
        '''
        Load packet from a dict::

            ipr = IPRoute()
            lo = ipr.link('dump', ifname='lo')[0]
            msg_type, msg_value = type(lo), lo.dump()
            ...
            lo = msg_type()
            lo.load(msg_value)

        The same methods -- `dump()`/`load()` -- implement the
        pickling protocol for the nlmsg class, see `__reduce__()`
        and `__setstate__()`.
        '''
        if isinstance(dump, dict):
            for k, v in dump.items():
                if k == 'header':
                    self['header'].update(dump['header'])
                else:
                    self[k] = v
        else:
            self.setvalue(dump)
        return self

    def dump(self):
        '''
        Dump packet as a dict
        '''
        a = self.getvalue()
        if isinstance(a, dict):
            ret = {}
            for k, v in a.items():
                if k == 'header':
                    ret['header'] = dict(a['header'])
                elif k == 'attrs':
                    ret['attrs'] = attrs = []
                    for i in a['attrs']:
                        if isinstance(i[1], nlmsg_base):
                            attrs.append([i[0], i[1].dump()])
                        elif isinstance(i[1], set):
                            attrs.append([i[0], tuple(i[1])])
                        else:
                            attrs.append([i[0], i[1]])
                else:
                    ret[k] = v
        else:
            ret = a
        return ret

    def getvalue(self):
        '''
        Atomic NLAs return their value in the 'value' field,
        not as a dictionary. Complex NLAs return whole dictionary.
        '''
        if (
            self._nla_array
            and len(self.value)
            and hasattr(self.value[0], 'getvalue')
        ):
            return [x.getvalue() for x in self.value]

        if self.value != NotInitialized:
            # value decoded by custom decoder
            return self.value

        if 'value' in self and self['value'] != NotInitialized:
            # raw value got by generic decoder
            return self.value_map.get(self['value'], self['value'])

        return self

    def compile_nla(self):
        # Bug-Url: https://github.com/svinota/pyroute2/issues/980
        # Bug-Url: https://github.com/svinota/pyroute2/pull/981
        if isinstance(self.nla_map, NlaMapAdapter):
            self.nla_map.types = self
            self.__class__.__t_nla_map = self.nla_map
            self.__class__.__r_nla_map = self.nla_map
            self.__class__.__compiled_nla = True
            return
        elif isinstance(self.nla_map, dict):
            if isinstance(self.nla_map['decode'], NlaMapAdapter):
                self.nla_map['decode'].types = self
            if isinstance(self.nla_map['encode'], NlaMapAdapter):
                self.nla_map['encode'].types = self
            self.__class__.__t_nla_map = self.nla_map['decode']
            self.__class__.__r_nla_map = self.nla_map['encode']
            self.__class__.__compiled_nla = True
            return

        # clean up NLA mappings
        t_nla_map = {}
        r_nla_map = {}

        # fix nla flags
        nla_map = []
        for item in self.nla_map:
            if not isinstance(item[-1], int):
                item = list(item)
                item.append(0)
            nla_map.append(item)

        # detect, whether we have pre-defined keys
        if not isinstance(nla_map[0][0], int):
            # create enumeration
            nla_types = enumerate((i[0] for i in nla_map))
            # that's a little bit tricky, but to reduce
            # the required amount of code in modules, we have
            # to jump over the head
            zipped = [
                (k[1][0], k[0][0], k[0][1], k[0][2])
                for k in zip(nla_map, nla_types)
            ]
        else:
            zipped = nla_map

        for key, name, nla_class, nla_flags in zipped:
            # it is an array
            if nla_class[0] == '*':
                nla_class = nla_class[1:]
                nla_array = True
            else:
                nla_array = False
            # are there any init call in the string?
            lb = nla_class.find('(')
            rb = nla_class.find(')')
            if 0 < lb < rb:
                init = nla_class[lb + 1 : rb]
                nla_class = nla_class[:lb]
            else:
                init = None
            # lookup NLA class
            if nla_class == 'recursive':
                nla_class = type(self)
            elif nla_class == 'nested':
                nla_class = type(self)
                nla_flags |= NLA_F_NESTED
            else:
                nla_class = getattr(self, nla_class)
            # update mappings
            prime = {
                'class': nla_class,
                'type': key,
                'name': name,
                'nla_flags': nla_flags,
                'nla_array': nla_array,
                'init': init,
            }
            t_nla_map[key] = r_nla_map[name] = prime

        self.__class__.__t_nla_map = t_nla_map
        self.__class__.__r_nla_map = r_nla_map
        self.__class__.__compiled_nla = True

    def valid_nla(self, nla):
        return nla in self.__class__.__r_nla_map.keys()

    def encode_nlas(self, offset):
        '''
        Encode the NLA chain. Should not be called manually, since
        it is called from `encode()` routine.
        '''
        r_nla_map = self.__class__.__r_nla_map
        for i in range(len(self['attrs'])):
            cell = self['attrs'][i]
            if cell[0] in r_nla_map:
                prime = r_nla_map[cell[0]]
                msg_class = prime['class']
                # is it a class or a function?
                if isinstance(msg_class, types.FunctionType):
                    # if it is a function -- use it to get the class
                    msg_class = msg_class(self, value=cell[1])
                # encode NLA
                nla_instance = msg_class(
                    data=self.data,
                    offset=offset,
                    parent=self,
                    init=prime['init'],
                )
                nla_instance._nla_flags |= prime['nla_flags']
                if isinstance(cell, tuple) and len(cell) > 2:
                    nla_instance._nla_flags |= cell[2]
                nla_instance._nla_array = prime['nla_array']
                nla_instance.setvalue(cell[1])
                # overwrite header type after calling setvalue
                nla_instance['header']['type'] = (
                    prime['type'] | nla_instance._nla_flags
                )
                try:
                    nla_instance.encode()
                except:
                    raise
                else:
                    nla_instance.decoded = True
                    self['attrs'][i] = nla_slot(prime['name'], nla_instance)
                offset += (nla_instance.length + 4 - 1) & ~(4 - 1)
        return offset

    def decode_nlas(self, offset):
        '''
        Decode the NLA chain. Should not be called manually, since
        it is called from `decode()` routine.
        '''
        t_nla_map = self.__class__.__t_nla_map
        while offset - self.offset <= self.length - 4:
            nla_instance = None
            # pick the length and the type
            (length, base_msg_type) = struct.unpack_from(
                'HH', self.data, offset
            )
            # first two bits of msg_type are flags:
            msg_type = base_msg_type & ~(NLA_F_NESTED | NLA_F_NET_BYTEORDER)
            # rewind to the beginning
            length = min(max(length, 4), (self.length - offset + self.offset))
            # we have a mapping for this NLA
            if msg_type in t_nla_map:
                prime = t_nla_map[msg_type]
                # get the class
                msg_class = t_nla_map[msg_type]['class']
                # is it a class or a function?
                if isinstance(msg_class, types.FunctionType):
                    # if it is a function -- use it to get the class
                    msg_class = msg_class(self, data=self.data, offset=offset)
                # decode NLA
                nla_instance = msg_class(
                    data=self.data,
                    offset=offset,
                    parent=self,
                    length=length,
                    init=prime['init'],
                )
                nla_instance._nla_array = prime['nla_array']
                nla_instance._nla_flags = base_msg_type & (
                    NLA_F_NESTED | NLA_F_NET_BYTEORDER
                )
                name = prime['name']
            else:
                name = 'UNKNOWN'
                nla_instance = nla_base(
                    data=self.data, offset=offset, length=length
                )

            self['attrs'].append(nla_slot(name, nla_instance))
            offset += (length + 4 - 1) & ~(4 - 1)


##
# 8<---------------------------------------------------------------------
#
# NLMSG fields codecs, mixin classes
#
class nlmsg_decoder_generic(object):
    def ft_decode(self, offset):
        global cache_fmt
        for name, fmt in self.fields:
            ##
            # ~~ size = struct.calcsize(efmt)
            #
            # The use of the cache gives here a tiny performance
            # improvement, but it is an improvement anyways
            #
            size = (
                cache_fmt.get(fmt, None)
                or cache_fmt.__setitem__(fmt, struct.calcsize(fmt))
                or cache_fmt[fmt]
            )
            ##
            value = struct.unpack_from(fmt, self.data, offset)
            offset += size
            if len(value) == 1:
                self[name] = value[0]
            else:
                self[name] = value
        # read NLA chain
        if self.nla_map:
            offset = (offset + 4 - 1) & ~(4 - 1)
            try:
                self.decode_nlas(offset)
            except Exception as e:
                log.warning(traceback.format_exc())
                raise NetlinkNLADecodeError(e)
        else:
            del self['attrs']
        if self['value'] is NotInitialized:
            del self['value']


class nlmsg_decoder_string(object):
    def ft_decode(self, offset):
        (value,) = struct.unpack_from(
            '%is' % (self.length - 4), self.data, offset
        )
        if self.zstring == 1:
            self['value'] = value.strip(b'\0')
        else:
            self['value'] = value


class nlmsg_decoder_struct(object):
    def ft_decode(self, offset):
        names = []
        fmt = ''
        for field in self.fields:
            names.append(field[0])
            fmt += field[1]
        value = struct.unpack_from(fmt, self.data, offset)
        values = list(value)
        for name in names:
            if name[0] != '_':
                self[name] = values.pop(0)
        # read NLA chain
        if self.nla_map:
            offset = (offset + 4 - 1) & ~(4 - 1)
            try:
                self.decode_nlas(offset)
            except Exception as e:
                log.warning(traceback.format_exc())
                raise NetlinkNLADecodeError(e)
        else:
            del self['attrs']
        if self['value'] is NotInitialized:
            del self['value']


class nlmsg_encoder_generic(object):
    def ft_encode(self, offset):
        for name, fmt in self.fields:
            value = self[name]

            if fmt == 's':
                length = len(value or '') + self.zstring
                efmt = '%is' % (length)
            else:
                length = struct.calcsize(fmt)
                efmt = fmt

            self.data.extend([0] * length)

            # in python3 we should force it
            if sys.version[0] == '3':
                if isinstance(value, str):
                    value = bytes(value, 'utf-8')
                elif isinstance(value, float):
                    value = int(value)
            elif sys.version[0] == '2':
                if isinstance(value, unicode):
                    value = value.encode('utf-8')

            try:
                if fmt[-1] == 'x':
                    struct.pack_into(efmt, self.data, offset)
                elif type(value) in (list, tuple, set):
                    struct.pack_into(efmt, self.data, offset, *value)
                else:
                    struct.pack_into(efmt, self.data, offset, value)
            except struct.error:
                log.error(''.join(traceback.format_stack()))
                log.error(traceback.format_exc())
                log.error("error pack: %s %s %s" % (efmt, value, type(value)))
                raise

            offset += length

        diff = ((offset + 4 - 1) & ~(4 - 1)) - offset
        offset += diff
        self.data.extend([0] * diff)

        return offset, diff


#
# 8<---------------------------------------------------------------------
##


class nla_slot(object):
    __slots__ = ("cell",)

    def __init__(self, name, value):
        self.cell = (name, value)

    def try_to_decode(self):
        try:
            cell = self.cell[1]
            if not cell.decoded:
                cell.decode()
            return True
        except Exception:
            log.warning("decoding %s" % (self.cell[0]))
            log.warning(traceback.format_exc())
            return False

    def get_value(self):
        cell = self.cell[1]
        if self.try_to_decode():
            return cell.getvalue()
        else:
            return cell.data[cell.offset : cell.offset + cell.length]

    def get_flags(self):
        if self.try_to_decode():
            return self.cell[1]._nla_flags
        return None

    @property
    def name(self):
        return self.cell[0]

    @property
    def value(self):
        return self.get_value()

    @property
    def nla(self):
        self.try_to_decode()
        return self.cell[1]

    def __getitem__(self, key):
        if key == 1:
            return self.get_value()
        elif key == 0:
            return self.cell[0]
        elif isinstance(key, slice):
            s = list(self.cell.__getitem__(key))
            if self.cell[1] in s:
                s[s.index(self.cell[1])] = self.get_value()
            return s
        else:
            raise IndexError(key)

    def __repr__(self):
        if self.get_flags():
            return repr((self.cell[0], self.get_value(), self.get_flags()))
        return repr((self.cell[0], self.get_value()))


##
# 8<---------------------------------------------------------------------
#
# NLA base classes
#
class nla_header(object):
    __slots__ = ()
    is_nla = True
    header = (('length', 'H'), ('type', 'H'))


class nla_base(
    nla_header, nlmsg_base, nlmsg_encoder_generic, nlmsg_decoder_generic
):
    '''
    Generic NLA base class.
    '''

    __slots__ = ()
    zstring = 0


class nla_base_string(
    nla_header, nlmsg_base, nlmsg_encoder_generic, nlmsg_decoder_string
):
    '''
    NLA base class, string decoder.
    '''

    __slots__ = ()
    fields = [('value', 's')]
    zstring = 0


class nla_base_struct(
    nla_header, nlmsg_base, nlmsg_encoder_generic, nlmsg_decoder_struct
):
    '''
    NLA base class, packed struct decoder.
    '''

    __slots__ = ()


#
# 8<---------------------------------------------------------------------
##


class nlmsg_atoms(object):
    '''
    A collection of base NLA types
    '''

    __slots__ = ()

    class none(nla_base):
        '''
        'none' type is used to skip decoding of NLA. You can
        also use 'hex' type to dump NLA's content.
        '''

        __slots__ = ()

        def decode(self):
            nla_base.decode(self)
            self.value = None

    class flag(nla_base):
        '''
        'flag' type is used to denote attrs that have no payload
        '''

        __slots__ = ()

        fields = []

        def decode(self):
            nla_base.decode(self)
            self.value = True

    class uint8(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', 'B')]

    class uint16(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', 'H')]

    class uint32(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', 'I')]

    class uint64(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', 'Q')]

    class int8(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', 'b')]

    class int16(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', 'h')]

    class int32(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', 'i')]

    class int64(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', 'q')]

    class be8(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', '>B')]

    class be16(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', '>H')]

    class be32(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', '>I')]

    class be64(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', '>Q')]

    class sbe8(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', '>b')]

    class sbe16(nla_base):
        __slots__ = ()
        sql_type = 'INTEGER'

        fields = [('value', '>h')]

    class sbe32(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', '>i')]

    class sbe64(nla_base):
        __slots__ = ()
        sql_type = 'BIGINT'

        fields = [('value', '>q')]

    class ipXaddr(nla_base_string):
        __slots__ = ()
        sql_type = 'TEXT'

        family = None

        def encode(self):
            self['value'] = inet_pton(self.family, self.value)
            nla_base_string.encode(self)

        def decode(self):
            nla_base_string.decode(self)
            self.value = inet_ntop(self.family, self['value'])

    class ip4addr(ipXaddr):
        '''
        Explicit IPv4 address type class.
        '''

        __slots__ = ()

        family = AF_INET

    class ip6addr(ipXaddr):
        '''
        Explicit IPv6 address type class.
        '''

        __slots__ = ()
        family = AF_INET6

    class ipaddr(nla_base_string):
        '''
        This class is used to decode IP addresses according to
        the family. Socket library currently supports only two
        families, AF_INET and AF_INET6.

        We do not specify here the string size, it will be
        calculated in runtime.
        '''

        __slots__ = ()
        sql_type = 'TEXT'

        def ft_encode(self, offset):
            # use real provided family, not implicit
            if self.value.find(':') > -1:
                family = AF_INET6
            else:
                family = AF_INET
            self['value'] = inet_pton(family, self.value)
            return nla_base_string.ft_encode(self, offset)

        def ft_decode(self, offset):
            nla_base_string.ft_decode(self, offset)
            # use real provided family, not implicit
            if self.length > 8:
                family = AF_INET6
            else:
                family = AF_INET
            self.value = inet_ntop(family, self['value'])

    class target(nla_base_string):
        '''
        A universal target class. The target type depends on the msg
        family:

        * AF_INET: IPv4 addr, string: "127.0.0.1"
        * AF_INET6: IPv6 addr, string: "::1"
        * AF_MPLS: MPLS labels, 0 .. k: [{"label": 0x20, "ttl": 16}, ...]
        '''

        __slots__ = ()
        sql_type = 'TEXT'
        family = None
        own_parent = True

        def get_family(self):
            if self.family is not None:
                return self.family
            pointer = self
            while pointer.parent is not None:
                pointer = pointer.parent
            return pointer.get('family', AF_UNSPEC)

        def encode(self):
            family = self.get_family()
            if family in (AF_INET, AF_INET6):
                self['value'] = inet_pton(family, self.value)
            elif family == AF_MPLS:
                self['value'] = b''
                if isinstance(self.value, (set, list, tuple)):
                    labels = self.value
                else:
                    if 'label' in self:
                        labels = [
                            {
                                'label': self.get('label', 0),
                                'tc': self.get('tc', 0),
                                'bos': self.get('bos', 0),
                                'ttl': self.get('ttl', 0),
                            }
                        ]
                    else:
                        labels = []
                for record in labels:
                    label = (
                        (record.get('label', 0) << 12)
                        | (record.get('tc', 0) << 9)
                        | ((1 if record.get('bos') else 0) << 8)
                        | record.get('ttl', 0)
                    )
                    self['value'] += struct.pack('>I', label)
            else:
                raise TypeError('socket family not supported')
            nla_base_string.encode(self)

        def decode(self):
            nla_base_string.decode(self)
            family = self.get_family()
            if family in (AF_INET, AF_INET6):
                self.value = inet_ntop(family, self['value'])
            elif family == AF_MPLS:
                self.value = []
                for i in range(len(self['value']) // 4):
                    label = struct.unpack(
                        '>I', self['value'][i * 4 : i * 4 + 4]
                    )[0]
                    record = {
                        'label': (label & 0xFFFFF000) >> 12,
                        'tc': (label & 0x00000E00) >> 9,
                        'bos': (label & 0x00000100) >> 8,
                        'ttl': label & 0x000000FF,
                    }
                    self.value.append(record)
            else:
                raise TypeError('socket family not supported')

    class mpls_target(target):
        __slots__ = ()

        family = AF_MPLS

    class l2addr(nla_base):
        '''
        Decode MAC address.
        '''

        __slots__ = ()
        sql_type = 'TEXT'

        fields = [('value', '=6s')]

        def encode(self):
            self['value'] = struct.pack(
                'BBBBBB', *[int(i, 16) for i in self.value.split(':')]
            )
            nla_base.encode(self)

        def decode(self):
            nla_base.decode(self)
            self.value = ':'.join(
                '%02x' % (i) for i in struct.unpack('BBBBBB', self['value'])
            )

    class lladdr(nla_base_string):
        '''
        Decode link layer address: a MAC, IPv4 or IPv6 address. This type
        depends on the link layer address length:

        * 6: MAC addr, string: "52:ff:ff:ff:ff:03"
        * 4: IPv4 addr, string: "127.0.0.1"
        * 16: IPv6 addr, string: "::1"
        * any other length: hex dump
        '''

        __slots__ = ()
        sql_type = 'TEXT'

        def encode(self):
            if ':' in self.value:
                if len(self.value) == 17 and '::' not in self.value:
                    self['value'] = struct.pack(
                        'BBBBBB', *[int(i, 16) for i in self.value.split(':')]
                    )
                else:
                    self['value'] = inet_pton(AF_INET6, self.value)
            elif '.' in self.value:
                self['value'] = inet_pton(AF_INET, self.value)
            else:
                raise TypeError('Unsupported value {}'.format(self.value))
            nla_base_string.encode(self)

        def decode(self):
            nla_base_string.decode(self)
            if len(self['value']) == 6:
                self.value = ':'.join(
                    '%02x' % (i)
                    for i in struct.unpack('BBBBBB', self['value'])
                )
            elif len(self['value']) == 4:
                self.value = inet_ntop(AF_INET, self['value'])
            elif len(self['value']) == 16:
                self.value = inet_ntop(AF_INET6, self['value'])
            elif len(self['value']) == 0:
                self.value = ''
            else:
                # unknown / invalid lladdr
                # extract data for the whole message
                offset = self.parent.offset
                length = self.parent.length
                data = self.parent.data[offset : offset + length]
                # report
                logging.warning(
                    'unknown or invalid lladdr size, please report to: '
                    'https://github.com/svinota/pyroute2/issues/717 \n'
                    'packet data: %s',
                    hexdump(data),
                )
                # continue with hex dump as the value
                self.value = hexdump(self['value'])

    class hex(nla_base_string):
        '''
        Represent NLA's content with header as hex string.
        '''

        __slots__ = ()

        def decode(self):
            nla_base_string.decode(self)
            self.value = hexdump(self['value'])

    class array(nla_base_string):
        '''
        Array of simple data type
        '''

        __slots__ = ("_fmt",)
        own_parent = True

        @property
        def fmt(self):
            # try to get format from parent
            # work only with elementary types
            if getattr(self, "_fmt", None) is not None:
                return self._fmt
            try:
                fclass = getattr(self.parent, self._nla_init)
                self._fmt = fclass.fields[0][1]
            except Exception:
                self._fmt = self._nla_init
            return self._fmt

        def encode(self):
            fmt = '%s%i%s' % (self.fmt[:-1], len(self.value), self.fmt[-1:])
            self['value'] = struct.pack(fmt, *self.value)
            nla_base_string.encode(self)

        def decode(self):
            nla_base_string.decode(self)
            data_length = len(self['value'])
            element_size = struct.calcsize(self.fmt)
            array_size = data_length // element_size
            trail = (data_length % element_size) or -data_length
            data = self['value'][:-trail]
            fmt = '%s%i%s' % (self.fmt[:-1], array_size, self.fmt[-1:])
            self.value = struct.unpack(fmt, data)

    class cdata(nla_base_string):
        '''
        Binary data
        '''

        __slots__ = ()

    class string(nla_base_string):
        '''
        UTF-8 string.
        '''

        __slots__ = ()
        sql_type = 'TEXT'

        def encode(self):
            if isinstance(self['value'], str) and sys.version[0] == '3':
                self['value'] = bytes(self['value'], 'utf-8')
            nla_base_string.encode(self)

        def decode(self):
            nla_base_string.decode(self)
            self.value = self['value']
            if sys.version_info[0] >= 3:
                try:
                    self.value = self.value.decode('utf-8')
                except UnicodeDecodeError:
                    pass  # Failed to decode, keep undecoded value

    class asciiz(string):
        '''
        Zero-terminated string.
        '''

        __slots__ = ()
        zstring = 1

    # FIXME: support NLA_FLAG and NLA_MSECS as well.
    #
    # aliases to support standard kernel attributes:
    #
    binary = cdata  # NLA_BINARY
    nul_string = asciiz  # NLA_NUL_STRING


##
# 8<---------------------------------------------------------------------
#
# NLA base classes
#
class nla(nla_base, nlmsg_atoms):
    '''
    Main NLA class
    '''

    __slots__ = ()

    def decode(self):
        nla_base.decode(self)
        del self['header']


class nla_string(nla_base_string, nlmsg_atoms):
    '''
    NLA + string decoder
    '''

    __slots__ = ()

    def decode(self):
        nla_base_string.decode(self)
        del self['header']


class nla_struct(nla_base_struct, nlmsg_atoms):
    '''
    NLA + packed struct decoder
    '''

    __slots__ = ()

    def decode(self):
        nla_base_struct.decode(self)
        del self['header']


#
# 8<---------------------------------------------------------------------
##


class nlmsg(
    nlmsg_base, nlmsg_encoder_generic, nlmsg_decoder_generic, nlmsg_atoms
):
    '''
    Main netlink message class
    '''

    __slots__ = ()

    header = (
        ('length', 'I'),
        ('type', 'H'),
        ('flags', 'H'),
        ('sequence_number', 'I'),
        ('pid', 'I'),
    )


class nlmsgerr(nlmsg):
    '''
    Extended ack error message
    '''

    __slots__ = ()

    fields = (('error', 'i'),)

    nla_map = (
        ('NLMSGERR_ATTR_UNUSED', 'none'),
        ('NLMSGERR_ATTR_MSG', 'asciiz'),
        ('NLMSGERR_ATTR_OFFS', 'uint32'),
        ('NLMSGERR_ATTR_COOKIE', 'uint8'),
    )


class genlmsg(nlmsg):
    '''
    Generic netlink message
    '''

    __slots__ = ()

    fields = (('cmd', 'B'), ('version', 'B'), ('reserved', 'H'))


class ctrlmsg(genlmsg):
    '''
    Netlink control message
    '''

    __slots__ = ()

    # FIXME: to be extended
    nla_map = (
        ('CTRL_ATTR_UNSPEC', 'none'),
        ('CTRL_ATTR_FAMILY_ID', 'uint16'),
        ('CTRL_ATTR_FAMILY_NAME', 'asciiz'),
        ('CTRL_ATTR_VERSION', 'uint32'),
        ('CTRL_ATTR_HDRSIZE', 'uint32'),
        ('CTRL_ATTR_MAXATTR', 'uint32'),
        ('CTRL_ATTR_OPS', '*ops'),
        ('CTRL_ATTR_MCAST_GROUPS', '*mcast_groups'),
        ('CTRL_ATTR_POLICY', 'policy_nest'),
        ('CTRL_ATTR_OP_POLICY', 'command_nest'),
        ('CTRL_ATTR_OP', 'uint32'),
    )

    class ops(nla):
        __slots__ = ()

        nla_map = (
            ('CTRL_ATTR_OP_UNSPEC', 'none'),
            ('CTRL_ATTR_OP_ID', 'uint32'),
            ('CTRL_ATTR_OP_FLAGS', 'uint32'),
        )

    class mcast_groups(nla):
        __slots__ = ()

        nla_map = (
            ('CTRL_ATTR_MCAST_GRP_UNSPEC', 'none'),
            ('CTRL_ATTR_MCAST_GRP_NAME', 'asciiz'),
            ('CTRL_ATTR_MCAST_GRP_ID', 'uint32'),
        )

    class policy_nest(nla):
        __slots__ = ()

        nla_map = {
            'decode': NlaMapAdapter(
                lambda x: NlaSpec('attribute_nest', x, f'POLICY({x})')
            ),
            'encode': NlaMapAdapter(
                lambda x: NlaSpec('attribute_nest', int(x[7:-1]), x)
            ),
        }

        class attribute_nest(nla):
            __slots__ = ()

            nla_map = {
                'decode': NlaMapAdapter(
                    lambda x: NlaSpec('nl_policy_type_attr', x, f'ATTR({x})')
                ),
                'encode': NlaMapAdapter(
                    lambda x: NlaSpec('nl_policy_type_attr', int(x[5:-1]), x)
                ),
            }

            class nl_policy_type_attr(nla):
                __slots__ = ()

                nla_map = (
                    ('NL_POLICY_TYPE_ATTR_UNSPEC', 'none'),
                    ('NL_POLICY_TYPE_ATTR_TYPE', 'uint32'),
                    ('NL_POLICY_TYPE_ATTR_MIN_VALUE_S', 'int64'),
                    ('NL_POLICY_TYPE_ATTR_MAX_VALUE_S', 'int64'),
                    ('NL_POLICY_TYPE_ATTR_MIN_VALUE_U', 'int64'),
                    ('NL_POLICY_TYPE_ATTR_MAX_VALUE_U', 'int64'),
                    ('NL_POLICY_TYPE_ATTR_MIN_LENGTH', 'uint32'),
                    ('NL_POLICY_TYPE_ATTR_MAX_LENGTH', 'uint32'),
                    ('NL_POLICY_TYPE_ATTR_POLICY_IDX', 'uint32'),
                    ('NL_POLICY_TYPE_ATTR_POLICY_MAXTYPE', 'uint32'),
                    ('NL_POLICY_TYPE_ATTR_BITFIELD32_MASK', 'uint32'),
                    ('NL_POLICY_TYPE_ATTR_PAD', 'uint64'),
                    ('NL_POLICY_TYPE_ATTR_MASK', 'uint64'),
                )

    class command_nest(nla):
        __slots__ = ()

        nla_map = {
            'decode': NlaMapAdapter(
                lambda x: NlaSpec('command_nest_attrs', x, f'OP({x})')
            ),
            'encode': NlaMapAdapter(
                lambda x: NlaSpec('command_nest_attrs', int(x[3:-1]), x)
            ),
        }

        class command_nest_attrs(nla):
            __slots__ = ()

            nla_map = (
                ('CTRL_ATTR_POLICY_UNSPEC', 'none'),
                ('CTRL_ATTR_POLICY_DO', 'uint32'),
                ('CTRL_ATTR_POLICY_DUMP', 'uint32'),
            )
