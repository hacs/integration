"""
NFCTSocket -- low level connection tracking API

See also: pyroute2.conntrack
"""

import socket

from pyroute2.netlink import (
    NETLINK_NETFILTER,
    NLA_F_NESTED,
    NLM_F_ACK,
    NLM_F_CREATE,
    NLM_F_DUMP,
    NLM_F_EXCL,
    NLM_F_REQUEST,
    NLMSG_ERROR,
    nla,
)
from pyroute2.netlink.nfnetlink import NFNL_SUBSYS_CTNETLINK, nfgen_msg
from pyroute2.netlink.nlsocket import NetlinkSocket

IPCTNL_MSG_CT_NEW = 0
IPCTNL_MSG_CT_GET = 1
IPCTNL_MSG_CT_DELETE = 2
IPCTNL_MSG_CT_GET_CTRZERO = 3
IPCTNL_MSG_CT_GET_STATS_CPU = 4
IPCTNL_MSG_CT_GET_STATS = 5
IPCTNL_MSG_CT_GET_DYING = 6
IPCTNL_MSG_CT_GET_UNCONFIRMED = 7
IPCTNL_MSG_MAX = 8


try:
    IP_PROTOCOLS = {
        num: name[8:]
        for name, num in vars(socket).items()
        if name.startswith("IPPROTO")
    }
except (IOError, OSError):
    IP_PROTOCOLS = {}


# Window scaling is advertised by the sender
IP_CT_TCP_FLAG_WINDOW_SCALE = 0x01

# SACK is permitted by the sender
IP_CT_TCP_FLAG_SACK_PERM = 0x02

# This sender sent FIN first
IP_CT_TCP_FLAG_CLOSE_INIT = 0x04

# Be liberal in window checking
IP_CT_TCP_FLAG_BE_LIBERAL = 0x08

# Has unacknowledged data
IP_CT_TCP_FLAG_DATA_UNACKNOWLEDGED = 0x10

# The field td_maxack has been set
IP_CT_TCP_FLAG_MAXACK_SET = 0x20


# From linux/include/net/tcp_states.h
TCPF_ESTABLISHED = 1 << 1
TCPF_SYN_SENT = 1 << 2
TCPF_SYN_RECV = 1 << 3
TCPF_FIN_WAIT1 = 1 << 4
TCPF_FIN_WAIT2 = 1 << 5
TCPF_TIME_WAIT = 1 << 6
TCPF_CLOSE = 1 << 7
TCPF_CLOSE_WAIT = 1 << 8
TCPF_LAST_ACK = 1 << 9
TCPF_LISTEN = 1 << 10
TCPF_CLOSING = 1 << 11
TCPF_NEW_SYN_RECV = 1 << 12
TCPF_TO_NAME = {
    TCPF_ESTABLISHED: 'ESTABLISHED',
    TCPF_SYN_SENT: 'SYN_SENT',
    TCPF_SYN_RECV: 'SYN_RECV',
    TCPF_FIN_WAIT1: 'FIN_WAIT1',
    TCPF_FIN_WAIT2: 'FIN_WAIT2',
    TCPF_TIME_WAIT: 'TIME_WAIT',
    TCPF_CLOSE: 'CLOSE',
    TCPF_CLOSE_WAIT: 'CLOSE_WAIT',
    TCPF_LAST_ACK: 'LAST_ACK',
    TCPF_LISTEN: 'LISTEN',
    TCPF_CLOSING: 'CLOSING',
    TCPF_NEW_SYN_RECV: 'NEW_SYN_RECV',
}


