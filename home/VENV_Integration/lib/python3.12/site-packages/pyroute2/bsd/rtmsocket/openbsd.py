from pyroute2.bsd.pf_route import (
    bsdmsg,
    if_announcemsg,
    if_msg,
    ifa_msg,
    rt_msg,
)

RTM_ADD = 0x1  # Add Route
RTM_DELETE = 0x2  # Delete Route
RTM_CHANGE = 0x3  # Change Metrics or flags
RTM_GET = 0x4  # Report Metrics
RTM_LOSING = 0x5  # Kernel Suspects Partitioning
RTM_REDIRECT = 0x6  # Told to use different route
RTM_MISS = 0x7  # Lookup failed on this address
RTM_LOCK = 0x8  # Fix specified metrics
RTM_RESOLVE = 0xB  # Req to resolve dst to LL addr
RTM_NEWADDR = 0xC  # Address being added to iface
RTM_DELADDR = 0xD  # Address being removed from iface
RTM_IFINFO = 0xE  # Iface going up/down etc
RTM_IFANNOUNCE = 0xF  # Iface arrival/departure
RTM_DESYNC = 0x10  # route socket buffer overflow
RTM_INVALIDATE = 0x10  # Invalidate cache of L2 route
RTM_BFD = 0x12  # bidirectional forwarding detection
RTM_PROPOSAL = 0x13  # proposal for netconfigd


class RTMSocketBase(object):
    msg_map = {
        RTM_ADD: rt_msg,
        RTM_DELETE: rt_msg,
        RTM_CHANGE: rt_msg,
        RTM_GET: rt_msg,
        RTM_LOSING: rt_msg,
        RTM_REDIRECT: rt_msg,
        RTM_MISS: rt_msg,
        RTM_LOCK: rt_msg,
        RTM_RESOLVE: rt_msg,
        RTM_NEWADDR: ifa_msg,
        RTM_DELADDR: ifa_msg,
        RTM_IFINFO: if_msg,
        RTM_IFANNOUNCE: if_announcemsg,
        RTM_DESYNC: bsdmsg,
        RTM_INVALIDATE: bsdmsg,
        RTM_BFD: bsdmsg,
        RTM_PROPOSAL: bsdmsg,
    }
