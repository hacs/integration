'''
RTNetlink: network setup
========================

RTNL is a netlink protocol, used to get and set information
about different network objects -- addresses, routes, interfaces
etc.

RTNL protocol-specific data in messages depends on the object
type. E.g., complete packet with the interface address information::

    nlmsg header:
        + uint32 length
        + uint16 type
        + uint16 flags
        + uint32 sequence number
        + uint32 pid
    ifaddrmsg structure:
        + unsigned char ifa_family
        + unsigned char ifa_prefixlen
        + unsigned char ifa_flags
        + unsigned char ifa_scope
        + uint32 ifa_index
    [ optional NLA tree ]

NLA for this kind of packets can be of type IFA_ADDRESS, IFA_LOCAL
etc. -- please refer to the corresponding source.

Other objects types require different structures, sometimes really
complex. All these structures are described in sources.

---------------------------

Module contents:

'''

from pyroute2.common import map_namespace

#  RTnetlink multicast group flags (for use with bind())
RTMGRP_NONE = 0x0
RTMGRP_LINK = 0x1
RTMGRP_NOTIFY = 0x2
RTMGRP_NEIGH = 0x4
RTMGRP_TC = 0x8
RTMGRP_IPV4_IFADDR = 0x10
RTMGRP_IPV4_MROUTE = 0x20
RTMGRP_IPV4_ROUTE = 0x40
RTMGRP_IPV4_RULE = 0x80
RTMGRP_IPV6_IFADDR = 0x100
RTMGRP_IPV6_MROUTE = 0x200
RTMGRP_IPV6_ROUTE = 0x400
RTMGRP_IPV6_IFINFO = 0x800
RTMGRP_DECnet_IFADDR = 0x1000
RTMGRP_NOP2 = 0x2000
RTMGRP_DECnet_ROUTE = 0x4000
RTMGRP_DECnet_RULE = 0x8000
RTMGRP_NOP4 = 0x10000
RTMGRP_IPV6_PREFIX = 0x20000
RTMGRP_IPV6_RULE = 0x40000
RTMGRP_MPLS_ROUTE = 0x4000000

# multicast group ids (for use with {add,drop}_membership)
RTNLGRP_NONE = 0
RTNLGRP_LINK = 1
RTNLGRP_NOTIFY = 2
RTNLGRP_NEIGH = 3
RTNLGRP_TC = 4
RTNLGRP_IPV4_IFADDR = 5
RTNLGRP_IPV4_MROUTE = 6
RTNLGRP_IPV4_ROUTE = 7
RTNLGRP_IPV4_RULE = 8
RTNLGRP_IPV6_IFADDR = 9
RTNLGRP_IPV6_MROUTE = 10
RTNLGRP_IPV6_ROUTE = 11
RTNLGRP_IPV6_IFINFO = 12
RTNLGRP_DECnet_IFADDR = 13
RTNLGRP_NOP2 = 14
RTNLGRP_DECnet_ROUTE = 15
RTNLGRP_DECnet_RULE = 16
RTNLGRP_NOP4 = 17
RTNLGRP_IPV6_PREFIX = 18
RTNLGRP_IPV6_RULE = 19
RTNLGRP_ND_USEROPT = 20
RTNLGRP_PHONET_IFADDR = 21
RTNLGRP_PHONET_ROUTE = 22
RTNLGRP_DCB = 23
RTNLGRP_IPV4_NETCONF = 24
RTNLGRP_IPV6_NETCONF = 25
RTNLGRP_MDB = 26
RTNLGRP_MPLS_ROUTE = 27
RTNLGRP_NSID = 28
RTNLGRP_MPLS_NETCONF = 29
RTNLGRP_IPV4_MROUTE_R = 30
RTNLGRP_IPV6_MROUTE_R = 31