# From include/uapi/linux/netfilter/nf_conntrack_common.h
IPS_EXPECTED = 1 << 0
IPS_SEEN_REPLY = 1 << 1
IPS_ASSURED = 1 << 2
IPS_CONFIRMED = 1 << 3
IPS_SRC_NAT = 1 << 4
IPS_DST_NAT = 1 << 5
IPS_NAT_MASK = IPS_DST_NAT | IPS_SRC_NAT
IPS_SEQ_ADJUST = 1 << 6
IPS_SRC_NAT_DONE = 1 << 7
IPS_DST_NAT_DONE = 1 << 8
IPS_NAT_DONE_MASK = IPS_DST_NAT_DONE | IPS_SRC_NAT_DONE
IPS_DYING = 1 << 9
IPS_FIXED_TIMEOUT = 1 << 10
IPS_TEMPLATE = 1 << 11
IPS_UNTRACKED = 1 << 12
IPS_HELPER = 1 << 13
IPS_OFFLOAD = 1 << 14
IPS_UNCHANGEABLE_MASK = (
    IPS_NAT_DONE_MASK
    | IPS_NAT_MASK
    | IPS_EXPECTED
    | IPS_CONFIRMED
    | IPS_DYING
    | IPS_SEQ_ADJUST
    | IPS_TEMPLATE
    | IPS_OFFLOAD
)
IPSBIT_TO_NAME = {
    IPS_EXPECTED: 'EXPECTED',
    IPS_SEEN_REPLY: 'SEEN_REPLY',
    IPS_ASSURED: 'ASSURED',
    IPS_CONFIRMED: 'CONFIRMED',
    IPS_SRC_NAT: 'SRC_NAT',
    IPS_DST_NAT: 'DST_NAT',
    IPS_SEQ_ADJUST: 'SEQ_ADJUST',
    IPS_SRC_NAT_DONE: 'SRC_NAT_DONE',
    IPS_DST_NAT_DONE: 'DST_NAT_DONE',
    IPS_DYING: 'DYING',
    IPS_FIXED_TIMEOUT: 'FIXED_TIMEOUT',
    IPS_TEMPLATE: 'TEMPLATE',
    IPS_UNTRACKED: 'UNTRACKED',
    IPS_HELPER: 'HELPER',
    IPS_OFFLOAD: 'OFFLOAD',
}

# From include/uapi/linux/netfilter/nf_conntrack_tcp.h
IP_CT_TCP_FLAG_WINDOW_SCALE = 0x01
IP_CT_TCP_FLAG_SACK_PERM = 0x02
IP_CT_TCP_FLAG_CLOSE_INIT = 0x04
IP_CT_TCP_FLAG_BE_LIBERAL = 0x08
IP_CT_TCP_FLAG_DATA_UNACKNOWLEDGED = 0x10
IP_CT_TCP_FLAG_MAXACK_SET = 0x20
IP_CT_EXP_CHALLENGE_ACK = 0x40
IP_CT_TCP_SIMULTANEOUS_OPEN = 0x80
IP_CT_TCP_FLAG_TO_NAME = {
    IP_CT_TCP_FLAG_WINDOW_SCALE: 'WINDOW_SCALE',
    IP_CT_TCP_FLAG_SACK_PERM: 'SACK_PERM',
    IP_CT_TCP_FLAG_CLOSE_INIT: 'CLOSE_INIT',
    IP_CT_TCP_FLAG_BE_LIBERAL: 'BE_LIBERAL',
    IP_CT_TCP_FLAG_DATA_UNACKNOWLEDGED: 'DATA_UNACKNOWLEDGED',
    IP_CT_TCP_FLAG_MAXACK_SET: 'MAXACK_SET',
    IP_CT_EXP_CHALLENGE_ACK: 'CHALLENGE_ACK',
    IP_CT_TCP_SIMULTANEOUS_OPEN: 'SIMULTANEOUS_OPEN',
}

# From linux/include/uapi/linux/netfilter/nf_conntrack_tcp.h
TCP_CONNTRACK_SYN_SENT = 1
TCP_CONNTRACK_SYN_RECV = 2
TCP_CONNTRACK_ESTABLISHED = 3
TCP_CONNTRACK_FIN_WAIT = 4
TCP_CONNTRACK_CLOSE_WAIT = 5
TCP_CONNTRACK_LAST_ACK = 6
TCP_CONNTRACK_TIME_WAIT = 7
TCP_CONNTRACK_CLOSE = 8
TCP_CONNTRACK_LISTEN = 9
TCP_CONNTRACK_MAX = 10
TCP_CONNTRACK_IGNORE = 11
TCP_CONNTRACK_RETRANS = 12
TCP_CONNTRACK_UNACK = 13
TCP_CONNTRACK_TIMEOUT_MAX = 14
TCP_CONNTRACK_TO_NAME = {
    TCP_CONNTRACK_SYN_SENT: "SYN_SENT",
    TCP_CONNTRACK_SYN_RECV: "SYN_RECV",
    TCP_CONNTRACK_ESTABLISHED: "ESTABLISHED",
    TCP_CONNTRACK_FIN_WAIT: "FIN_WAIT",
    TCP_CONNTRACK_CLOSE_WAIT: "CLOSE_WAIT",
    TCP_CONNTRACK_LAST_ACK: "LAST_ACK",
    TCP_CONNTRACK_TIME_WAIT: "TIME_WAIT",
    TCP_CONNTRACK_CLOSE: "CLOSE",
    TCP_CONNTRACK_LISTEN: "LISTEN",
    TCP_CONNTRACK_MAX: "MAX",
    TCP_CONNTRACK_IGNORE: "IGNORE",
    TCP_CONNTRACK_RETRANS: "RETRANS",
    TCP_CONNTRACK_UNACK: "UNACK",
    TCP_CONNTRACK_TIMEOUT_MAX: "TIMEOUT_MAX",
}


