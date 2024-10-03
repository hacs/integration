import importlib
import logging
import os
import pkgutil
import struct
import sys
from socket import AF_INET, AF_INET6

from pyroute2 import config
from pyroute2.common import basestring, map_namespace
from pyroute2.config import AF_BRIDGE
from pyroute2.netlink import NLA_F_NESTED, nla, nlmsg, nlmsg_atoms
from pyroute2.netlink.rtnl.ifinfmsg.plugins import (
    bond,
    can,
    geneve,
    gtp,
    ipoib,
    ipvlan,
    team,
    tun,
    tuntap,
    vlan,
    vrf,
    vti,
    vti6,
    vxlan,
    xfrm,
)
from pyroute2.netlink.rtnl.iw_event import iw_event

log = logging.getLogger(__name__)

# it's simpler to double constants here, than to change all the
# module layout; but it is a subject of the future refactoring
RTM_NEWLINK = 16
RTM_DELLINK = 17
#


##
#
# tuntap flags
#
IFT_TUN = 0x0001
IFT_TAP = 0x0002
IFT_NO_PI = 0x1000
IFT_ONE_QUEUE = 0x2000
IFT_VNET_HDR = 0x4000
IFT_TUN_EXCL = 0x8000
IFT_MULTI_QUEUE = 0x0100
IFT_ATTACH_QUEUE = 0x0200
IFT_DETACH_QUEUE = 0x0400
# read-only
IFT_PERSIST = 0x0800
IFT_NOFILTER = 0x1000

##
#
# normal flags
#
IFF_UP = 0x1  # interface is up
IFF_BROADCAST = 0x2  # broadcast address valid
IFF_DEBUG = 0x4  # turn on debugging
IFF_LOOPBACK = 0x8  # is a loopback net
IFF_POINTOPOINT = 0x10  # interface is has p-p link
IFF_NOTRAILERS = 0x20  # avoid use of trailers
IFF_RUNNING = 0x40  # interface RFC2863 OPER_UP
IFF_NOARP = 0x80  # no ARP protocol
IFF_PROMISC = 0x100  # receive all packets
IFF_ALLMULTI = 0x200  # receive all multicast packets
IFF_MASTER = 0x400  # master of a load balancer
IFF_SLAVE = 0x800  # slave of a load balancer
IFF_MULTICAST = 0x1000  # Supports multicast
IFF_PORTSEL = 0x2000  # can set media type
IFF_AUTOMEDIA = 0x4000  # auto media select active
IFF_DYNAMIC = 0x8000  # dialup device with changing addresses
IFF_LOWER_UP = 0x10000  # driver signals L1 up
IFF_DORMANT = 0x20000  # driver signals dormant
IFF_ECHO = 0x40000  # echo sent packets

(IFF_NAMES, IFF_VALUES) = map_namespace('IFF', globals())

IFF_MASK = (
    IFF_UP
    | IFF_DEBUG
    | IFF_NOTRAILERS
    | IFF_NOARP
    | IFF_PROMISC
    | IFF_ALLMULTI
)

IFF_VOLATILE = (
    IFF_LOOPBACK
    | IFF_POINTOPOINT
    | IFF_BROADCAST
    | IFF_ECHO
    | IFF_MASTER
    | IFF_SLAVE
    | IFF_RUNNING
    | IFF_LOWER_UP
    | IFF_DORMANT
)

##
#
# gre flags
#
GRE_ACK = 0x0080
GRE_REC = 0x0700
GRE_STRICT = 0x0800
GRE_SEQ = 0x1000
GRE_KEY = 0x2000
GRE_ROUTING = 0x4000
GRE_CSUM = 0x8000

(GRE_NAMES, GRE_VALUES) = map_namespace('GRE_', globals())

##
#
# vlan filter flags
#
BRIDGE_VLAN_INFO_MASTER = 0x1  # operate on bridge device
BRIDGE_VLAN_INFO_PVID = 0x2  # ingress untagged
BRIDGE_VLAN_INFO_UNTAGGED = 0x4  # egress untagged
BRIDGE_VLAN_INFO_RANGE_BEGIN = 0x8  # range start
BRIDGE_VLAN_INFO_RANGE_END = 0x10  # range end
BRIDGE_VLAN_INFO_BRENTRY = 0x20  # global bridge vlan entry
(BRIDGE_VLAN_NAMES, BRIDGE_VLAN_VALUES) = map_namespace(
    'BRIDGE_VLAN_INFO', globals()
)

BRIDGE_VLAN_TUNNEL_UNSPEC = 0
BRIDGE_VLAN_TUNNEL_ID = 1
BRIDGE_VLAN_TUNNEL_VID = 2
BRIDGE_VLAN_TUNNEL_FLAGS = 3
BRIDGE_VLAN_TUNNEL_MAX = 4

BRIDGE_FLAGS_MASTER = 1
BRIDGE_FLAGS_SELF = 2
(BRIDGE_FLAGS_NAMES, BRIDGE_FLAGS_VALUES) = map_namespace(
    'BRIDGE_FLAGS', globals()
)

##
#
# XDP flags
#
XDP_FLAGS_UPDATE_IF_NOEXIST = 1 << 0
XDP_FLAGS_SKB_MODE = 1 << 1
XDP_FLAGS_DRV_MODE = 1 << 2
XDP_FLAGS_HW_MODE = 1 << 3
XDP_FLAGS_REPLACE = 1 << 4
XDP_FLAGS_MODES = XDP_FLAGS_SKB_MODE | XDP_FLAGS_DRV_MODE | XDP_FLAGS_HW_MODE
XDP_FLAGS_MASK = (
    XDP_FLAGS_UPDATE_IF_NOEXIST | XDP_FLAGS_MODES | XDP_FLAGS_REPLACE
)

(XDP_FLAGS_NAMES, XDP_FLAGS_VALUES) = map_namespace('XDP_FLAGS', globals())

states = (
    'UNKNOWN',
    'NOTPRESENT',
    'DOWN',
    'LOWERLAYERDOWN',
    'TESTING',
    'DORMANT',
    'UP',
)
state_by_name = {i[1]: i[0] for i in enumerate(states)}
state_by_code = dict(enumerate(states))
stats_names = (
    'rx_packets',
    'tx_packets',
    'rx_bytes',
    'tx_bytes',
    'rx_errors',
    'tx_errors',
    'rx_dropped',
    'tx_dropped',
    'multicast',
    'collisions',
    'rx_length_errors',
    'rx_over_errors',
    'rx_crc_errors',
    'rx_frame_errors',
    'rx_fifo_errors',
    'rx_missed_errors',
    'tx_aborted_errors',
    'tx_carrier_errors',
    'tx_fifo_errors',
    'tx_heartbeat_errors',
    'tx_window_errors',
    'rx_compressed',
    'tx_compressed',
)


