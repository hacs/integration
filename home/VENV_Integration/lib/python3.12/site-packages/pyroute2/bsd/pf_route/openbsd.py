from pyroute2.common import map_namespace
from pyroute2.netlink import nlmsg_base

IFNAMSIZ = 16

IFF_UP = 0x1
IFF_BROADCAST = 0x2
IFF_DEBUG = 0x4
IFF_LOOPBACK = 0x8
IFF_POINTOPOINT = 0x10
IFF_STATICARP = 0x20
IFF_RUNNING = 0x40
IFF_NOARP = 0x80
IFF_PROMISC = 0x100
IFF_ALLMULTI = 0x200
IFF_OACTIVE = 0x400
IFF_SIMPLEX = 0x800
IFF_LINK0 = 0x1000
IFF_LINK1 = 0x2000
IFF_LINK2 = 0x4000
IFF_MULTICAST = 0x8000
(IFF_NAMES, IFF_VALUES) = map_namespace('IFF', globals())


class bsdmsg(nlmsg_base):
    __slots__ = ()
    header = (
        ('length', 'H'),
        ('version', 'B'),
        ('type', 'B'),
        ('hdrlen', 'H'),
    )


class if_msg(bsdmsg):
    __slots__ = ()
    fields = (
        ('ifm_index', 'H'),
        ('ifm_tableid', 'H'),
        ('ifm_pad1', 'B'),
        ('ifm_pad2', 'B'),
        ('ifm_addrs', 'i'),
        ('ifm_flags', 'i'),
        ('ifm_xflags', 'i'),
        ('ifi_type', 'B'),
        ('ifi_addrlen', 'B'),
        ('ifi_hdrlen', 'B'),
        ('ifi_link_state', 'B'),
        ('ifi_mtu', 'I'),
        ('ifi_metric', 'I'),
        ('ifi_rdomain', 'I'),
        ('ifi_baudrate', 'Q'),
        ('ifi_ipackets', 'Q'),
        ('ifi_ierrors', 'Q'),
        ('ifi_opackets', 'Q'),
        ('ifi_oerrors', 'Q'),
        ('ifi_collisions', 'Q'),
        ('ifi_ibytes', 'Q'),
        ('ifi_obytes', 'Q'),
        ('ifi_imcasts', 'Q'),
        ('ifi_omcasts', 'Q'),
        ('ifi_iqdrops', 'Q'),
        ('ifi_oqdrops', 'Q'),
        ('ifi_noproto', 'Q'),
        ('ifi_capabilities', 'I'),
        ('ifu_sec', 'Q'),
        ('ifu_usec', 'I'),
    )


class rt_msg_base(bsdmsg):
    __slots__ = ()
    fields = (
        ('rtm_index', 'H'),
        ('rtm_tableid', 'H'),
        ('rtm_priority', 'B'),
        ('rtm_mpls', 'B'),
        ('rtm_addrs', 'i'),
        ('rtm_flags', 'i'),
        ('rtm_fmask', 'i'),
        ('rtm_pid', 'I'),
        ('rtm_seq', 'i'),
        ('rtm_errno', 'i'),
        ('rtm_inits', 'I'),
        ('rmx_pksent', 'Q'),
        ('rmx_expire', 'q'),
        ('rmx_locks', 'I'),
        ('rmx_mtu', 'I'),
        ('rmx_refcnt', 'I'),
        ('rmx_hopcount', 'I'),
        ('rmx_recvpipe', 'I'),
        ('rmx_sendpipe', 'I'),
        ('rmx_ssthresh', 'I'),
        ('rmx_rtt', 'I'),
        ('rmx_rttvar', 'I'),
        ('rmx_pad', 'I'),
    )
    sockaddr_offset = 96

    ifa_slots = {
        0: ('DST', 'rt_slot_addr'),
        1: ('GATEWAY', 'rt_slot_addr'),
        2: ('NETMASK', 'rt_slot_addr'),
        3: ('GENMASK', 'hex'),
        4: ('IFP', 'rt_slot_ifp'),
        5: ('IFA', 'rt_slot_addr'),
        6: ('AUTHOR', 'hex'),
        7: ('BRD', 'rt_slot_addr'),
        8: ('SRC', 'rt_slot_addr'),
        9: ('SRCMASK', 'rt_slot_addr'),
        10: ('LABEL', 'hex'),
        11: ('BFD', 'hex'),
        12: ('DNS', 'hex'),
        13: ('STATIC', 'hex'),
        14: ('SEARCH', 'hex'),
    }


class ifa_msg_base(bsdmsg):
    __slots__ = ()
    fields = (
        ('ifam_index', 'H'),
        ('ifam_tableid', 'H'),
        ('ifam_pad1', 'B'),
        ('ifam_pad2', 'B'),
        ('rtm_addrs', 'i'),
        ('ifam_flags', 'i'),
        ('ifam_metric', 'i'),
    )
    sockaddr_offset = 24


class ifma_msg_base(bsdmsg):
    __slots__ = ()
    fields = (('rtm_addrs', 'i'), ('ifmam_flags', 'i'), ('ifmam_index', 'H'))
    sockaddr_offset = 16


class if_announcemsg(bsdmsg):
    __slots__ = ()
    fields = (
        ('ifan_index', 'H'),
        ('ifan_what', 'H'),
        ('ifan_name', '%is' % IFNAMSIZ),
    )

    def decode(self):
        bsdmsg.decode(self)
        self['ifan_name'] = self['ifan_name'].strip(b'\0').decode('ascii')