def terminate_single_msg(msg):
    return msg


def terminate_error_msg(msg):
    return msg['header']['type'] == NLMSG_ERROR


class nfct_stats(nfgen_msg):
    nla_map = (
        ('CTA_STATS_GLOBAL_UNSPEC', 'none'),
        ('CTA_STATS_GLOBAL_ENTRIES', 'be32'),
        ('CTA_STATS_GLOBAL_MAX_ENTRIES', 'be32'),
    )


class nfct_stats_cpu(nfgen_msg):
    nla_map = (
        ('CTA_STATS_UNSPEC', 'none'),
        ('CTA_STATS_SEARCHED', 'be32'),
        ('CTA_STATS_FOUND', 'be32'),
        ('CTA_STATS_NEW', 'be32'),
        ('CTA_STATS_INVALID', 'be32'),
        ('CTA_STATS_IGNORE', 'be32'),
        ('CTA_STATS_DELETE', 'be32'),
        ('CTA_STATS_DELETE_LIST', 'be32'),
        ('CTA_STATS_INSERT', 'be32'),
        ('CTA_STATS_INSERT_FAILED', 'be32'),
        ('CTA_STATS_DROP', 'be32'),
        ('CTA_STATS_EARLY_DROP', 'be32'),
        ('CTA_STATS_ERROR', 'be32'),
        ('CTA_STATS_SEARCH_RESTART', 'be32'),
    )