def load_plugins_by_path(path):
    plugins = {}
    files = set(
        [
            x.split('.')[0]
            for x in filter(
                lambda x: x.endswith(('.py', '.pyc', '.pyo')), os.listdir(path)
            )
            if not x.startswith('_')
        ]
    )
    sys.path.append(path)
    for name in files:
        try:
            module = __import__(name, globals(), locals(), [], 0)
            register_kind = getattr(module, 'register_kind', name)
            plugins[register_kind] = getattr(module, register_kind)
        except:
            pass
    sys.path.pop()
    return plugins


def load_plugins_by_pkg(pkg):
    plugins = {}
    plugin_modules = {
        name: name.split('.')[-1]
        for loader, name, ispkg in pkgutil.iter_modules(
            path=pkg.__path__, prefix=pkg.__name__ + '.'
        )
    }

    # Hack to make it compatible with pyinstaller
    # plugin loading will work with and without pyinstaller
    # Inspired on:
    # https://github.com/webcomics/dosage/blob/master/dosagelib/loader.py
    # see: https://github.com/pyinstaller/pyinstaller/issues/1905
    importers = map(pkgutil.get_importer, pkg.__path__)
    toc = set()

    for importer in importers:
        if hasattr(importer, 'toc'):
            toc |= importer.toc

    for element in toc:
        if element.startswith(pkg.__name__) and element != pkg.__name__:
            plugin_modules[element] = element.split('.')[-1]

    for mod_path, mod_name in plugin_modules.items():
        if mod_name.startswith('_'):
            continue
        module = importlib.import_module(mod_path)
        register_kind = getattr(module, 'register_kind', mod_name)
        plugins[register_kind] = getattr(module, register_kind)

    return plugins


data_plugins = {}

for module in (
    bond,
    can,
    geneve,
    gtp,
    ipvlan,
    team,
    tuntap,
    tun,
    vlan,
    vrf,
    vti,
    vti6,
    vxlan,
    xfrm,
    ipoib,
):
    name = module.__name__.split('.')[-1]
    data_plugins[name] = getattr(module, name)

for pkg in config.data_plugins_pkgs:
    data_plugins.update(load_plugins_by_pkg(pkg))

for path in config.data_plugins_path:
    data_plugins.update(load_plugins_by_path(path))


class ifla_bridge_id(nla):
    fields = [('value', '=8s')]

    def encode(self):
        r_prio = struct.pack('H', self['prio'])
        r_addr = struct.pack(
            'BBBBBB', *[int(i, 16) for i in self['addr'].split(':')]
        )
        self['value'] = r_prio + r_addr
        nla.encode(self)

    def decode(self):
        nla.decode(self)
        r_prio = self['value'][:2]
        r_addr = self['value'][2:]
        self.value = {
            'prio': struct.unpack('H', r_prio)[0],
            'addr': ':'.join(
                '%02x' % (i) for i in struct.unpack('BBBBBB', r_addr)
            ),
        }


class protinfo_bridge(nla):
    prefix = 'IFLA_BRPORT_'
    nla_map = (
        ('IFLA_BRPORT_UNSPEC', 'none'),
        ('IFLA_BRPORT_STATE', 'uint8'),
        ('IFLA_BRPORT_PRIORITY', 'uint16'),
        ('IFLA_BRPORT_COST', 'uint32'),
        ('IFLA_BRPORT_MODE', 'uint8'),
        ('IFLA_BRPORT_GUARD', 'uint8'),
        ('IFLA_BRPORT_PROTECT', 'uint8'),
        ('IFLA_BRPORT_FAST_LEAVE', 'uint8'),
        ('IFLA_BRPORT_LEARNING', 'uint8'),
        ('IFLA_BRPORT_UNICAST_FLOOD', 'uint8'),
        ('IFLA_BRPORT_PROXYARP', 'uint8'),
        ('IFLA_BRPORT_LEARNING_SYNC', 'uint8'),
        ('IFLA_BRPORT_PROXYARP_WIFI', 'uint8'),
        ('IFLA_BRPORT_ROOT_ID', 'br_id'),
        ('IFLA_BRPORT_BRIDGE_ID', 'br_id'),
        ('IFLA_BRPORT_DESIGNATED_PORT', 'uint16'),
        ('IFLA_BRPORT_DESIGNATED_COST', 'uint16'),
        ('IFLA_BRPORT_ID', 'uint16'),
        ('IFLA_BRPORT_NO', 'uint16'),
        ('IFLA_BRPORT_TOPOLOGY_CHANGE_ACK', 'uint8'),
        ('IFLA_BRPORT_CONFIG_PENDING', 'uint8'),
        ('IFLA_BRPORT_MESSAGE_AGE_TIMER', 'uint64'),
        ('IFLA_BRPORT_FORWARD_DELAY_TIMER', 'uint64'),
        ('IFLA_BRPORT_HOLD_TIMER', 'uint64'),
        ('IFLA_BRPORT_FLUSH', 'flag'),
        ('IFLA_BRPORT_MULTICAST_ROUTER', 'uint8'),
        ('IFLA_BRPORT_PAD', 'uint64'),
        ('IFLA_BRPORT_MCAST_FLOOD', 'uint8'),
        ('IFLA_BRPORT_MCAST_TO_UCAST', 'uint8'),
        ('IFLA_BRPORT_VLAN_TUNNEL', 'uint8'),
        ('IFLA_BRPORT_BCAST_FLOOD', 'uint8'),
        ('IFLA_BRPORT_GROUP_FWD_MASK', 'uint16'),
        ('IFLA_BRPORT_NEIGH_SUPPRESS', 'uint8'),
        ('IFLA_BRPORT_ISOLATED', 'uint8'),
        ('IFLA_BRPORT_BACKUP_PORT', 'uint32'),
        ('IFLA_BRPORT_MRP_RING_OPEN', 'uint8'),
        ('IFLA_BRPORT_MRP_IN_OPEN', 'uint8'),
    )

    class br_id(ifla_bridge_id):
        pass


