from pyroute2.common import map_namespace
from pyroute2.netlink import nla, nlmsg

# neighbor cache entry flags
NTF_USE = 0x01
NTF_SELF = 0x02
NTF_MASTER = 0x04
NTF_PROXY = 0x08
NTF_EXT_LEARNED = 0x10
NTF_ROUTER = 0x80

# neighbor cache entry states
NUD_INCOMPLETE = 0x01
NUD_REACHABLE = 0x02
NUD_STALE = 0x04
NUD_DELAY = 0x08
NUD_PROBE = 0x10
NUD_FAILED = 0x20

# dummy states
NUD_NOARP = 0x40
NUD_PERMANENT = 0x80
NUD_NONE = 0x00

(NTF_NAMES, NTF_VALUES) = map_namespace('NTF_', globals())
(NUD_NAMES, NUD_VALUES) = map_namespace('NUD_', globals())
flags = dict([(x[0][4:].lower(), x[1]) for x in NTF_NAMES.items()])
states = dict([(x[0][4:].lower(), x[1]) for x in NUD_NAMES.items()])


def states_a2n(s):
    # parse state string
    ss = s.split(',')
    ret = 0
    for state in ss:
        state = state.upper()
        if not state.startswith('NUD_'):
            state = 'NUD_' + state
        ret |= NUD_NAMES[state]
    return ret


class ndmsg(nlmsg):
    '''
    ARP cache update message

    C structure::

        struct ndmsg {
            unsigned char ndm_family;
            int           ndm_ifindex;  /* Interface index */
            __u16         ndm_state;    /* State */
            __u8          ndm_flags;    /* Flags */
            __u8          ndm_type;
        };

    Cache info structure::

        struct nda_cacheinfo {
            __u32         ndm_confirmed;
            __u32         ndm_used;
            __u32         ndm_updated;
            __u32         ndm_refcnt;
        };
    '''

    __slots__ = ()

    prefix = 'NDA_'

    fields = (
        ('family', 'B'),
        ('__pad', '3x'),
        ('ifindex', 'i'),
        ('state', 'H'),
        ('flags', 'B'),
        ('ndm_type', 'B'),
    )

    # Please note, that nla_map creates implicit
    # enumeration. In this case it will be:
    #
    # NDA_UNSPEC = 0
    # NDA_DST = 1
    # NDA_LLADDR = 2
    # NDA_CACHEINFO = 3
    # NDA_PROBES = 4
    # ...
    #
    nla_map = (
        ('NDA_UNSPEC', 'none'),
        ('NDA_DST', 'ipaddr'),
        ('NDA_LLADDR', 'lladdr'),
        ('NDA_CACHEINFO', 'cacheinfo'),
        ('NDA_PROBES', 'uint32'),
        ('NDA_VLAN', 'uint16'),
        ('NDA_PORT', 'be16'),
        ('NDA_VNI', 'uint32'),
        ('NDA_IFINDEX', 'uint32'),
        ('NDA_MASTER', 'uint32'),
        ('NDA_LINK_NETNSID', 'uint32'),
        ('NDA_SRC_VNI', 'uint32'),
    )

    class cacheinfo(nla):
        __slots__ = ()

        fields = (
            ('ndm_confirmed', 'I'),
            ('ndm_used', 'I'),
            ('ndm_updated', 'I'),
            ('ndm_refcnt', 'I'),
        )