class nfct_msg(nfgen_msg):
    prefix = 'CTA_'
    nla_map = (
        ('CTA_UNSPEC', 'none'),
        ('CTA_TUPLE_ORIG', 'cta_tuple'),
        ('CTA_TUPLE_REPLY', 'cta_tuple'),
        ('CTA_STATUS', 'be32'),
        ('CTA_PROTOINFO', 'cta_protoinfo'),
        ('CTA_HELP', 'asciiz'),
        ('CTA_NAT_SRC', 'cta_nat'),
        ('CTA_TIMEOUT', 'be32'),
        ('CTA_MARK', 'be32'),
        ('CTA_COUNTERS_ORIG', 'cta_counters'),
        ('CTA_COUNTERS_REPLY', 'cta_counters'),
        ('CTA_USE', 'be32'),
        ('CTA_ID', 'be32'),
        ('CTA_NAT_DST', 'cta_nat'),
        ('CTA_TUPLE_MASTER', 'cta_tuple'),
        ('CTA_SEQ_ADJ_ORIG', 'cta_nat_seq_adj'),
        ('CTA_SEQ_ADJ_REPLY', 'cta_nat_seq_adj'),
        ('CTA_SECMARK', 'be32'),
        ('CTA_ZONE', 'be16'),
        ('CTA_SECCTX', 'cta_secctx'),
        ('CTA_TIMESTAMP', 'cta_timestamp'),
        ('CTA_MARK_MASK', 'be32'),
        ('CTA_LABELS', 'cta_labels'),
        ('CTA_LABELS_MASK', 'cta_labels'),
        ('CTA_SYNPROXY', 'cta_synproxy'),
        ('CTA_FILTER', 'cta_filter'),
    )

    @classmethod
    def create_from(cls, **kwargs):
        self = cls()

        for key, value in kwargs.items():
            if isinstance(value, NFCTAttr):
                value = {'attrs': value.attrs()}
            if value is not None:
                self['attrs'].append([self.name2nla(key), value])

        return self

    class cta_tuple(nla):
        nla_map = (
            ('CTA_TUPLE_UNSPEC', 'none'),
            ('CTA_TUPLE_IP', 'cta_ip'),
            ('CTA_TUPLE_PROTO', 'cta_proto'),
        )

        class cta_ip(nla):
            nla_map = (
                ('CTA_IP_UNSPEC', 'none'),
                ('CTA_IP_V4_SRC', 'ip4addr'),
                ('CTA_IP_V4_DST', 'ip4addr'),
                ('CTA_IP_V6_SRC', 'ip6addr'),
                ('CTA_IP_V6_DST', 'ip6addr'),
            )

        class cta_proto(nla):
            nla_map = (
                ('CTA_PROTO_UNSPEC', 'none'),
                ('CTA_PROTO_NUM', 'uint8'),
                ('CTA_PROTO_SRC_PORT', 'be16'),
                ('CTA_PROTO_DST_PORT', 'be16'),
                ('CTA_PROTO_ICMP_ID', 'be16'),
                ('CTA_PROTO_ICMP_TYPE', 'uint8'),
                ('CTA_PROTO_ICMP_CODE', 'uint8'),
                ('CTA_PROTO_ICMPV6_ID', 'be16'),
                ('CTA_PROTO_ICMPV6_TYPE', 'uint8'),
                ('CTA_PROTO_ICMPV6_CODE', 'uint8'),
            )

    class cta_protoinfo(nla):
        nla_map = (
            ('CTA_PROTOINFO_UNSPEC', 'none'),
            ('CTA_PROTOINFO_TCP', 'cta_protoinfo_tcp'),
            ('CTA_PROTOINFO_DCCP', 'cta_protoinfo_dccp'),
            ('CTA_PROTOINFO_SCTP', 'cta_protoinfo_sctp'),
        )

        class cta_protoinfo_tcp(nla):
            nla_map = (
                ('CTA_PROTOINFO_TCP_UNSPEC', 'none'),
                ('CTA_PROTOINFO_TCP_STATE', 'uint8'),
                ('CTA_PROTOINFO_TCP_WSCALE_ORIGINAL', 'uint8'),
                ('CTA_PROTOINFO_TCP_WSCALE_REPLY', 'uint8'),
                ('CTA_PROTOINFO_TCP_FLAGS_ORIGINAL', 'cta_tcp_flags'),
                ('CTA_PROTOINFO_TCP_FLAGS_REPLY', 'cta_tcp_flags'),
            )

            class cta_tcp_flags(nla):
                fields = [('value', 'BB')]

        class cta_protoinfo_dccp(nla):
            nla_map = (
                ('CTA_PROTOINFO_DCCP_UNSPEC', 'none'),
                ('CTA_PROTOINFO_DCCP_STATE', 'uint8'),
                ('CTA_PROTOINFO_DCCP_ROLE', 'uint8'),
                ('CTA_PROTOINFO_DCCP_HANDSHAKE_SEQ', 'be64'),
            )

        class cta_protoinfo_sctp(nla):
            nla_map = (
                ('CTA_PROTOINFO_SCTP_UNSPEC', 'none'),
                ('CTA_PROTOINFO_SCTP_STATE', 'uint8'),
                ('CTA_PROTOINFO_SCTP_VTAG_ORIGINAL', 'be32'),
                ('CTA_PROTOINFO_SCTP_VTAG_REPLY', 'be32'),
            )

    class cta_nat(nla):
        nla_map = (
            ('CTA_NAT_UNSPEC', 'none'),
            ('CTA_NAT_V4_MINIP', 'ip4addr'),
            ('CTA_NAT_V4_MAXIP', 'ip4addr'),
            ('CTA_NAT_PROTO', 'cta_protonat'),
            ('CTA_NAT_V6_MINIP', 'ip6addr'),
            ('CTA_NAT_V6_MAXIP', 'ip6addr'),
        )

        class cta_protonat(nla):
            nla_map = (
                ('CTA_PROTONAT_UNSPEC', 'none'),
                ('CTA_PROTONAT_PORT_MIN', 'be16'),
                ('CTA_PROTONAT_PORT_MAX', 'be16'),
            )

    class cta_nat_seq_adj(nla):
        nla_map = (
            ('CTA_NAT_SEQ_UNSPEC', 'none'),
            ('CTA_NAT_SEQ_CORRECTION_POS', 'be32'),
            ('CTA_NAT_SEQ_OFFSET_BEFORE', 'be32'),
            ('CTA_NAT_SEQ_OFFSET_AFTER', 'be32'),
        )

    class cta_counters(nla):
        nla_map = (
            ('CTA_COUNTERS_UNSPEC', 'none'),
            ('CTA_COUNTERS_PACKETS', 'be64'),
            ('CTA_COUNTERS_BYTES', 'be64'),
            ('CTA_COUNTERS32_PACKETS', 'be32'),
            ('CTA_COUNTERS32_BYTES', 'be32'),
        )

    class cta_secctx(nla):
        nla_map = (
            ('CTA_SECCTX_UNSPEC', 'none'),
            ('CTA_SECCTX_NAME', 'asciiz'),
        )

    class cta_timestamp(nla):
        nla_map = (
            ('CTA_TIMESTAMP_UNSPEC', 'none'),
            ('CTA_TIMESTAMP_START', 'be64'),
            ('CTA_TIMESTAMP_STOP', 'be64'),
        )

    class cta_filter(nla):
        nla_flags = NLA_F_NESTED
        nla_map = (
            ('CTA_FILTER_UNSPEC', 'none'),
            ('CTA_FILTER_ORIG_FLAGS', 'uint32'),
            ('CTA_FILTER_REPLY_FLAGS', 'uint32'),
        )

    class cta_labels(nla):
        fields = [('value', 'QQ')]

        def encode(self):
            if not isinstance(self['value'], tuple):
                self['value'] = (
                    self['value'] & 0xFFFFFFFFFFFFFFFF,
                    self['value'] >> 64,
                )
            nla.encode(self)

        def decode(self):
            nla.decode(self)
            if isinstance(self['value'], tuple):
                self['value'] = (self['value'][0] & 0xFFFFFFFFFFFFFFFF) | (
                    self['value'][1] << 64
                )

    class cta_synproxy(nla):
        nla_map = (
            ('CTA_SYNPROXY_UNSPEC', 'none'),
            ('CTA_SYNPROXY_ISN', 'be32'),
            ('CTA_SYNPROXY_ITS', 'be32'),
            ('CTA_SYNPROXY_TSOFF', 'be32'),
        )