class macvx_data(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_MACVLAN_UNSPEC', 'none'),
        ('IFLA_MACVLAN_MODE', 'mode'),
        ('IFLA_MACVLAN_FLAGS', 'flags'),
        ('IFLA_MACVLAN_MACADDR_MODE', 'macaddr_mode'),
        ('IFLA_MACVLAN_MACADDR', 'l2addr'),
        ('IFLA_MACVLAN_MACADDR_DATA', 'macaddr_data'),
        ('IFLA_MACVLAN_MACADDR_COUNT', 'uint32'),
    )

    class mode(nlmsg_atoms.uint32):
        value_map = {
            0: 'none',
            1: 'private',
            2: 'vepa',
            4: 'bridge',
            8: 'passthru',
            16: 'source',
        }

    class flags(nlmsg_atoms.uint16):
        value_map = {0: 'none', 1: 'nopromisc'}

    class macaddr_mode(nlmsg_atoms.uint32):
        value_map = {0: 'add', 1: 'del', 2: 'flush', 3: 'set'}

    class macaddr_data(nla):
        nla_map = ((4, 'IFLA_MACVLAN_MACADDR', 'l2addr'),)


class iptnl_data(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_IPIP_UNSPEC', 'none'),
        ('IFLA_IPIP_LINK', 'uint32'),
        ('IFLA_IPIP_LOCAL', 'ip4addr'),
        ('IFLA_IPIP_REMOTE', 'ip4addr'),
        ('IFLA_IPIP_TTL', 'uint8'),
        ('IFLA_IPIP_TOS', 'uint8'),
        ('IFLA_IPIP_ENCAP_LIMIT', 'uint8'),
        ('IFLA_IPIP_FLOWINFO', 'be32'),
        ('IFLA_IPIP_FLAGS', 'uint32'),
        ('IFLA_IPIP_PROTO', 'uint8'),
        ('IFLA_IPIP_PMTUDISC', 'uint8'),
        ('IFLA_IPIP_6RD_PREFIX', 'ip6addr'),
        ('IFLA_IPIP_6RD_RELAY_PREFIX', 'ip4addr'),
        ('IFLA_IPIP_6RD_PREFIXLEN', 'uint16'),
        ('IFLA_IPIP_6RD_RELAY_PREFIXLEN', 'uint16'),
        ('IFLA_IPIP_ENCAP_TYPE', 'uint16'),
        ('IFLA_IPIP_ENCAP_FLAGS', 'uint16'),
        ('IFLA_IPIP_ENCAP_SPORT', 'be16'),
        ('IFLA_IPIP_ENCAP_DPORT', 'be16'),
        ('IFLA_IPIP_COLLECT_METADATA', 'flag'),
        ('IFLA_IPIP_FWMARK', 'uint32'),
    )


