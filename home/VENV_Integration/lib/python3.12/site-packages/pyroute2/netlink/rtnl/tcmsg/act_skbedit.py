'''
skbedit
+++++++

Usage::

    from pyroute2 import IPRoute

    # Assume you are working with eth1 interface
    IFNAME = "eth1"

    ipr = IPRoute()
    ifindex = ipr.link_lookup(ifname=IFNAME)

    # First create parent qdisc
    ipr.tc("add", "htb", index=ifindex, handle=0x10000)

    # Then add a matchall filter with skbedit action
    # Simple action example
    action = {"kind": "skbedit",
              "priority": 0x10001 # Also known as "1:1" in TC format
              }
    ipr.tc("add-filter", "matchall", index=ifindex, parent=0x10000,
           prio=1, action=action)

    # Extended action example
    action = {"kind": "skbedit",
              "priority": 0x10001, # Also known as "1:1" in TC format
              "mark": 0x1337,
              "mask": 0xFFFFFFFF,
              "ptype": "host"
              }
    ipr.tc("add-filter", "matchall", index=ifindex, parent=0x10000,
           prio=1, action=action)

NOTES:
    Here is the list of all supported options::
    - mark: integer
    - mask: integer
    - priority: integer
    - ptype: "host", "otherhost", "broadcast" or "multicast"
    - queue: integer
'''

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.common import tc_actions

# Packet types defined in if_packet.h
PACKET_HOST = 0
PACKET_BROADCAST = 1
PACKET_MULTICAST = 2
PACKET_OTHERHOST = 3


def convert_ptype(value):
    types = {
        'host': PACKET_HOST,
        'otherhost': PACKET_OTHERHOST,
        'broadcast': PACKET_BROADCAST,
        'multicast': PACKET_MULTICAST,
    }

    res = types.get(value.lower())
    if res is not None:
        return res
    raise ValueError(
        'Invalid ptype specified! See tc-skbedit man ' 'page for valid values.'
    )


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (
        ('priority', 'TCA_SKBEDIT_PRIORITY'),
        ('queue', 'TCA_SKBEDIT_QUEUE_MAPPING'),
        ('mark', 'TCA_SKBEDIT_MARK'),
        ('ptype', 'TCA_SKBEDIT_PTYPE'),
        ('mask', 'TCA_SKBEDIT_MASK'),
    )

    # Assign TCA_SKBEDIT_PARMS first
    parms = {}
    parms['action'] = tc_actions['pipe']
    ret['attrs'].append(['TCA_SKBEDIT_PARMS', parms])

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            if k == 'ptype':
                r = convert_ptype(r)
            ret['attrs'].append([v, r])

    return ret


class options(nla):
    nla_map = (
        ('TCA_SKBEDIT_UNSPEC', 'none'),
        ('TCA_SKBEDIT_TM', 'tca_parse_tm'),
        ('TCA_SKBEDIT_PARMS', 'tca_parse_parms'),
        ('TCA_SKBEDIT_PRIORITY', 'uint32'),
        ('TCA_SKBEDIT_QUEUE_MAPPING', 'uint16'),
        ('TCA_SKBEDIT_MARK', 'uint32'),
        ('TCA_SKBEDIT_PAD', 'hex'),
        ('TCA_SKBEDIT_PTYPE', 'uint16'),
        ('TCA_SKBEDIT_MASK', 'uint32'),
        ('TCA_SKBEDIT_FLAGS', 'uint64'),
    )

    class tca_parse_parms(nla):
        # As described in tc_mpls.h, it uses
        # generic TC action fields
        fields = (
            ('index', 'I'),
            ('capab', 'I'),
            ('action', 'i'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
        )

    class tca_parse_tm(nla):
        # See struct tcf_t
        fields = (
            ('install', 'Q'),
            ('lastuse', 'Q'),
            ('expires', 'Q'),
            ('firstuse', 'Q'),
        )