# Types of messages
# RTM_BASE = 16
RTM_NEWLINK = 16
RTM_DELLINK = 17
RTM_GETLINK = 18
RTM_SETLINK = 19
RTM_NEWADDR = 20
RTM_DELADDR = 21
RTM_GETADDR = 22
RTM_NEWROUTE = 24
RTM_DELROUTE = 25
RTM_GETROUTE = 26
RTM_NEWNEIGH = 28
RTM_DELNEIGH = 29
RTM_GETNEIGH = 30
RTM_NEWRULE = 32
RTM_DELRULE = 33
RTM_GETRULE = 34
RTM_NEWQDISC = 36
RTM_DELQDISC = 37
RTM_GETQDISC = 38
RTM_NEWTCLASS = 40
RTM_DELTCLASS = 41
RTM_GETTCLASS = 42
RTM_NEWTFILTER = 44
RTM_DELTFILTER = 45
RTM_GETTFILTER = 46
RTM_NEWACTION = 48
RTM_DELACTION = 49
RTM_GETACTION = 50
RTM_NEWPREFIX = 52
RTM_GETMULTICAST = 58
RTM_GETANYCAST = 62
RTM_NEWNEIGHTBL = 64
RTM_GETNEIGHTBL = 66
RTM_SETNEIGHTBL = 67
RTM_NEWNDUSEROPT = 68
RTM_NEWADDRLABEL = 72
RTM_DELADDRLABEL = 73
RTM_GETADDRLABEL = 74
RTM_GETDCB = 78
RTM_SETDCB = 79
RTM_NEWNETCONF = 80
RTM_DELNETCONF = 81
RTM_GETNETCONF = 82
RTM_NEWMDB = 84
RTM_DELMDB = 85
RTM_GETMDB = 86
RTM_NEWNSID = 88
RTM_DELNSID = 89
RTM_GETNSID = 90
RTM_NEWSTATS = 92
RTM_GETSTATS = 94
RTM_NEWCACHEREPORT = 96
RTM_NEWLINKPROP = 108
RTM_DELLINKPROP = 109
RTM_GETLINKPROP = 110
# fake internal message types
RTM_NEWNETNS = 500
RTM_DELNETNS = 501
RTM_GETNETNS = 502
(RTM_NAMES, RTM_VALUES) = map_namespace('RTM_', globals())

TC_H_INGRESS = 0xFFFFFFF1
TC_H_CLSACT = TC_H_INGRESS
TC_H_ROOT = 0xFFFFFFFF


RTMGRP_DEFAULTS = (
    RTMGRP_IPV4_IFADDR
    | RTMGRP_IPV6_IFADDR
    | RTMGRP_IPV4_ROUTE
    | RTMGRP_IPV6_ROUTE
    | RTMGRP_IPV4_RULE
    | RTMGRP_IPV6_RULE
    | RTMGRP_NEIGH
    | RTMGRP_LINK
    | RTMGRP_TC
    | RTMGRP_MPLS_ROUTE
)

encap_type = {'unspec': 0, 'mpls': 1, 0: 'unspec', 1: 'mpls'}

rtypes = {
    'RTN_UNSPEC': 0,
    'RTN_UNICAST': 1,  # Gateway or direct route
    'RTN_LOCAL': 2,  # Accept locally
    'RTN_BROADCAST': 3,  # Accept locally as broadcast
    #                        send as broadcast
    'RTN_ANYCAST': 4,  # Accept locally as broadcast,
    #                        but send as unicast
    'RTN_MULTICAST': 5,  # Multicast route
    'RTN_BLACKHOLE': 6,  # Drop
    'RTN_UNREACHABLE': 7,  # Destination is unreachable
    'RTN_PROHIBIT': 8,  # Administratively prohibited
    'RTN_THROW': 9,  # Not in this table
    'RTN_NAT': 10,  # Translate this address
    'RTN_XRESOLVE': 11,
}  # Use external resolver
# normalized
rt_type = dict(
    [(x[0][4:].lower(), x[1]) for x in rtypes.items()]
    + [(x[1], x[0][4:].lower()) for x in rtypes.items()]
)

rtprotos = {
    'RTPROT_UNSPEC': 0,
    'RTPROT_REDIRECT': 1,  # Route installed by ICMP redirects;
    #                        not used by current IPv4
    'RTPROT_KERNEL': 2,  # Route installed by kernel
    'RTPROT_BOOT': 3,  # Route installed during boot
    'RTPROT_STATIC': 4,  # Route installed by administrator
    # Values of protocol >= RTPROT_STATIC are not
    # interpreted by kernel;
    # keep in sync with iproute2 !
    'RTPROT_GATED': 8,  # gated
    'RTPROT_RA': 9,  # RDISC/ND router advertisements
    'RTPROT_MRT': 10,  # Merit MRT
    'RTPROT_ZEBRA': 11,  # Zebra
    'RTPROT_BIRD': 12,  # BIRD
    'RTPROT_DNROUTED': 13,  # DECnet routing daemon
    'RTPROT_XORP': 14,  # XORP
    'RTPROT_NTK': 15,  # Netsukuku
    'RTPROT_DHCP': 16,
}  # DHCP client
# normalized
rt_proto = dict(
    [(x[0][7:].lower(), x[1]) for x in rtprotos.items()]
    + [(x[1], x[0][7:].lower()) for x in rtprotos.items()]
)

rtscopes = {
    'RT_SCOPE_UNIVERSE': 0,
    'RT_SCOPE_SITE': 200,
    'RT_SCOPE_LINK': 253,
    'RT_SCOPE_HOST': 254,
    'RT_SCOPE_NOWHERE': 255,
}
# normalized
rt_scope = dict(
    [(x[0][9:].lower(), x[1]) for x in rtscopes.items()]
    + [(x[1], x[0][9:].lower()) for x in rtscopes.items()]
)