class ifinfbase(object):
    '''
    Network interface message.

    C structure::

        struct ifinfomsg {
            unsigned char  ifi_family; /* AF_UNSPEC */
            unsigned short ifi_type;   /* Device type */
            int            ifi_index;  /* Interface index */
            unsigned int   ifi_flags;  /* Device flags  */
            unsigned int   ifi_change; /* change mask */
        };
    '''

    prefix = 'IFLA_'

    #
    # Changed from PRIMARY KEY to NOT NULL to support multiple
    # targets in one table, so we can collect info from multiple
    # systems.
    #
    # To provide data integrity one should use foreign keys,
    # but when you create a foreign key using interfaces as
    # the parent table, create also a unique index on
    # the fields specified in the foreign key definition.
    #
    # E.g.
    #
    # CREATE TABLE interfaces (f_target TEXT NOT NULL,
    #                          f_index INTEGER NOT NULL, ...)
    # CREATE TABLE routes (f_target TEXT NOT NULL,
    #                      f_RTA_OIF INTEGER, ...
    #                      FOREIGN KEY (f_target, f_RTA_OIF)
    #                      REFERENCES interfaces(f_target, f_index))
    # CREATE UNIQUE INDEX if_idx ON interfaces(f_target, f_index)
    #
    sql_constraints = {'index': 'NOT NULL'}
    sql_extra_fields = (('state', 'TEXT'),)
    lookup_fallbacks = {'index': 'ifname'}

    fields = (
        ('family', 'B'),
        ('__align', 'x'),
        ('ifi_type', 'H'),
        ('index', 'i'),
        ('flags', 'I'),
        ('change', 'I'),
    )

    nla_map = (
        ('IFLA_UNSPEC', 'none'),
        ('IFLA_ADDRESS', 'l2addr'),
        ('IFLA_BROADCAST', 'l2addr'),
        ('IFLA_IFNAME', 'asciiz'),
        ('IFLA_MTU', 'uint32'),
        ('IFLA_LINK', 'uint32'),
        ('IFLA_QDISC', 'asciiz'),
        ('IFLA_STATS', 'ifstats'),
        ('IFLA_COST', 'hex'),
        ('IFLA_PRIORITY', 'hex'),
        ('IFLA_MASTER', 'uint32'),
        ('IFLA_WIRELESS', 'wireless'),
        ('IFLA_PROTINFO', 'protinfo'),
        ('IFLA_TXQLEN', 'uint32'),
        ('IFLA_MAP', 'ifmap'),
        ('IFLA_WEIGHT', 'hex'),
        ('IFLA_OPERSTATE', 'state'),
        ('IFLA_LINKMODE', 'uint8'),
        ('IFLA_LINKINFO', 'ifinfo'),
        ('IFLA_NET_NS_PID', 'uint32'),
        ('IFLA_IFALIAS', 'asciiz'),
        ('IFLA_NUM_VF', 'uint32'),
        ('IFLA_VFINFO_LIST', 'vflist'),
        ('IFLA_STATS64', 'ifstats64'),
        ('IFLA_VF_PORTS', 'hex'),
        ('IFLA_PORT_SELF', 'hex'),
        ('IFLA_AF_SPEC', 'af_spec'),
        ('IFLA_GROUP', 'uint32'),
        ('IFLA_NET_NS_FD', 'netns_fd'),
        ('IFLA_EXT_MASK', 'uint32'),
        ('IFLA_PROMISCUITY', 'uint32'),
        ('IFLA_NUM_TX_QUEUES', 'uint32'),
        ('IFLA_NUM_RX_QUEUES', 'uint32'),
        ('IFLA_CARRIER', 'uint8'),
        ('IFLA_PHYS_PORT_ID', 'hex'),
        ('IFLA_CARRIER_CHANGES', 'uint32'),
        ('IFLA_PHYS_SWITCH_ID', 'hex'),
        ('IFLA_LINK_NETNSID', 'int32'),
        ('IFLA_PHYS_PORT_NAME', 'asciiz'),
        ('IFLA_PROTO_DOWN', 'uint8'),
        ('IFLA_GSO_MAX_SEGS', 'uint32'),
        ('IFLA_GSO_MAX_SIZE', 'uint32'),
        ('IFLA_PAD', 'hex'),
        ('IFLA_XDP', 'xdp'),
        ('IFLA_EVENT', 'uint32'),
        ('IFLA_NEW_NETNSID', 'be32'),
        ('IFLA_IF_NETNSID', 'uint32'),
        ('IFLA_CARRIER_UP_COUNT', 'uint32'),
        ('IFLA_CARRIER_DOWN_COUNT', 'uint32'),
        ('IFLA_NEW_IFINDEX', 'uint32'),
        ('IFLA_MIN_MTU', 'uint32'),
        ('IFLA_MAX_MTU', 'uint32'),
        ('IFLA_PROP_LIST', 'proplist'),
        ('IFLA_ALT_IFNAME', 'asciiz'),
        ('IFLA_PERM_ADDRESS', 'hex'),
        ('IFLA_PROTO_DOWN_REASON', 'down_reason'),
        ('IFLA_PARENT_DEV_NAME', 'asciiz'),
        ('IFLA_PARENT_DEV_BUS_NAME', 'asciiz'),
        ('IFLA_GRO_MAX_SIZE', 'uint32'),
        ('IFLA_TSO_MAX_SIZE', 'uint32'),
        ('IFLA_TSO_MAX_SEGS', 'uint32'),
    )

    @staticmethod
    def flags2names(flags, mask=0xFFFFFFFF):
        ret = []
        for flag in IFF_VALUES:
            if (flag & mask & flags) == flag:
                ret.append(IFF_VALUES[flag])
        return ret

    @staticmethod
    def names2flags(flags):
        ret = 0
        mask = 0
        for flag in flags:
            if flag[0] == '!':
                flag = flag[1:]
            else:
                ret |= IFF_NAMES[flag]
            mask |= IFF_NAMES[flag]
        return (ret, mask)

    def encode(self):
        # convert flags
        if isinstance(self['flags'], (set, tuple, list)):
            self['flags'], self['change'] = self.names2flags(self['flags'])
        return super(ifinfbase, self).encode()

    class down_reason(nla):
        nla_flags = NLA_F_NESTED
        prefix = 'IFLA_'
        nla_map = (
            ('IFLA_PROTO_DOWN_REASON_UNSPEC', 'none'),
            ('IFLA_PROTO_DOWN_REASON_MASK', 'uint32'),
            ('IFLA_PROTO_DOWN_REASON_VALUE', 'uint32'),
        )

    class netns_fd(nla):
        fields = [('value', 'I')]
        netns_run_dir = '/var/run/netns'
        netns_fd = None

        def encode(self):
            #
            # There are two ways to specify netns
            #
            # 1. provide fd to an open file
            # 2. provide a file name
            #
            # In the first case, the value is passed to the kernel
            # as is. In the second case, the object opens appropriate
            # file from `self.netns_run_dir` and closes it upon
            # `__del__(self)`
            if isinstance(self.value, int):
                self['value'] = self.value
            else:
                if isinstance(self.value, bytes):
                    self.value = self.value.decode('utf-8')
                if '/' in self.value:
                    netns_path = self.value
                else:
                    netns_path = '%s/%s' % (self.netns_run_dir, self.value)
                self.netns_fd = os.open(netns_path, os.O_RDONLY)
                self['value'] = self.netns_fd
                self.register_clean_cb(self.close)
            nla.encode(self)

        def close(self):
            if self.netns_fd is not None:
                os.close(self.netns_fd)

    class xdp(nla):
        nla_flags = NLA_F_NESTED
        prefix = 'IFLA_'
        nla_map = (
            ('IFLA_XDP_UNSPEC', 'none'),
            ('IFLA_XDP_FD', 'xdp_fd'),
            ('IFLA_XDP_ATTACHED', 'xdp_mode'),
            ('IFLA_XDP_FLAGS', 'xdp_flags'),
            ('IFLA_XDP_PROG_ID', 'uint32'),
            ('IFLA_XDP_DRV_PROG_ID', 'uint32'),
            ('IFLA_XDP_SKB_PROG_ID', 'uint32'),
            ('IFLA_XDP_HW_PROG_ID', 'uint32'),
            ('IFLA_XDP_EXPECTED_FD', 'xdp_fd'),
        )

        class xdp_fd(nlmsg_atoms.int32):
            sql_type = None

        class xdp_flags(nla):
            fields = [('value', '>H')]
            sql_type = 'INTEGER'

            def encode(self):
                v = self.value
                for flag in XDP_FLAGS_VALUES:
                    v &= ~flag

                if v != 0:
                    log.warning('possibly incorrect XDP flags')

                nla.encode(self)

        class xdp_mode(nlmsg_atoms.uint8):
            value_map = {
                0: None,
                1: 'xdp',
                2: 'xdpgeneric',
                3: 'xdpoffload',
                4: 'xdpmulti',
            }

    class proplist(nla):
        nla_flags = NLA_F_NESTED
        # Proplist has currently only IFLA_ALT_IFNAME, but start at same
        # index than IFLA_ALT_IFNAME in ifinfbase()
        nla_map = ((53, 'IFLA_ALT_IFNAME', 'asciiz'),)

        def altnames(self):
            return (
                attr[1]
                for attr in self["attrs"]
                if attr[0] == "IFLA_ALT_IFNAME"
            )

    class vflist(nla):
        nla_map = (('IFLA_VF_INFO_UNSPEC', 'none'), ('IFLA_VF_INFO', 'vfinfo'))

        class vfinfo(nla):
            prefix = 'IFLA_VF_'
            nla_map = (
                ('IFLA_VF_UNSPEC', 'none'),
                ('IFLA_VF_MAC', 'vf_mac'),
                ('IFLA_VF_VLAN', 'vf_vlan'),
                ('IFLA_VF_TX_RATE', 'vf_tx_rate'),
                ('IFLA_VF_SPOOFCHK', 'vf_spoofchk'),
                ('IFLA_VF_LINK_STATE', 'vf_link_state'),
                ('IFLA_VF_RATE', 'vf_rate'),
                ('IFLA_VF_RSS_QUERY_EN', 'vf_rss_query_en'),
                ('IFLA_VF_STATS', 'vf_stats'),
                ('IFLA_VF_TRUST', 'vf_trust'),
                ('IFLA_VF_IB_NODE_GUID', 'vf_ib_node_guid'),
                ('IFLA_VF_IB_PORT_GUID', 'vf_ib_port_guid'),
                ('IFLA_VF_VLAN_LIST', 'vf_vlist'),
            )

            class vf_ib_node_guid(nla):
                fields = (('vf', 'I'), ('ib_node_guid', '32B'))

                def decode(self):
                    nla.decode(self)
                    self['ib_node_guid'] = ':'.join(
                        ['%02x' % x for x in self['ib_node_guid'][4:12][::-1]]
                    )

                def encode(self):
                    encoded_guid = self['ib_node_guid'].split(':')[::-1]
                    self['ib_node_guid'] = (
                        [0] * 4 + [int(x, 16) for x in encoded_guid] + [0] * 20
                    )
                    nla.encode(self)

            class vf_ib_port_guid(nla):
                fields = (('vf', 'I'), ('ib_port_guid', '32B'))

                def decode(self):
                    nla.decode(self)
                    self['ib_port_guid'] = ':'.join(
                        ['%02x' % x for x in self['ib_port_guid'][4:12][::-1]]
                    )

                def encode(self):
                    encoded_guid = self['ib_port_guid'].split(':')[::-1]
                    self['ib_port_guid'] = (
                        [0] * 4 + [int(x, 16) for x in encoded_guid] + [0] * 20
                    )
                    nla.encode(self)

            class vf_mac(nla):
                fields = (('vf', 'I'), ('mac', '32B'))

                def decode(self):
                    nla.decode(self)
                    self['mac'] = ':'.join(
                        ['%02x' % x for x in self['mac'][:6]]
                    )

                def encode(self):
                    self['mac'] = [
                        int(x, 16) for x in self['mac'].split(':')
                    ] + [0] * 26
                    nla.encode(self)

            class vf_vlan(nla):
                fields = (('vf', 'I'), ('vlan', 'I'), ('qos', 'I'))

            class vf_tx_rate(nla):
                fields = (('vf', 'I'), ('tx_rate', 'I'))

            class vf_spoofchk(nla):
                fields = (('vf', 'I'), ('spoofchk', 'I'))

            class vf_link_state(nla):
                fields = (('vf', 'I'), ('link_state', 'I'))

            class vf_rate(nla):
                fields = (
                    ('vf', 'I'),
                    ('min_tx_rate', 'I'),
                    ('max_tx_rate', 'I'),
                )

            class vf_rss_query_en(nla):
                fields = (('vf', 'I'), ('rss_query_en', 'I'))

            class vf_stats(nla):
                nla_map = (
                    ('IFLA_VF_STATS_RX_PACKETS', 'uint64'),
                    ('IFLA_VF_STATS_TX_PACKETS', 'uint64'),
                    ('IFLA_VF_STATS_RX_BYTES', 'uint64'),
                    ('IFLA_VF_STATS_TX_BYTES', 'uint64'),
                    ('IFLA_VF_STATS_BROADCAST', 'uint64'),
                    ('IFLA_VF_STATS_MULTICAST', 'uint64'),
                    ('IFLA_VF_STATS_PAD', 'uint64'),
                    ('IFLA_VF_STATS_RX_DROPPED', 'uint64'),
                    ('IFLA_VF_STATS_TX_DROPPED', 'uint64'),
                )

            class vf_trust(nla):
                fields = (('vf', 'I'), ('trust', 'I'))

            class vf_vlist(nla):
                nla_map = (
                    ('IFLA_VF_VLAN_INFO_UNSPEC', 'none'),
                    ('IFLA_VF_VLAN_INFO', 'ivvi'),
                )

                class ivvi(nla):
                    fields = (
                        ('vf', 'I'),
                        ('vlan', 'I'),
                        ('qos', 'I'),
                        ('proto', '>H'),
                    )

    class wireless(iw_event):
        pass

    class state(nla):
        fields = (('value', 'B'),)
        sql_type = 'TEXT'

        def encode(self):
            self['value'] = state_by_name[self.value]
            nla.encode(self)

        def decode(self):
            nla.decode(self)
            self.value = state_by_code[self['value']]

    class ifstats(nla):
        fields = [(i, 'I') for i in stats_names]

    class ifstats64(nla):
        fields = [(i, 'Q') for i in stats_names]

    class ifmap(nla):
        fields = (
            ('mem_start', 'Q'),
            ('mem_end', 'Q'),
            ('base_addr', 'Q'),
            ('irq', 'H'),
            ('dma', 'B'),
            ('port', 'B'),
        )

    @staticmethod
    def protinfo(self, *argv, **kwarg):
        proto_map = {AF_BRIDGE: protinfo_bridge}
        return proto_map.get(self['family'], self.hex)

    class ifinfo(nla):
        prefix = 'IFLA_INFO_'
        nla_map = (
            ('IFLA_INFO_UNSPEC', 'none'),
            ('IFLA_INFO_KIND', 'asciiz'),
            ('IFLA_INFO_DATA', 'info_data'),
            ('IFLA_INFO_XSTATS', 'hex'),
            ('IFLA_INFO_SLAVE_KIND', 'asciiz'),
            ('IFLA_INFO_SLAVE_DATA', 'info_slave_data'),
        )

        @staticmethod
        def info_slave_data(self, *argv, **kwarg):
            '''
            Return IFLA_INFO_SLAVE_DATA type based on
            IFLA_INFO_SLAVE_KIND or IFLA_INFO_KIND.
            '''
            kind = self.get_attr('IFLA_INFO_SLAVE_KIND')
            if kind is None:
                kind = self.get_attr('IFLA_INFO_KIND')
            data_map = {
                'bridge': self.bridge_slave_data,
                'bridge_slave': self.bridge_slave_data,
                'bond': self.bond_slave_data,
            }
            return data_map.get(kind, self.hex)

        class bridge_slave_data(protinfo_bridge):
            pass

        class bond_slave_data(nla):
            nla_map = (
                ('IFLA_BOND_SLAVE_UNSPEC', 'none'),
                ('IFLA_BOND_SLAVE_STATE', 'uint8'),
                ('IFLA_BOND_SLAVE_MII_STATUS', 'uint8'),
                ('IFLA_BOND_SLAVE_LINK_FAILURE_COUNT', 'uint32'),
                ('IFLA_BOND_SLAVE_PERM_HWADDR', 'l2addr'),
                ('IFLA_BOND_SLAVE_QUEUE_ID', 'uint16'),
                ('IFLA_BOND_SLAVE_AD_AGGREGATOR_ID', 'uint16'),
            )

        @staticmethod
        def info_data(self, *argv, **kwarg):
            '''
            The function returns appropriate IFLA_INFO_DATA
            type according to IFLA_INFO_KIND info. Return
            'hex' type for all unknown kind's and when the
            kind is not known.
            '''
            kind = self.get_attr('IFLA_INFO_KIND')
            return self.data_map.get(kind, self.hex)

        class veth_data(nla):
            nla_map = (
                ('VETH_INFO_UNSPEC', 'none'),
                ('VETH_INFO_PEER', 'info_peer'),
            )

            @staticmethod
            def info_peer(self, *argv, **kwarg):
                return ifinfveth

        class ipip_data(iptnl_data):
            pass

        class sit_data(iptnl_data):
            nla_map = [
                (x[0].replace('IPIP', 'SIT'), x[1]) for x in iptnl_data.nla_map
            ]

        class ip6tnl_data(nla):
            prefix = 'IFLA_'
            nla_map = (
                ('IFLA_IP6TNL_UNSPEC', 'none'),
                ('IFLA_IP6TNL_LINK', 'uint32'),
                ('IFLA_IP6TNL_LOCAL', 'ip6addr'),
                ('IFLA_IP6TNL_REMOTE', 'ip6addr'),
                ('IFLA_IP6TNL_TTL', 'uint8'),
                ('IFLA_IP6TNL_TOS', 'uint8'),
                ('IFLA_IP6TNL_ENCAP_LIMIT', 'uint8'),
                ('IFLA_IP6TNL_FLOWINFO', 'be32'),
                ('IFLA_IP6TNL_FLAGS', 'uint32'),
                ('IFLA_IP6TNL_PROTO', 'uint8'),
                ('IFLA_IP6TNL_PMTUDISC', 'uint8'),
                ('IFLA_IP6TNL_6RD_PREFIX', 'ip6addr'),
                ('IFLA_IP6TNL_6RD_RELAY_PREFIX', 'ip4addr'),
                ('IFLA_IP6TNL_6RD_PREFIXLEN', 'uint16'),
                ('IFLA_IP6TNL_6RD_RELAY_PREFIXLEN', 'uint16'),
                ('IFLA_IP6TNL_ENCAP_TYPE', 'uint16'),
                ('IFLA_IP6TNL_ENCAP_FLAGS', 'uint16'),
                ('IFLA_IP6TNL_ENCAP_SPORT', 'be16'),
                ('IFLA_IP6TNL_ENCAP_DPORT', 'be16'),
                ('IFLA_IP6TNL_COLLECT_METADATA', 'flag'),
                ('IFLA_IP6TNL_FWMARK', 'uint32'),
            )

        class gre_data(nla):
            prefix = 'IFLA_'
            nla_map = (
                ('IFLA_GRE_UNSPEC', 'none'),
                ('IFLA_GRE_LINK', 'uint32'),
                ('IFLA_GRE_IFLAGS', 'gre_flags'),
                ('IFLA_GRE_OFLAGS', 'gre_flags'),
                ('IFLA_GRE_IKEY', 'be32'),
                ('IFLA_GRE_OKEY', 'be32'),
                ('IFLA_GRE_LOCAL', 'ip4addr'),
                ('IFLA_GRE_REMOTE', 'ip4addr'),
                ('IFLA_GRE_TTL', 'uint8'),
                ('IFLA_GRE_TOS', 'uint8'),
                ('IFLA_GRE_PMTUDISC', 'uint8'),
                ('IFLA_GRE_ENCAP_LIMIT', 'uint8'),
                ('IFLA_GRE_FLOWINFO', 'be32'),
                ('IFLA_GRE_FLAGS', 'uint32'),
                ('IFLA_GRE_ENCAP_TYPE', 'uint16'),
                ('IFLA_GRE_ENCAP_FLAGS', 'uint16'),
                ('IFLA_GRE_ENCAP_SPORT', 'be16'),
                ('IFLA_GRE_ENCAP_DPORT', 'be16'),
                ('IFLA_GRE_COLLECT_METADATA', 'flag'),
                ('IFLA_GRE_IGNORE_DF', 'uint8'),
                ('IFLA_GRE_FWMARK', 'uint32'),
            )

            class gre_flags(nla):
                fields = [('value', '>H')]
                sql_type = 'INTEGER'

                def encode(self):
                    #
                    # for details see:
                    url = 'https://github.com/svinota/pyroute2/issues/531'

                    v = self.value
                    for flag in GRE_VALUES:
                        v &= ~flag
                    if v != 0:
                        log.warning(
                            'possibly incorrect GRE flags, ' 'see %s' % url
                        )
                    nla.encode(self)

        class ip6gre_data(nla):
            # Ostensibly the same as ip6gre_data except that local
            # and remote are ipv6 addrs.
            # As of Linux 4.8,IFLA_GRE_COLLECT_METADATA has not been
            # implemented for IPv6.
            # Linux uses the same enum names for v6 and v4 (in if_tunnel.h);
            # Here we name them IFLA_IP6GRE_xxx instead to avoid conflicts
            # with gre_data above.
            prefix = 'IFLA_'
            nla_map = (
                ('IFLA_IP6GRE_UNSPEC', 'none'),
                ('IFLA_IP6GRE_LINK', 'uint32'),
                ('IFLA_IP6GRE_IFLAGS', 'uint16'),
                ('IFLA_IP6GRE_OFLAGS', 'uint16'),
                ('IFLA_IP6GRE_IKEY', 'be32'),
                ('IFLA_IP6GRE_OKEY', 'be32'),
                ('IFLA_IP6GRE_LOCAL', 'ip6addr'),
                ('IFLA_IP6GRE_REMOTE', 'ip6addr'),
                ('IFLA_IP6GRE_TTL', 'uint8'),
                ('IFLA_IP6GRE_TOS', 'uint8'),
                ('IFLA_IP6GRE_PMTUDISC', 'uint8'),
                ('IFLA_IP6GRE_ENCAP_LIMIT', 'uint8'),
                ('IFLA_IP6GRE_FLOWINFO', 'be32'),
                ('IFLA_IP6GRE_FLAGS', 'uint32'),
                ('IFLA_IP6GRE_ENCAP_TYPE', 'uint16'),
                ('IFLA_IP6GRE_ENCAP_FLAGS', 'uint16'),
                ('IFLA_IP6GRE_ENCAP_SPORT', 'be16'),
                ('IFLA_IP6GRE_ENCAP_DPORT', 'be16'),
            )

        class macvlan_data(macvx_data):
            pass

        class macvtap_data(macvx_data):
            nla_map = [
                (x[0].replace('MACVLAN', 'MACVTAP'), x[1])
                for x in macvx_data.nla_map
            ]

        class bridge_data(nla):
            prefix = 'IFLA_'
            nla_map = (
                ('IFLA_BR_UNSPEC', 'none'),
                ('IFLA_BR_FORWARD_DELAY', 'uint32'),
                ('IFLA_BR_HELLO_TIME', 'uint32'),
                ('IFLA_BR_MAX_AGE', 'uint32'),
                ('IFLA_BR_AGEING_TIME', 'uint32'),
                ('IFLA_BR_STP_STATE', 'uint32'),
                ('IFLA_BR_PRIORITY', 'uint16'),
                ('IFLA_BR_VLAN_FILTERING', 'uint8'),
                ('IFLA_BR_VLAN_PROTOCOL', 'be16'),
                ('IFLA_BR_GROUP_FWD_MASK', 'uint16'),
                ('IFLA_BR_ROOT_ID', 'br_id'),
                ('IFLA_BR_BRIDGE_ID', 'br_id'),
                ('IFLA_BR_ROOT_PORT', 'uint16'),
                ('IFLA_BR_ROOT_PATH_COST', 'uint32'),
                ('IFLA_BR_TOPOLOGY_CHANGE', 'uint8'),
                ('IFLA_BR_TOPOLOGY_CHANGE_DETECTED', 'uint8'),
                ('IFLA_BR_HELLO_TIMER', 'uint64'),
                ('IFLA_BR_TCN_TIMER', 'uint64'),
                ('IFLA_BR_TOPOLOGY_CHANGE_TIMER', 'uint64'),
                ('IFLA_BR_GC_TIMER', 'uint64'),
                ('IFLA_BR_GROUP_ADDR', 'l2addr'),
                ('IFLA_BR_FDB_FLUSH', 'flag'),
                ('IFLA_BR_MCAST_ROUTER', 'uint8'),
                ('IFLA_BR_MCAST_SNOOPING', 'uint8'),
                ('IFLA_BR_MCAST_QUERY_USE_IFADDR', 'uint8'),
                ('IFLA_BR_MCAST_QUERIER', 'uint8'),
                ('IFLA_BR_MCAST_HASH_ELASTICITY', 'uint32'),
                ('IFLA_BR_MCAST_HASH_MAX', 'uint32'),
                ('IFLA_BR_MCAST_LAST_MEMBER_CNT', 'uint32'),
                ('IFLA_BR_MCAST_STARTUP_QUERY_CNT', 'uint32'),
                ('IFLA_BR_MCAST_LAST_MEMBER_INTVL', 'uint64'),
                ('IFLA_BR_MCAST_MEMBERSHIP_INTVL', 'uint64'),
                ('IFLA_BR_MCAST_QUERIER_INTVL', 'uint64'),
                ('IFLA_BR_MCAST_QUERY_INTVL', 'uint64'),
                ('IFLA_BR_MCAST_QUERY_RESPONSE_INTVL', 'uint64'),
                ('IFLA_BR_MCAST_STARTUP_QUERY_INTVL', 'uint64'),
                ('IFLA_BR_NF_CALL_IPTABLES', 'uint8'),
                ('IFLA_BR_NF_CALL_IP6TABLES', 'uint8'),
                ('IFLA_BR_NF_CALL_ARPTABLES', 'uint8'),
                ('IFLA_BR_VLAN_DEFAULT_PVID', 'uint16'),
                ('IFLA_BR_PAD', 'uint64'),
                ('IFLA_BR_VLAN_STATS_ENABLED', 'uint8'),
                ('IFLA_BR_MCAST_STATS_ENABLED', 'uint8'),
                ('IFLA_BR_MCAST_IGMP_VERSION', 'uint8'),
                ('IFLA_BR_MCAST_MLD_VERSION', 'uint8'),
            )

            class br_id(ifla_bridge_id):
                pass

        # IFLA_INFO_DATA plugin system prototype
        data_map = {
            'macvlan': macvlan_data,
            'macvtap': macvtap_data,
            'ipip': ipip_data,
            'sit': sit_data,
            'ip6tnl': ip6tnl_data,
            'gre': gre_data,
            'gretap': gre_data,
            'ip6gre': ip6gre_data,
            'ip6gretap': ip6gre_data,
            'veth': veth_data,
            'bridge': bridge_data,
            'bridge_slave': bridge_slave_data,
        }
        # expand supported interface types
        data_map.update(data_plugins)

        @classmethod
        def register_link_kind(cls, path=None, pkg=None, module=None):
            cls.data_map.update(data_plugins)
            if path is not None:
                cls.data_map.update(load_plugins_by_path(path))
            elif pkg is not None:
                cls.data_map.update(load_plugins_by_pkg(pkg))
            elif module is not None:
                for name, link_class in module.items():
                    cls.data_map[name] = link_class
            else:
                raise TypeError('path or pkg required')

        @classmethod
        def unregister_link_kind(cls, kind):
            return cls.data_map.pop(kind)

        @classmethod
        def list_link_kind(cls):
            return cls.data_map

    sql_extend = ((ifinfo, 'IFLA_LINKINFO'), (xdp, 'IFLA_XDP'))

    @staticmethod
    def af_spec(self, *argv, **kwarg):
        specs = {
            0: self.af_spec_inet,
            AF_INET: self.af_spec_inet,
            AF_INET6: self.af_spec_inet,
            AF_BRIDGE: self.af_spec_bridge,
        }
        return specs.get(self['family'], self.hex)

    class af_spec_bridge(nla):
        prefix = 'IFLA_BRIDGE_'
        # Bug-Url: https://github.com/svinota/pyroute2/issues/284
        # resolve conflict with link()/flags
        # IFLA_BRIDGE_FLAGS is for compatibility, in nla dicts
        # IFLA_BRIDGE_VLAN_FLAGS overrides it
        nla_map = (
            (0, 'IFLA_BRIDGE_FLAGS', 'uint16'),
            (0, 'IFLA_BRIDGE_VLAN_FLAGS', 'vlan_flags'),
            (1, 'IFLA_BRIDGE_MODE', 'uint16'),
            (2, 'IFLA_BRIDGE_VLAN_INFO', 'vlan_info'),
            (3, 'IFLA_BRIDGE_VLAN_TUNNEL_INFO', 'vlan_tunnel_info'),
        )

        class vlan_flags(nla):
            fields = [('value', 'H')]

            def encode(self):
                # convert flags
                if isinstance(self['value'], basestring):
                    self['value'] = BRIDGE_FLAGS_NAMES[
                        'BRIDGE_FLAGS_' + self['value'].upper()
                    ]
                nla.encode(self)

        class vlan_info(nla):
            prefix = ''
            fields = (('flags', 'H'), ('vid', 'H'))

            @staticmethod
            def flags2names(flags):
                ret = []
                for flag in BRIDGE_VLAN_VALUES:
                    if (flag & flags) == flag:
                        ret.append(BRIDGE_VLAN_VALUES[flag])
                return ret

            @staticmethod
            def names2flags(flags):
                ret = 0
                for flag in flags:
                    ret |= BRIDGE_VLAN_NAMES[
                        'BRIDGE_VLAN_INFO_' + flag.upper()
                    ]
                return ret

            def encode(self):
                # convert flags
                if isinstance(self['flags'], (set, tuple, list)):
                    self['flags'] = self.names2flags(self['flags'])
                return super(nla, self).encode()

        class vlan_tunnel_info(nla):
            prefix = 'IFLA_BRIDGE_VLAN_TUNNEL_'
            nla_map = (
                ('IFLA_BRIDGE_VLAN_TUNNEL_UNSPEC', 'none'),
                ('IFLA_BRIDGE_VLAN_TUNNEL_ID', 'uint32'),
                ('IFLA_BRIDGE_VLAN_TUNNEL_VID', 'uint16'),
                ('IFLA_BRIDGE_VLAN_TUNNEL_FLAGS', 'uint16'),
            )

    class af_spec_inet(nla):
        nla_map = (
            ('AF_UNSPEC', 'none'),
            ('AF_UNIX', 'hex'),
            ('AF_INET', 'inet'),
            ('AF_AX25', 'hex'),
            ('AF_IPX', 'hex'),
            ('AF_APPLETALK', 'hex'),
            ('AF_NETROM', 'hex'),
            ('AF_BRIDGE', 'hex'),
            ('AF_ATMPVC', 'hex'),
            ('AF_X25', 'hex'),
            ('AF_INET6', 'inet6'),
        )

        class inet(nla):
            #  ./include/linux/inetdevice.h: struct ipv4_devconf
            #  ./include/uapi/linux/ip.h
            field_names = (
                'dummy',
                'forwarding',
                'mc_forwarding',
                'proxy_arp',
                'accept_redirects',
                'secure_redirects',
                'send_redirects',
                'shared_media',
                'rp_filter',
                'accept_source_route',
                'bootp_relay',
                'log_martians',
                'tag',
                'arpfilter',
                'medium_id',
                'noxfrm',
                'nopolicy',
                'force_igmp_version',
                'arp_announce',
                'arp_ignore',
                'promote_secondaries',
                'arp_accept',
                'arp_notify',
                'accept_local',
                'src_vmark',
                'proxy_arp_pvlan',
                'route_localnet',
                'igmpv2_unsolicited_report_interval',
                'igmpv3_unsolicited_report_interval',
            )
            fields = [(i, 'I') for i in field_names]

        class inet6(nla):
            prefix = 'IFLA_'
            nla_map = (
                ('IFLA_INET6_UNSPEC', 'none'),
                ('IFLA_INET6_FLAGS', 'uint32'),
                ('IFLA_INET6_CONF', 'ipv6_devconf'),
                ('IFLA_INET6_STATS', 'ipv6_stats'),
                ('IFLA_INET6_MCAST', 'hex'),
                ('IFLA_INET6_CACHEINFO', 'ipv6_cache_info'),
                ('IFLA_INET6_ICMP6STATS', 'icmp6_stats'),
                ('IFLA_INET6_TOKEN', 'ip6addr'),
                ('IFLA_INET6_ADDR_GEN_MODE', 'uint8'),
            )

            class ipv6_devconf(nla):
                # ./include/uapi/linux/ipv6.h
                # DEVCONF_
                field_names = (
                    'forwarding',
                    'hop_limit',
                    'mtu',
                    'accept_ra',
                    'accept_redirects',
                    'autoconf',
                    'dad_transmits',
                    'router_solicitations',
                    'router_solicitation_interval',
                    'router_solicitation_delay',
                    'use_tempaddr',
                    'temp_valid_lft',
                    'temp_preferred_lft',
                    'regen_max_retry',
                    'max_desync_factor',
                    'max_addresses',
                    'force_mld_version',
                    'accept_ra_defrtr',
                    'accept_ra_pinfo',
                    'accept_ra_rtr_pref',
                    'router_probe_interval',
                    'accept_ra_rt_info_max_plen',
                    'proxy_ndp',
                    'optimistic_dad',
                    'accept_source_route',
                    'mc_forwarding',
                    'disable_ipv6',
                    'accept_dad',
                    'force_tllao',
                    'ndisc_notify',
                )
                fields = [(i, 'I') for i in field_names]

            class ipv6_cache_info(nla):
                # ./include/uapi/linux/if_link.h: struct ifla_cacheinfo
                fields = (
                    ('max_reasm_len', 'I'),
                    ('tstamp', 'I'),
                    ('reachable_time', 'I'),
                    ('retrans_time', 'I'),
                )

            class ipv6_stats(nla):
                # ./include/uapi/linux/snmp.h
                field_names = (
                    'num',
                    'inpkts',
                    'inoctets',
                    'indelivers',
                    'outforwdatagrams',
                    'outpkts',
                    'outoctets',
                    'inhdrerrors',
                    'intoobigerrors',
                    'innoroutes',
                    'inaddrerrors',
                    'inunknownprotos',
                    'intruncatedpkts',
                    'indiscards',
                    'outdiscards',
                    'outnoroutes',
                    'reasmtimeout',
                    'reasmreqds',
                    'reasmoks',
                    'reasmfails',
                    'fragoks',
                    'fragfails',
                    'fragcreates',
                    'inmcastpkts',
                    'outmcastpkts',
                    'inbcastpkts',
                    'outbcastpkts',
                    'inmcastoctets',
                    'outmcastoctets',
                    'inbcastoctets',
                    'outbcastoctets',
                    'csumerrors',
                    'noectpkts',
                    'ect1pkts',
                    'ect0pkts',
                    'cepkts',
                )
                fields = [(i, 'Q') for i in field_names]

            class icmp6_stats(nla):
                # ./include/uapi/linux/snmp.h
                field_names = (
                    'num',
                    'inmsgs',
                    'inerrors',
                    'outmsgs',
                    'outerrors',
                    'csumerrors',
                )
                fields = [(i, 'Q') for i in field_names]


class ifinfmsg(ifinfbase, nlmsg):
    def decode(self):
        nlmsg.decode(self)
        if self['flags'] & 1:
            self['state'] = 'up'
        else:
            self['state'] = 'down'


class ifinfveth(ifinfbase, nla):
    pass