FILTER_FLAG_CTA_IP_SRC = 1 << 0
FILTER_FLAG_CTA_IP_DST = 1 << 1
FILTER_FLAG_CTA_TUPLE_ZONE = 1 << 2
FILTER_FLAG_CTA_PROTO_NUM = 1 << 3
FILTER_FLAG_CTA_PROTO_SRC_PORT = 1 << 4
FILTER_FLAG_CTA_PROTO_DST_PORT = 1 << 5
FILTER_FLAG_CTA_PROTO_ICMP_TYPE = 1 << 6
FILTER_FLAG_CTA_PROTO_ICMP_CODE = 1 << 7
FILTER_FLAG_CTA_PROTO_ICMP_ID = 1 << 8
FILTER_FLAG_CTA_PROTO_ICMPV6_TYPE = 1 << 9
FILTER_FLAG_CTA_PROTO_ICMPV6_CODE = 1 << 10
FILTER_FLAG_CTA_PROTO_ICMPV6_ID = 1 << 11

FILTER_FLAG_ALL_CTA_PROTO = (
    FILTER_FLAG_CTA_PROTO_SRC_PORT
    | FILTER_FLAG_CTA_PROTO_DST_PORT
    | FILTER_FLAG_CTA_PROTO_ICMP_TYPE
    | FILTER_FLAG_CTA_PROTO_ICMP_CODE
    | FILTER_FLAG_CTA_PROTO_ICMP_ID
    | FILTER_FLAG_CTA_PROTO_ICMPV6_TYPE
    | FILTER_FLAG_CTA_PROTO_ICMPV6_CODE
    | FILTER_FLAG_CTA_PROTO_ICMPV6_ID
)
FILTER_FLAG_ALL = 0xFFFFFFFF


class NFCTAttr(object):
    def attrs(self):
        return []


class NFCTAttrTuple(NFCTAttr):
    __slots__ = (
        'saddr',
        'daddr',
        'proto',
        'sport',
        'dport',
        'icmp_id',
        'icmp_type',
        'family',
        '_attr_ip',
        '_attr_icmp',
    )

    def __init__(
        self,
        family=socket.AF_INET,
        saddr=None,
        daddr=None,
        proto=None,
        sport=None,
        dport=None,
        icmp_id=None,
        icmp_type=None,
        icmp_code=None,
    ):
        self.saddr = saddr
        self.daddr = daddr
        self.proto = proto
        self.sport = sport
        self.dport = dport
        self.icmp_id = icmp_id
        self.icmp_type = icmp_type
        self.icmp_code = icmp_code
        self.family = family

        self._attr_ip, self._attr_icmp = {
            socket.AF_INET: ['CTA_IP_V4', 'CTA_PROTO_ICMP'],
            socket.AF_INET6: ['CTA_IP_V6', 'CTA_PROTO_ICMPV6'],
        }[self.family]

    def proto_name(self):
        return IP_PROTOCOLS.get(self.proto, None)

    def reverse(self):
        return NFCTAttrTuple(
            family=self.family,
            saddr=self.daddr,
            daddr=self.saddr,
            proto=self.proto,
            sport=self.dport,
            dport=self.sport,
            icmp_id=self.icmp_id,
            icmp_type=self.icmp_type,
            icmp_code=self.icmp_code,
        )

    def attrs(self):
        cta_ip = []
        cta_proto = []
        cta_tuple = []

        self.flags = 0

        if self.saddr is not None:
            cta_ip.append([self._attr_ip + '_SRC', self.saddr])
            self.flags |= FILTER_FLAG_CTA_IP_SRC

        if self.daddr is not None:
            cta_ip.append([self._attr_ip + '_DST', self.daddr])
            self.flags |= FILTER_FLAG_CTA_IP_DST

        if self.proto is not None:
            cta_proto.append(['CTA_PROTO_NUM', self.proto])
            self.flags |= FILTER_FLAG_CTA_PROTO_NUM

        if self.sport is not None:
            cta_proto.append(['CTA_PROTO_SRC_PORT', self.sport])
            self.flags |= FILTER_FLAG_CTA_PROTO_SRC_PORT

        if self.dport is not None:
            cta_proto.append(['CTA_PROTO_DST_PORT', self.dport])
            self.flags |= FILTER_FLAG_CTA_PROTO_DST_PORT

        if self.icmp_id is not None:
            cta_proto.append([self._attr_icmp + '_ID', self.icmp_id])

        if self.icmp_type is not None:
            cta_proto.append([self._attr_icmp + '_TYPE', self.icmp_type])

        if self.icmp_code is not None:
            cta_proto.append([self._attr_icmp + '_CODE', self.icmp_code])

        if cta_ip:
            cta_tuple.append(['CTA_TUPLE_IP', {'attrs': cta_ip}])

        if cta_proto:
            cta_tuple.append(['CTA_TUPLE_PROTO', {'attrs': cta_proto}])

        return cta_tuple

    @classmethod
    def from_netlink(cls, family, ndmsg):
        cta_ip = ndmsg.get_attr('CTA_TUPLE_IP')
        cta_proto = ndmsg.get_attr('CTA_TUPLE_PROTO')
        kwargs = {'family': family}

        if family == socket.AF_INET:
            kwargs['saddr'] = cta_ip.get_attr('CTA_IP_V4_SRC')
            kwargs['daddr'] = cta_ip.get_attr('CTA_IP_V4_DST')
        elif family == socket.AF_INET6:
            kwargs['saddr'] = cta_ip.get_attr('CTA_IP_V6_SRC')
            kwargs['daddr'] = cta_ip.get_attr('CTA_IP_V6_DST')
        else:
            raise NotImplementedError(family)

        proto = cta_proto.get_attr('CTA_PROTO_NUM')
        kwargs['proto'] = proto

        if proto == socket.IPPROTO_ICMP:
            kwargs['icmp_id'] = cta_proto.get_attr('CTA_PROTO_ICMP_ID')
            kwargs['icmp_type'] = cta_proto.get_attr('CTA_PROTO_ICMP_TYPE')
            kwargs['icmp_code'] = cta_proto.get_attr('CTA_PROTO_ICMP_CODE')
        elif proto == socket.IPPROTO_ICMPV6:
            kwargs['icmp_id'] = cta_proto.get_attr('CTA_PROTO_ICMPV6_ID')
            kwargs['icmp_type'] = cta_proto.get_attr('CTA_PROTO_ICMPV6_TYPE')
            kwargs['icmp_code'] = cta_proto.get_attr('CTA_PROTO_ICMPV6_CODE')
        elif proto in (socket.IPPROTO_TCP, socket.IPPROTO_UDP):
            kwargs['sport'] = cta_proto.get_attr('CTA_PROTO_SRC_PORT')
            kwargs['dport'] = cta_proto.get_attr('CTA_PROTO_DST_PORT')

        return cls(**kwargs)

    def is_attr_match(self, other, attrname):
        l_attr = getattr(self, attrname)
        if l_attr is not None:
            r_attr = getattr(other, attrname)
            if l_attr != r_attr:
                return False
        return True

    def nla_eq(self, family, ndmsg):
        if self.family != family:
            return False

        test_attr = []
        cta_ip = ndmsg.get_attr('CTA_TUPLE_IP')
        if family == socket.AF_INET:
            test_attr.append((self.saddr, cta_ip, 'CTA_IP_V4_SRC'))
            test_attr.append((self.daddr, cta_ip, 'CTA_IP_V4_DST'))
        elif family == socket.AF_INET6:
            test_attr.append((self.saddr, cta_ip, 'CTA_IP_V6_SRC'))
            test_attr.append((self.daddr, cta_ip, 'CTA_IP_V6_DST'))
        else:
            raise NotImplementedError(family)

        if self.proto is not None:
            cta_proto = ndmsg.get_attr('CTA_TUPLE_PROTO')
            if self.proto != cta_proto.get_attr('CTA_PROTO_NUM'):
                return False

            if self.proto == socket.IPPROTO_ICMP:
                (
                    test_attr.append(
                        (self.icmp_id, cta_proto, 'CTA_PROTO_ICMP_ID')
                    )
                )
                (
                    test_attr.append(
                        (self.icmp_type, cta_proto, 'CTA_PROTO_ICMP_TYPE')
                    )
                )
                (
                    test_attr.append(
                        (self.icmp_code, cta_proto, 'CTA_PROTO_ICMP_CODE')
                    )
                )
            elif self.proto == socket.IPPROTO_ICMPV6:
                (
                    test_attr.append(
                        (self.icmp_id, cta_proto, 'CTA_PROTO_ICMPV6_ID')
                    )
                )
                (
                    test_attr.append(
                        (self.icmp_type, cta_proto, 'CTA_PROTO_ICMPV6_TYPE')
                    )
                )
                (
                    test_attr.append(
                        (self.icmp_code, cta_proto, 'CTA_PROTO_ICMPV6_CODE')
                    )
                )
            elif self.proto in (socket.IPPROTO_TCP, socket.IPPROTO_UDP):
                (
                    test_attr.append(
                        (self.sport, cta_proto, 'CTA_PROTO_SRC_PORT')
                    )
                )
                (
                    test_attr.append(
                        (self.dport, cta_proto, 'CTA_PROTO_DST_PORT')
                    )
                )

        for val, ndmsg, attrname in test_attr:
            if val is not None and val != ndmsg.get_attr(attrname):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise NotImplementedError()

        if self.family != other.family:
            return False

        for attrname in ('saddr', 'daddr'):
            if not self.is_attr_match(other, attrname):
                return False

        if self.proto is not None:
            if self.proto != other.proto:
                return False

            if self.proto in (socket.IPPROTO_UDP, socket.IPPROTO_TCP):
                for attrname in ('sport', 'dport'):
                    if not self.is_attr_match(other, attrname):
                        return False
            elif self.proto in (socket.IPPROTO_ICMP, socket.IPPROTO_ICMPV6):
                for attrname in ('icmp_id', 'icmp_type', 'icmp_code'):
                    if not self.is_attr_match(other, attrname):
                        return False

        return True

    def __repr__(self):
        proto_name = self.proto_name()
        if proto_name is None:
            proto_name = 'UNKNOWN'

        if self.family == socket.AF_INET:
            r = 'IPv4('
        elif self.family == socket.AF_INET6:
            r = 'IPv6('
        else:
            r = 'Unkown[family={}]('.format(self.family)
        r += 'saddr={}, daddr={}, '.format(self.saddr, self.daddr)

        r += '{}('.format(proto_name)
        if self.proto in (socket.IPPROTO_ICMP, socket.IPPROTO_ICMPV6):
            r += 'id={}, type={}, code={}'.format(
                self.icmp_id, self.icmp_type, self.icmp_code
            )
        elif self.proto in (socket.IPPROTO_TCP, socket.IPPROTO_UDP):
            r += 'sport={}, dport={}'.format(self.sport, self.dport)
        return r + '))'


class NFCTSocket(NetlinkSocket):
    policy = {
        k | (NFNL_SUBSYS_CTNETLINK << 8): v
        for k, v in {
            IPCTNL_MSG_CT_NEW: nfct_msg,
            IPCTNL_MSG_CT_GET: nfct_msg,
            IPCTNL_MSG_CT_DELETE: nfct_msg,
            IPCTNL_MSG_CT_GET_CTRZERO: nfct_msg,
            IPCTNL_MSG_CT_GET_STATS_CPU: nfct_stats_cpu,
            IPCTNL_MSG_CT_GET_STATS: nfct_stats,
            IPCTNL_MSG_CT_GET_DYING: nfct_msg,
            IPCTNL_MSG_CT_GET_UNCONFIRMED: nfct_msg,
        }.items()
    }

    def __init__(self, nfgen_family=socket.AF_INET, **kwargs):
        super(NFCTSocket, self).__init__(family=NETLINK_NETFILTER, **kwargs)
        self.register_policy(self.policy)
        self._nfgen_family = nfgen_family

    def request(self, msg, msg_type, **kwargs):
        msg['nfgen_family'] = self._nfgen_family
        msg_type |= NFNL_SUBSYS_CTNETLINK << 8
        return tuple(self.nlm_request(msg, msg_type, **kwargs))

    def dump(
        self,
        mark=None,
        mark_mask=0xFFFFFFFF,
        tuple_orig=None,
        tuple_reply=None,
    ):
        """Dump conntrack entries

        Several kernel side filtering are supported:
          * mark and mark_mask, for almost all kernel
          * tuple_orig and tuple_reply, since kernel 5.8 and newer.
            Warning: tuple_reply has a bug in kernel, fixed only recently.

        tuple_orig and tuple_reply are type NFCTAttrTuple.
        You can give only some attribute for filtering.

        Example::
            # Get only connections from 192.168.1.1
            filter = NFCTAttrTuple(saddr='192.168.1.1')
            ct.dump_entries(tuple_orig=filter)

            # Get HTTPS connections
            filter = NFCTAttrTuple(proto=socket.IPPROTO_TCP, dport=443)
            ct.dump_entries(tuple_orig=filter)

        Note that NFCTAttrTuple attributes are working like one AND operator.

        Example::
           # Get connections from 192.168.1.1 AND on port 443
           TCP = socket.IPPROTO_TCP
           filter = NFCTAttrTuple(saddr='192.168.1.1', proto=TCP, dport=443)
           ct.dump_entries(tuple_orig=filter)

        """
        if tuple_orig is not None:
            tuple_orig.attrs()  # for creating flags
            cta_filter = {
                'attrs': [['CTA_FILTER_ORIG_FLAGS', tuple_orig.flags]]
            }
            msg = nfct_msg.create_from(
                tuple_orig=tuple_orig, cta_filter=cta_filter
            )
        elif tuple_reply is not None:
            tuple_reply.attrs()
            cta_filter = {
                'attrs': [['CTA_FILTER_REPLY_FLAGS', tuple_reply.flags]]
            }
            msg = nfct_msg.create_from(
                tuple_reply=tuple_reply, cta_filter=cta_filter
            )
        elif mark:
            msg = nfct_msg.create_from(mark=mark, mark_mask=mark_mask)
        else:
            msg = nfct_msg.create_from()
        return self.request(
            msg, IPCTNL_MSG_CT_GET, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def stat(self):
        return self.request(
            nfct_msg(),
            IPCTNL_MSG_CT_GET_STATS_CPU,
            msg_flags=NLM_F_REQUEST | NLM_F_DUMP,
        )

    def count(self):
        return self.request(
            nfct_msg(),
            IPCTNL_MSG_CT_GET_STATS,
            msg_flags=NLM_F_REQUEST | NLM_F_DUMP,
            terminate=terminate_single_msg,
        )

    def flush(self, mark=None, mark_mask=None):
        msg = nfct_msg.create_from(mark=mark, mark_mask=mark_mask)
        return self.request(
            msg,
            IPCTNL_MSG_CT_DELETE,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK,
            terminate=terminate_error_msg,
        )

    def conntrack_max_size(self):
        return self.request(
            nfct_msg(),
            IPCTNL_MSG_CT_GET_STATS,
            msg_flags=NLM_F_REQUEST | NLM_F_DUMP,
            terminate=terminate_single_msg,
        )

    def entry(self, cmd, **kwargs):
        """
        Get or change a conntrack entry.

        Examples::
            # add an entry
            ct.entry('add', timeout=30,
                     tuple_orig=NFCTAttrTuple(
                         saddr='192.168.122.1', daddr='192.168.122.67',
                         proto=6, sport=34857, dport=5599),
                     tuple_reply=NFCTAttrTuple(
                         saddr='192.168.122.67', daddr='192.168.122.1',
                         proto=6, sport=5599, dport=34857))

            # set mark=5 on the matching entry
            ct.entry('set', mark=5,
                     tuple_orig=NFCTAttrTuple(
                         saddr='192.168.122.1', daddr='192.168.122.67',
                         proto=6, sport=34857, dport=5599))

            # get an entry
            ct.entry('get',
                     tuple_orig=NFCTAttrTuple(
                         saddr='192.168.122.1', daddr='192.168.122.67',
                         proto=6, sport=34857, dport=5599))

            # delete an entry
            ct.entry('del',
                     tuple_orig=NFCTAttrTuple(
                         saddr='192.168.122.1', daddr='192.168.122.67',
                         proto=6, sport=34857, dport=5599))
        """
        msg_type, msg_flags = {
            'add': [IPCTNL_MSG_CT_NEW, NLM_F_ACK | NLM_F_EXCL | NLM_F_CREATE],
            'set': [IPCTNL_MSG_CT_NEW, NLM_F_ACK],
            'get': [IPCTNL_MSG_CT_GET, NLM_F_ACK],
            'del': [IPCTNL_MSG_CT_DELETE, NLM_F_ACK],
        }[cmd]

        if msg_type == IPCTNL_MSG_CT_DELETE and not (
            'tuple_orig' in kwargs or 'tuple_reply' in kwargs
        ):
            raise ValueError('Deletion requires a tuple at least')

        return self.request(
            nfct_msg.create_from(**kwargs),
            msg_type,
            msg_flags=NLM_F_REQUEST | msg_flags,
            terminate=terminate_error_msg,
        )
