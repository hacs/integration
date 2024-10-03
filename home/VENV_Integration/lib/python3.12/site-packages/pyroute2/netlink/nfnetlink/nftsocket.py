"""
NFTSocket -- low level nftables API

See also: pyroute2.nftables
"""

import struct
import threading

from pyroute2.netlink import (
    NETLINK_NETFILTER,
    NLM_F_ACK,
    NLM_F_APPEND,
    NLM_F_CREATE,
    NLM_F_DUMP,
    NLM_F_EXCL,
    NLM_F_REPLACE,
    NLM_F_REQUEST,
    nla,
    nla_base_string,
    nlmsg_atoms,
)
from pyroute2.netlink.nfnetlink import NFNL_SUBSYS_NFTABLES, nfgen_msg
from pyroute2.netlink.nlsocket import NetlinkSocket

NFT_MSG_NEWTABLE = 0
NFT_MSG_GETTABLE = 1
NFT_MSG_DELTABLE = 2
NFT_MSG_NEWCHAIN = 3
NFT_MSG_GETCHAIN = 4
NFT_MSG_DELCHAIN = 5
NFT_MSG_NEWRULE = 6
NFT_MSG_GETRULE = 7
NFT_MSG_DELRULE = 8
NFT_MSG_NEWSET = 9
NFT_MSG_GETSET = 10
NFT_MSG_DELSET = 11
NFT_MSG_NEWSETELEM = 12
NFT_MSG_GETSETELEM = 13
NFT_MSG_DELSETELEM = 14
NFT_MSG_NEWGEN = 15
NFT_MSG_GETGEN = 16
NFT_MSG_TRACE = 17
NFT_MSG_NEWOBJ = 18
NFT_MSG_GETOBJ = 19
NFT_MSG_DELOBJ = 20
NFT_MSG_GETOBJ_RESET = 21
NFT_MSG_NEWFLOWTABLE = 22
NFT_MSG_GETFLOWTABLE = 23
NFT_MSG_DELFLOWTABLE = 24

# from nftables/include/datatype.h
DATA_TYPE_INVALID = 0
DATA_TYPE_VERDICT = 1
DATA_TYPE_NFPROTO = 2
DATA_TYPE_BITMASK = 3
DATA_TYPE_INTEGER = 4
DATA_TYPE_STRING = 5
DATA_TYPE_LLADDR = 6
DATA_TYPE_IPADDR = 7
DATA_TYPE_IP6ADDR = 8
DATA_TYPE_ETHERADDR = 9
DATA_TYPE_ETHERTYPE = 10
DATA_TYPE_ARPOP = 11
DATA_TYPE_INET_PROTOCOL = 12
DATA_TYPE_INET_SERVICE = 13
DATA_TYPE_ICMP_TYPE = 14
DATA_TYPE_TCP_FLAG = 15
DATA_TYPE_DCCP_PKTTYPE = 16
DATA_TYPE_MH_TYPE = 17
DATA_TYPE_TIME = 18
DATA_TYPE_MARK = 19
DATA_TYPE_IFINDEX = 20
DATA_TYPE_ARPHRD = 21
DATA_TYPE_REALM = 22
DATA_TYPE_CLASSID = 23
DATA_TYPE_UID = 24
DATA_TYPE_GID = 25
DATA_TYPE_CT_STATE = 26
DATA_TYPE_CT_DIR = 27
DATA_TYPE_CT_STATUS = 28
DATA_TYPE_ICMP6_TYPE = 29
DATA_TYPE_CT_LABEL = 30
DATA_TYPE_PKTTYPE = 31
DATA_TYPE_ICMP_CODE = 32
DATA_TYPE_ICMPV6_CODE = 33
DATA_TYPE_ICMPX_CODE = 34
DATA_TYPE_DEVGROUP = 35
DATA_TYPE_DSCP = 36
DATA_TYPE_ECN = 37
DATA_TYPE_FIB_ADDR = 38
DATA_TYPE_BOOLEAN = 39
DATA_TYPE_CT_EVENTBIT = 40
DATA_TYPE_IFNAME = 41
DATA_TYPE_IGMP_TYPE = 42
DATA_TYPE_TIME_DATE = 43
DATA_TYPE_TIME_HOUR = 44
DATA_TYPE_TIME_DAY = 45
DATA_TYPE_CGROUPV2 = 46

# from include/uapi/linux/netfilter.h
NFPROTO_INET = 1
NFPROTO_IPV4 = 2
NFPROTO_ARP = 3
NFPROTO_NETDEV = 5
NFPROTO_BRIDGE = 7
NFPROTO_IPV6 = 10


class nftnl_udata(nla_base_string):
    # TLV structures:
    # nftnl_udata
    #  <-------- HEADER --------> <------ PAYLOAD ------>
    # +------------+-------------+- - - - - - - - - - - -+
    # |    type    |     len     |         value         |
    # |  (1 byte)  |   (1 byte)  |                       |
    # +--------------------------+- - - - - - - - - - - -+
    #  <-- sizeof(nftnl_udata) -> <-- nftnl_udata->len -->
    __slots__ = ()

    @classmethod
    def udata_decode(cls, data):
        offset = 0
        result = []
        while offset + 2 < len(data):
            utype = data[offset]
            ulen = data[offset + 1]
            offset += 2
            if offset + ulen > len(data):
                return None  # bad decode
            try:
                type_name = cls.udata_types[utype]
            except IndexError:
                return None  # bad decode

            value = data[offset : offset + ulen]
            if type_name.endswith("_COMMENT") and value[-1] == 0:
                value = value[:-1]  # remove \x00 c *str
            result.append((type_name, value))
            offset += ulen
        return result

    @classmethod
    def udata_encode(cls, values):
        value = b""
        for type_name, udata in values:
            if isinstance(udata, str):
                udata = udata.encode()
            if type_name.endswith("_COMMENT") and udata[-1] != 0:
                udata = udata + b"\x00"
            utype = cls.udata_types.index(type_name)
            value += struct.pack("BB", utype, len(udata)) + udata
        return value

    def decode(self):
        nla_base_string.decode(self)
        value = self.udata_decode(self['value'])
        if value is not None:
            self.value = value

    def encode(self):
        if not isinstance(self.value, (bytes, str)):
            self['value'] = self.udata_encode(self.value)
        nla_base_string.encode(self)


class nft_map_uint8(nla):
    ops = {}
    fields = [('value', 'B')]

    def decode(self):
        nla.decode(self)
        self.value = self.ops.get(self['value'])


class nft_map_be32(nft_map_uint8):
    fields = [('value', '>I')]


class nft_map_be32_signed(nft_map_uint8):
    fields = [('value', '>i')]


class nft_flags_be32(nla):
    fields = [('value', '>I')]
    ops = None

    def decode(self):
        nla.decode(self)
        self.value = frozenset(
            o for i, o in enumerate(self.ops) if self['value'] & 1 << i
        )

    def encode(self):
        value = 0
        for i, name in enumerate(self.ops):
            if name in self.value:
                value |= 1 << i
        self["value"] = value
        nla.encode(self)


class nft_flags_be16(nla):
    fields = [('value', '>H')]
    ops = None

    def decode(self):
        nla.decode(self)
        self.value = frozenset(
            o for i, o in enumerate(self.ops) if self['value'] & 1 << i
        )


class nft_device(nla):
    class device_attributes(nla):
        nla_map = (
            ('NFTA_DEVICE_UNSPEC', 'none'),
            ('NFTA_DEVICE_NAME', 'asciiz'),
        )


class nft_gen_msg(nfgen_msg):
    nla_map = (
        ('NFTA_GEN_UNSPEC', 'none'),
        ('NFTA_GEN_ID', 'be32'),
        ('NFTA_GEN_PROC_PID', 'be32'),
        ('NFTA_GEN_PROC_NAME', 'asciiz'),
    )


class nft_chain_msg(nfgen_msg):
    prefix = 'NFTA_CHAIN_'
    nla_map = (
        ('NFTA_CHAIN_UNSPEC', 'none'),
        ('NFTA_CHAIN_TABLE', 'asciiz'),
        ('NFTA_CHAIN_HANDLE', 'be64'),
        ('NFTA_CHAIN_NAME', 'asciiz'),
        ('NFTA_CHAIN_HOOK', 'hook'),
        ('NFTA_CHAIN_POLICY', 'be32'),
        ('NFTA_CHAIN_USE', 'be32'),
        ('NFTA_CHAIN_TYPE', 'asciiz'),
        ('NFTA_CHAIN_COUNTERS', 'counters'),
        ('NFTA_CHAIN_PAD', 'hex'),
        ('NFTA_CHAIN_FLAGS', 'flags'),
        ('NFTA_CHAIN_ID', 'be32'),
        ('NFTA_CHAIN_USERDATA', 'hex'),
    )

    class counters(nla):
        nla_map = (
            ('NFTA_COUNTER_UNSPEC', 'none'),
            ('NFTA_COUNTER_BYTES', 'be64'),
            ('NFTA_COUNTER_PACKETS', 'be64'),
        )

    class hook(nft_device):
        nla_map = (
            ('NFTA_HOOK_UNSPEC', 'none'),
            ('NFTA_HOOK_HOOKNUM', 'be32'),
            ('NFTA_HOOK_PRIORITY', 'sbe32'),
            ('NFTA_HOOK_DEV', 'asciiz'),
            ('NFTA_HOOK_DEVS', 'device_attributes'),
        )

    class flags(nft_flags_be32):
        ops = ('NFT_CHAIN_HW_OFFLOAD', 'NFT_CHAIN_BINDING')


class nat_flags(nla):
    class nat_range(nft_flags_be32):
        ops = (
            'NF_NAT_RANGE_MAP_IPS',
            'NF_NAT_RANGE_PROTO_SPECIFIED',
            'NF_NAT_RANGE_PROTO_RANDOM',
            'NF_NAT_RANGE_PERSISTENT',
            'NF_NAT_RANGE_PROTO_RANDOM_FULLY',
            'NF_NAT_RANGE_PROTO_OFFSET',
            'NF_NAT_RANGE_NETMAP',
        )


class nft_regs(nla):
    class regs(nft_map_be32):
        ops = {
            0x00: 'NFT_REG_VERDICT',
            0x01: 'NFT_REG_1',
            0x02: 'NFT_REG_2',
            0x03: 'NFT_REG_3',
            0x04: 'NFT_REG_4',
            0x08: 'NFT_REG32_00',
            0x09: 'NFT_REG32_01',
            0x0A: 'NFT_REG32_02',
            0x0B: 'NFT_REG32_03',
            0x0C: 'NFT_REG32_04',
            0x0D: 'NFT_REG32_05',
            0x0E: 'NFT_REG32_06',
            0x0F: 'NFT_REG32_07',
            0x10: 'NFT_REG32_08',
            0x11: 'NFT_REG32_09',
            0x12: 'NFT_REG32_10',
            0x13: 'NFT_REG32_11',
            0x14: 'NFT_REG32_12',
            0x15: 'NFT_REG32_13',
            0x16: 'NFT_REG32_14',
            0x17: 'NFT_REG32_15',
        }


class nft_data(nla):
    class nfta_data(nla):
        nla_map = (
            ('NFTA_DATA_UNSPEC', 'none'),
            ('NFTA_DATA_VALUE', 'cdata'),
            ('NFTA_DATA_VERDICT', 'verdict'),
        )

        class verdict(nla):
            nla_map = (
                ('NFTA_VERDICT_UNSPEC', 'none'),
                ('NFTA_VERDICT_CODE', 'verdict_code'),
                ('NFTA_VERDICT_CHAIN', 'asciiz'),
            )

            class verdict_code(nft_map_be32_signed):
                ops = {
                    0: 'NF_DROP',
                    1: 'NF_ACCEPT',
                    2: 'NF_STOLEN',
                    3: 'NF_QUEUE',
                    4: 'NF_REPEAT',
                    5: 'NF_STOP',
                    -1: 'NFT_CONTINUE',
                    -2: 'NFT_BREAK',
                    -3: 'NFT_JUMP',
                    -4: 'NFT_GOTO',
                    -5: 'NFT_RETURN',
                }


# nft_expr struct, used for rules and set
class nft_contains_expr:
    class nft_expr(nla):
        header_type = 1

        nla_map = (
            ('NFTA_EXPR_UNSPEC', 'none'),
            ('NFTA_EXPR_NAME', 'asciiz'),
            ('NFTA_EXPR_DATA', 'expr'),
        )

        class nft_bitwise(nft_data, nft_regs):
            nla_map = (
                ('NFTA_BITWISE_UNSPEC', 'none'),
                ('NFTA_BITWISE_SREG', 'regs'),
                ('NFTA_BITWISE_DREG', 'regs'),
                ('NFTA_BITWISE_LEN', 'be32'),
                ('NFTA_BITWISE_MASK', 'nfta_data'),
                ('NFTA_BITWISE_XOR', 'nfta_data'),
                ('NFTA_BITWISE_OP', 'bitwise_op'),
                ('NFTA_BITWISE_DATA', 'nfta_data'),
            )

            class bitwise_op(nft_map_be32):
                ops = {
                    0: 'NFT_BITWISE_BOOL',
                    1: 'NFT_BITWISE_LSHIFT',
                    2: 'NFT_BITWISE_RSHIFT',
                }

        class nft_byteorder(nft_regs):
            nla_map = (
                ('NFTA_BYTEORDER_UNSPEC', 'none'),
                ('NFTA_BYTEORDER_SREG', 'regs'),
                ('NFTA_BYTEORDER_DREG', 'regs'),
                ('NFTA_BYTEORDER_OP', 'ops'),
                ('NFTA_BYTEORDER_LEN', 'be32'),
                ('NFTA_BYTEORDER_SIZE', 'be32'),
            )

            class ops(nft_map_be32):
                ops = {0: 'NFT_BYTEORDER_NTOH', 1: 'NFT_BYTEORDER_HTON'}

        class nft_cmp(nft_data, nft_regs):
            nla_map = (
                ('NFTA_CMP_UNSPEC', 'none'),
                ('NFTA_CMP_SREG', 'regs'),
                ('NFTA_CMP_OP', 'ops'),
                ('NFTA_CMP_DATA', 'nfta_data'),
            )

            class ops(nft_map_be32):
                ops = {
                    0: 'NFT_CMP_EQ',
                    1: 'NFT_CMP_NEQ',
                    2: 'NFT_CMP_LT',
                    3: 'NFT_CMP_LTE',
                    4: 'NFT_CMP_GT',
                    5: 'NFT_CMP_GTE',
                }

        class nft_match(nla):
            nla_map = (
                ('NFTA_MATCH_UNSPEC', 'none'),
                ('NFTA_MATCH_NAME', 'asciiz'),
                ('NFTA_MATCH_REV', 'be32'),
                ('NFTA_MATCH_INFO', 'hex'),
                ('NFTA_MATCH_PROTOCOL', 'hex'),
                ('NFTA_MATCH_FLAGS', 'hex'),
            )

        class nft_target(nla):
            nla_map = (
                ('NFTA_TARGET_UNSPEC', 'none'),
                ('NFTA_TARGET_NAME', 'asciiz'),
                ('NFTA_TARGET_REV', 'be32'),
                ('NFTA_TARGET_INFO', 'hex'),
                ('NFTA_TARGET_PROTOCOL', 'hex'),
                ('NFTA_TARGET_FLAGS', 'hex'),
            )

        class nft_connlimit(nla):
            nla_map = (
                ('NFTA_CONNLIMIT_UNSPEC', 'none'),
                ('NFTA_CONNLIMIT_COUNT', 'be32'),
                ('NFTA_CONNLIMIT_FLAGS', 'connlimit_flags'),
            )

            class connlimit_flags(nft_flags_be32):
                ops = ('NFT_LIMIT_F_INV',)

        class nft_counter(nla):
            nla_map = (
                ('NFTA_COUNTER_UNSPEC', 'none'),
                ('NFTA_COUNTER_BYTES', 'be64'),
                ('NFTA_COUNTER_PACKETS', 'be64'),
            )

        class nft_ct(nft_regs):
            nla_map = (
                ('NFTA_CT_UNSPEC', 'none'),
                ('NFTA_CT_DREG', 'regs'),
                ('NFTA_CT_KEY', 'keys'),
                ('NFTA_CT_DIRECTION', 'uint8'),
                ('NFTA_CT_SREG', 'regs'),
            )

            class keys(nft_map_be32):
                ops = {
                    0x00: 'NFT_CT_STATE',
                    0x01: 'NFT_CT_DIRECTION',
                    0x02: 'NFT_CT_STATUS',
                    0x03: 'NFT_CT_MARK',
                    0x04: 'NFT_CT_SECMARK',
                    0x05: 'NFT_CT_EXPIRATION',
                    0x06: 'NFT_CT_HELPER',
                    0x07: 'NFT_CT_L3PROTOCOL',
                    0x08: 'NFT_CT_SRC',
                    0x09: 'NFT_CT_DST',
                    0x0A: 'NFT_CT_PROTOCOL',
                    0x0B: 'NFT_CT_PROTO_SRC',
                    0x0C: 'NFT_CT_PROTO_DST',
                    0x0D: 'NFT_CT_LABELS',
                    0x0E: 'NFT_CT_PKTS',
                    0x0F: 'NFT_CT_BYTES',
                    0x10: 'NFT_CT_AVGPKT',
                    0x11: 'NFT_CT_ZONE',
                    0x12: 'NFT_CT_EVENTMASK',
                    0x13: 'NFT_CT_SRC_IP',
                    0x14: 'NFT_CT_DST_IP',
                    0x15: 'NFT_CT_SRC_IP6',
                    0x16: 'NFT_CT_DST_IP6',
                    0x17: 'NFT_CT_ID',
                }

        class nft_dup(nft_regs):
            nla_map = (
                ('NFTA_DUP_UNSPEC', 'none'),
                ('NFTA_DUP_SREG_ADDR', 'regs'),
                ('NFTA_DUP_SREG_DEV', 'regs'),
            )

        class nft_exthdr(nft_regs):
            nla_map = (
                ('NFTA_EXTHDR_UNSPEC', 'none'),
                ('NFTA_EXTHDR_DREG', 'regs'),
                ('NFTA_EXTHDR_TYPE', 'uint8'),
                ('NFTA_EXTHDR_OFFSET', 'be32'),
                ('NFTA_EXTHDR_LEN', 'be32'),
                ('NFTA_EXTHDR_FLAGS', 'exthdr_flags'),
                ('NFTA_EXTHDR_OP', 'exthdr_op'),
                ('NFTA_EXTHDR_SREG', 'regs'),
            )

            class exthdr_flags(nft_flags_be32):
                ops = ('NFT_EXTHDR_F_PRESENT',)

            class exthdr_op(nft_map_be32):
                ops = {
                    0: 'NFT_EXTHDR_OP_IPV6',
                    1: 'NFT_EXTHDR_OP_TCPOPT',
                    2: 'NFT_EXTHDR_OP_IPV4',
                }

        class nft_fib(nft_regs):
            nla_map = (
                ('NFTA_FIB_UNSPEC', 'none'),
                ('NFTA_FIB_DREG', 'regs'),
                ('NFTA_FIB_RESULT', 'fib_result'),
                ('NFTA_FIB_FLAGS', 'fib_flags'),
            )

            class fib_result(nft_flags_be32):
                ops = (
                    'NFT_FIB_RESULT_UNSPEC',
                    'NFT_FIB_RESULT_OIF',
                    'NFT_FIB_RESULT_OIFNAME',
                    'NFT_FIB_RESULT_ADDRTYPE',
                )

            class fib_flags(nft_map_be32):
                ops = {
                    0: 'NFTA_FIB_F_SADDR',
                    1: 'NFTA_FIB_F_DADDR',
                    2: 'NFTA_FIB_F_MARK',
                    3: 'NFTA_FIB_F_IIF',
                    4: 'NFTA_FIB_F_OIF',
                    5: 'NFTA_FIB_F_PRESENT',
                }

        class nft_fwd(nft_regs):
            nla_map = (
                ('NFTA_FWD_UNSPEC', 'none'),
                ('NFTA_FWD_SREG_DEV', 'regs'),
                ('NFTA_FWD_SREG_ADDR', 'regs'),
                ('NFTA_FWD_NFPROTO', 'u32'),
            )

        class nft_hash(nft_regs):
            nla_map = (
                ('NFTA_HASH_UNSPEC', 'none'),
                ('NFTA_HASH_SREG', 'regs'),
                ('NFTA_HASH_DREG', 'regs'),
                ('NFTA_HASH_LEN', 'be32'),
                ('NFTA_HASH_MODULUS', 'be32'),
                ('NFTA_HASH_SEED', 'be32'),
                ('NFTA_HASH_OFFSET', 'be32'),
                ('NFTA_HASH_TYPE', 'hash_type'),
                ('NFTA_HASH_SET_NAME', 'asciiz'),
                ('NFTA_HASH_SET_ID', 'be32'),
            )

            class hash_type(nft_map_be32):
                ops = {0: 'NFT_HASH_JENKINS', 1: 'NFT_HASH_SYM'}

        class nft_immediate(nft_data, nft_regs):
            nla_map = (
                ('NFTA_IMMEDIATE_UNSPEC', 'none'),
                ('NFTA_IMMEDIATE_DREG', 'regs'),
                ('NFTA_IMMEDIATE_DATA', 'nfta_data'),
            )

        class nft_limit(nla):
            nla_map = (
                ('NFTA_LIMIT_UNSPEC', 'none'),
                ('NFTA_LIMIT_RATE', 'be64'),
                ('NFTA_LIMIT_UNIT', 'be64'),
                ('NFTA_LIMIT_BURST', 'be32'),
                ('NFTA_LIMIT_TYPE', 'types'),
                ('NFTA_LIMIT_FLAGS', 'be32'),
            )  # make flags type

            class types(nft_map_be32):
                ops = {0: 'NFT_LIMIT_PKTS', 1: 'NFT_LIMIT_PKT_BYTES'}

        class nft_log(nla):
            nla_map = (
                ('NFTA_LOG_UNSPEC', 'none'),
                ('NFTA_LOG_GROUP', 'be32'),
                ('NFTA_LOG_PREFIX', 'asciiz'),
                ('NFTA_LOG_SNAPLEN', 'be32'),
                ('NFTA_LOG_QTHRESHOLD', 'be32'),
                ('NFTA_LOG_LEVEL', 'log_level'),
                ('NFTA_LOG_FLAGS', 'log_flags'),
            )

            class log_level(nft_map_be32):
                ops = {
                    0: 'NFT_LOGLEVEL_EMERG',
                    1: 'NFT_LOGLEVEL_ALERT',
                    2: 'NFT_LOGLEVEL_CRIT',
                    3: 'NFT_LOGLEVEL_ERR',
                    4: 'NFT_LOGLEVEL_WARNING',
                    5: 'NFT_LOGLEVEL_NOTICE',
                    6: 'NFT_LOGLEVEL_INFO',
                    7: 'NFT_LOGLEVEL_DEBUG',
                    8: 'NFT_LOGLEVEL_AUDIT',
                }

            class log_flags(nft_flags_be32):
                ops = (
                    'NF_LOG_TCPSEQ',
                    'NF_LOG_TCPOPT',
                    'NF_LOG_IPOPT',
                    'NF_LOG_UID',
                    'NF_LOG_NFLOG',
                    'NF_LOG_MACDECODE',
                )

        class nft_lookup(nft_regs):
            nla_map = (
                ('NFTA_LOOKUP_UNSPEC', 'none'),
                ('NFTA_LOOKUP_SET', 'asciiz'),
                ('NFTA_LOOKUP_SREG', 'regs'),
                ('NFTA_LOOKUP_DREG', 'regs'),
                ('NFTA_LOOKUP_SET_ID', 'be32'),
                ('NFTA_LOOKUP_FLAGS', 'lookup_flags'),
            )

            class lookup_flags(nft_flags_be32):
                ops = ('NFT_LOOKUP_F_INV',)

        class nft_masq(nft_regs, nat_flags):
            nla_map = (
                ('NFTA_MASQ_UNSPEC', 'none'),
                ('NFTA_MASQ_FLAGS', 'nat_range'),
                ('NFTA_MASQ_REG_PROTO_MIN', 'regs'),
                ('NFTA_MASQ_REG_PROTO_MAX', 'regs'),
            )

        class nft_meta(nft_regs):
            nla_map = (
                ('NFTA_META_UNSPEC', 'none'),
                ('NFTA_META_DREG', 'regs'),
                ('NFTA_META_KEY', 'meta_key'),
                ('NFTA_META_SREG', 'regs'),
            )

            class meta_key(nft_map_be32):
                ops = {
                    0: 'NFT_META_LEN',
                    1: 'NFT_META_PROTOCOL',
                    2: 'NFT_META_PRIORITY',
                    3: 'NFT_META_MARK',
                    4: 'NFT_META_IIF',
                    5: 'NFT_META_OIF',
                    6: 'NFT_META_IIFNAME',
                    7: 'NFT_META_OIFNAME',
                    8: 'NFT_META_IIFTYPE',
                    9: 'NFT_META_OIFTYPE',
                    10: 'NFT_META_SKUID',
                    11: 'NFT_META_SKGID',
                    12: 'NFT_META_NFTRACE',
                    13: 'NFT_META_RTCLASSID',
                    14: 'NFT_META_SECMARK',
                    15: 'NFT_META_NFPROTO',
                    16: 'NFT_META_L4PROTO',
                    17: 'NFT_META_BRI_IIFNAME',
                    18: 'NFT_META_BRI_OIFNAME',
                    19: 'NFT_META_PKTTYPE',
                    20: 'NFT_META_CPU',
                    21: 'NFT_META_IIFGROUP',
                    22: 'NFT_META_OIFGROUP',
                    23: 'NFT_META_CGROUP',
                    24: 'NFT_META_PRANDOM',
                    25: 'NFT_META_SECPATH',
                    26: 'NFT_META_IIFKIND',
                    27: 'NFT_META_OIFKIND',
                    28: 'NFT_META_BRI_IIFPVID',
                    29: 'NFT_META_BRI_IIFVPROTO',
                    30: 'NFT_META_TIME_NS',
                    31: 'NFT_META_TIME_DAY',
                    32: 'NFT_META_TIME_HOUR',
                    33: 'NFT_META_SDIF',
                    34: 'NFT_META_SDIFNAME',
                }

        class nft_nat(nft_regs, nat_flags):
            nla_map = (
                ('NFTA_NAT_UNSPEC', 'none'),
                ('NFTA_NAT_TYPE', 'types'),
                ('NFTA_NAT_FAMILY', 'be32'),
                ('NFTA_NAT_REG_ADDR_MIN', 'regs'),
                ('NFTA_NAT_REG_ADDR_MAX', 'regs'),
                ('NFTA_NAT_REG_PROTO_MIN', 'regs'),
                ('NFTA_NAT_REG_PROTO_MAX', 'regs'),
                ('NFTA_NAT_FLAGS', 'nat_range'),
            )

            class types(nft_map_be32):
                ops = {0: 'NFT_NAT_SNAT', 1: 'NFT_NAT_DNAT'}

        class nft_numgen(nft_regs):
            nla_map = (
                ('NFTA_NG_UNSPEC', 'none'),
                ('NFTA_NG_DREG', 'regs'),
                ('NFTA_NG_MODULUS', 'be32'),
                ('NFTA_NG_TYPE', 'types'),
                ('NFTA_NG_OFFSET', 'be32'),
                ('NFTA_NG_SET_NAME', 'asciiz'),
                ('NFTA_NG_SET_ID', 'be32'),
            )

            class types(nft_map_be32):
                ops = {0: 'NFT_NG_INCREMENTAL', 1: 'NFT_NG_RANDOM'}

        class nft_objref(nft_regs):
            nla_map = (
                ('NFTA_OBJREF_UNSPEC', 'none'),
                ('NFTA_OBJREF_IMM_TYPE', 'regs'),
                ('NFTA_OBJREF_IMM_NAME', 'asciiz'),
                ('NFTA_OBJREF_SET_SREG', 'regs'),
                ('NFTA_OBJREF_SET_NAME', 'asciiz'),
                ('NFTA_OBJREF_SET_ID', 'be32'),
            )

        class nft_offload(nla):
            nla_map = (
                ('NFTA_FLOW_UNSPEC', 'none'),
                ('NFTA_FLOW_TABLE_NAME', 'asciiz'),
            )

        class nft_osf(nft_regs):
            nla_map = (
                ('NFTA_OSF_UNSPEC', 'none'),
                ('NFTA_OSF_DREG', 'regs'),
                ('NFTA_OSF_TTL', 'uint8'),
                ('NFTA_OSF_FLAGS', 'osf_flags'),
            )

            class osf_flags(nft_flags_be32):
                ops = ('NFT_OSF_F_VERSION',)

        class nft_payload(nft_regs):
            nla_map = (
                ('NFTA_PAYLOAD_UNSPEC', 'none'),
                ('NFTA_PAYLOAD_DREG', 'regs'),
                ('NFTA_PAYLOAD_BASE', 'base_type'),
                ('NFTA_PAYLOAD_OFFSET', 'be32'),
                ('NFTA_PAYLOAD_LEN', 'be32'),
                ('NFTA_PAYLOAD_SREG', 'regs'),
                ('NFTA_PAYLOAD_CSUM_TYPE', 'csum_type'),
                ('NFTA_PAYLOAD_CSUM_OFFSET', 'be32'),
                ('NFTA_PAYLOAD_CSUM_FLAGS', 'csum_flags'),
            )

            class base_type(nft_map_be32):
                ops = {
                    0: 'NFT_PAYLOAD_LL_HEADER',
                    1: 'NFT_PAYLOAD_NETWORK_HEADER',
                    2: 'NFT_PAYLOAD_TRANSPORT_HEADER',
                }

            class csum_type(nft_map_be32):
                ops = {
                    0: 'NFT_PAYLOAD_CSUM_NONE',
                    1: 'NFT_PAYLOAD_CSUM_INET',  # RFC 791
                    2: 'NFT_PAYLOAD_CSUM_SCTP',
                }  # RFC 3309

            class csum_flags(nft_flags_be32):
                ops = ('NFT_PAYLOAD_L4CSUM_PSEUDOHDR',)

        class nft_queue(nft_regs):
            nla_map = (
                ('NFTA_QUEUE_UNSPEC', 'none'),
                ('NFTA_QUEUE_NUM', 'be16'),
                ('NFTA_QUEUE_TOTAL', 'be16'),
                ('NFTA_QUEUE_FLAGS', 'queue_flags'),
                ('NFTA_QUEUE_SREG_QNUM', 'regs'),
            )

            class queue_flags(nft_flags_be16):
                ops = ('NFT_QUEUE_FLAG_BYPASS', 'NFT_QUEUE_FLAG_CPU_FANOUT')

        class nft_quota(nla):
            nla_map = (
                ('NFTA_QUOTA_UNSPEC', 'none'),
                ('NFTA_QUOTA_BYTES', 'be16'),
                ('NFTA_QUOTA_FLAGS', 'quota_flags'),
                ('NFTA_QUOTA_PAD', 'hex'),
                ('NFTA_QUOTA_CONSUMED', 'be64'),
            )

            class quota_flags(nft_flags_be32):
                ops = ('NFT_QUOTA_F_INV', 'NFT_QUOTA_F_DEPLETED')

        class nft_range(nft_regs, nft_data):
            nla_map = (
                ('NFTA_RANGE_UNSPEC', 'none'),
                ('NFTA_RANGE_SREG', 'regs'),
                ('NFTA_RANGE_OP', 'range_op'),
                ('NFTA_RANGE_FROM_DATA', 'nfta_data'),
                ('NFTA_RANGE_TO_DATA', 'nfta_data'),
            )

            class range_op(nft_map_be32):
                ops = {0: 'NFT_RANGE_EQ', 1: 'NFT_RANGE_NEQ'}

        class nft_redir(nft_regs, nat_flags):
            nla_map = (
                ('NFTA_REDIR_UNSPEC', 'none'),
                ('NFTA_REDIR_REG_PROTO_MIN', 'regs'),
                ('NFTA_REDIR_REG_PROTO_MAX', 'regs'),
                ('NFTA_REDIR_FLAGS', 'nat_range'),
            )

        class nft_reject(nla):
            nla_map = (
                ('NFTA_REJECT_UNSPEC', 'none'),
                ('NFTA_REJECT_TYPE', 'types'),
                ('NFTA_REJECT_ICMP_CODE', 'codes'),
            )

            class types(nft_map_be32):
                ops = {
                    0: 'NFT_REJECT_ICMP_UNREACH',
                    1: 'NFT_REJECT_TCP_RST',
                    2: 'NFT_REJECT_ICMPX_UNREACH',
                }

            class codes(nft_map_uint8):
                ops = {
                    0: 'NFT_REJECT_ICMPX_NO_ROUTE',
                    1: 'NFT_REJECT_ICMPX_PORT_UNREACH',
                    2: 'NFT_REJECT_ICMPX_HOST_UNREACH',
                    3: 'NFT_REJECT_ICMPX_ADMIN_PROHIBITED',
                }

        class nft_rt(nft_regs):
            nla_map = (
                ('NFTA_RT_UNSPEC', 'none'),
                ('NFTA_RT_DREG', 'regs'),
                ('NFTA_RT_KEY', 'rt_keys'),
            )

            class rt_keys(nft_map_be32):
                ops = {
                    0: 'NFT_RT_CLASSID',
                    1: 'NFT_RT_NEXTHOP4',
                    2: 'NFT_RT_NEXTHOP6',
                    3: 'NFT_RT_TCPMSS',
                    4: 'NFT_RT_XFRM',
                }

        class nft_secmark(nla):
            nla_map = (
                ('NFTA_SECMARK_UNSPEC', 'none'),
                ('NFTA_SECMARK_CTX', 'asciiz'),
            )

        class nft_socket(nft_regs):
            nla_map = (
                ('NFTA_SOCKET_UNSPEC', 'none'),
                ('NFTA_SOCKET_KEY', 'socket_keys'),
                ('NFTA_SOCKET_DREG', 'regs'),
            )

            class socket_keys(nft_map_be32):
                ops = {
                    0: 'NFT_SOCKET_TRANSPARENT',
                    1: 'NFT_SOCKET_MARK',
                    2: 'NFT_SOCKET_WILDCARD',
                }

        class nft_synproxy(nla):
            nla_map = (
                ('NFTA_SYNPROXY_UNSPEC', 'none'),
                ('NFTA_SYNPROXY_MSS', 'u16'),
                ('NFTA_SYNPROXY_WSCALE', 'uint8'),
                ('NFTA_SYNPROXY_FLAGS', 'synproxy_flags'),
            )

            class synproxy_flags(nft_flags_be32):
                ops = (
                    'NF_SYNPROXY_OPT_MSS',
                    'NF_SYNPROXY_OPT_WSCALE',
                    'NF_SYNPROXY_OPT_SACK_PERM',
                    'NF_SYNPROXY_OPT_TIMESTAMP',
                    'NF_SYNPROXY_OPT_ECN',
                )

        class nft_tproxy(nft_regs):
            nla_map = (
                ('NFTA_TPROXY_UNSPEC', 'none'),
                ('NFTA_TPROXY_FAMILY', 'regs'),
                ('NFTA_TPROXY_REG_ADDR', 'regs'),
                ('NFTA_TPROXY_REG_PORT', 'regs'),
            )

        class nft_dynset(nft_regs):
            rule_expr = None
            nla_map = (
                ('NFTA_DYNSET_UNSPEC', 'none'),
                ('NFTA_DYNSET_SET_NAME', 'asciiz'),
                ('NFTA_DYNSET_SET_ID', 'be32'),
                ('NFTA_DYNSET_OP', 'dynset_op'),
                ('NFTA_DYNSET_SREG_KEY', 'regs'),
                ('NFTA_DYNSET_SREG_DATA', 'regs'),
                ('NFTA_DYNSET_TIMEOUT', 'be64'),
                ('NFTA_DYNSET_EXPR', 'rule_expr'),
                ('NFTA_DYNSET_PAD', 'hex'),
                ('NFTA_DYNSET_FLAGS', 'dynset_flags'),
            )

            class dynset_flags(nft_flags_be32):
                ops = ('NFT_DYNSET_F_INV',)

            class dynset_op(nft_map_be32):
                ops = {
                    0: 'NFT_DYNSET_OP_ADD',
                    1: 'NFT_DYNSET_OP_UPDATE',
                    2: 'NFT_DYNSET_OP_DELETE',
                }

        class nft_xfrm(nft_regs):
            nla_map = (
                ('NFTA_XFRM_UNSPEC', 'none'),
                ('NFTA_XFRM_DREG', 'regs'),
                ('NFTA_XFRM_KEY', 'xfrm_key'),
                ('NFTA_XFRM_DIR', 'uint8'),
                ('NFTA_XFRM_SPNUM', 'be32'),
            )

            class xfrm_key(nft_map_be32):
                ops = {
                    0: 'NFT_XFRM_KEY_UNSPEC',
                    1: 'NFT_XFRM_KEY_DADDR_IP4',
                    2: 'NFT_XFRM_KEY_DADDR_IP6',
                    3: 'NFT_XFRM_KEY_SADDR_IP4',
                    4: 'NFT_XFRM_KEY_SADDR_IP6',
                    5: 'NFT_XFRM_KEY_REQID',
                    6: 'NFT_XFRM_KEY_SPI',
                }

        @staticmethod
        def expr(self, *argv, **kwarg):
            data_type = self.get_attr('NFTA_EXPR_NAME')
            expr = getattr(self, 'nft_%s' % data_type, self.hex)
            if hasattr(expr, 'rule_expr'):
                expr.rule_expr = self.__class__
            return expr


class nft_rule_msg(nfgen_msg, nft_contains_expr):
    prefix = 'NFTA_RULE_'
    nla_map = (
        ('NFTA_RULE_UNSPEC', 'none'),
        ('NFTA_RULE_TABLE', 'asciiz'),
        ('NFTA_RULE_CHAIN', 'asciiz'),
        ('NFTA_RULE_HANDLE', 'be64'),
        ('NFTA_RULE_EXPRESSIONS', '*nft_expr'),
        ('NFTA_RULE_COMPAT', 'hex'),
        ('NFTA_RULE_POSITION', 'be64'),
        ('NFTA_RULE_USERDATA', 'hex'),
        ('NFTA_RULE_PAD', 'hex'),
        ('NFTA_RULE_ID', 'be32'),
        ('NFTA_RULE_POSITION_ID', 'be32'),
        ('NFTA_RULE_CHAIN_ID', 'be32'),
    )


class nft_set_msg(nfgen_msg, nft_contains_expr):
    prefix = 'NFTA_SET_'
    nla_map = (
        ('NFTA_SET_UNSPEC', 'none'),
        ('NFTA_SET_TABLE', 'asciiz'),
        ('NFTA_SET_NAME', 'asciiz'),
        ('NFTA_SET_FLAGS', 'set_flags'),
        ('NFTA_SET_KEY_TYPE', 'be32'),
        ('NFTA_SET_KEY_LEN', 'be32'),
        ('NFTA_SET_DATA_TYPE', 'be32'),
        ('NFTA_SET_DATA_LEN', 'be32'),
        ('NFTA_SET_POLICY', 'set_policy'),
        ('NFTA_SET_DESC', 'set_desc'),
        ('NFTA_SET_ID', 'be32'),
        ('NFTA_SET_TIMEOUT', 'be64'),
        ('NFTA_SET_GC_INTERVAL', 'be32'),
        ('NFTA_SET_USERDATA', 'set_udata'),
        ('NFTA_SET_PAD', 'hex'),
        ('NFTA_SET_OBJ_TYPE', 'be32'),
        ('NFTA_SET_HANDLE', 'be64'),
        ('NFTA_SET_EXPR', 'nft_expr'),
        ('NFTA_SET_EXPRESSIONS', '*nft_expr'),
    )

    class set_udata(nftnl_udata):
        udata_types = (
            "NFTNL_UDATA_SET_KEYBYTEORDER",
            "NFTNL_UDATA_SET_DATABYTEORDER",
            "NFTNL_UDATA_SET_MERGE_ELEMENTS",
            "NFTNL_UDATA_SET_KEY_TYPEOF",
            "NFTNL_UDATA_SET_DATA_TYPEOF",
            "NFTNL_UDATA_SET_EXPR",
            "NFTNL_UDATA_SET_DATA_INTERVAL",
            "NFTNL_UDATA_SET_COMMENT",
        )

    class set_flags(nft_flags_be32):
        ops = (
            'NFT_SET_ANONYMOUS',
            'NFT_SET_CONSTANT',
            'NFT_SET_INTERVAL',
            'NFT_SET_MAP',
            'NFT_SET_TIMEOUT',
            'NFT_SET_EVAL',
            'NFT_SET_OBJECT',
            'NFT_SET_CONCAT',
        )

    class set_policy(nft_map_be32):
        ops = {0: 'NFT_SET_POL_PERFORMANCE', 1: 'NFT_SET_POL_MEMORY'}

    class set_desc(nla):
        nla_map = (
            ('NFTA_SET_DESC_UNSPEC', 'none'),
            ('NFTA_SET_DESC_SIZE', 'be32'),
            ('NFTA_SET_DESC_CONCAT', '*list_elem'),
        )

        class list_elem(nla):
            nla_map = (
                ('NFTA_LIST_UNSPEC', 'none'),
                ('NFTA_LIST_ELEM', '*set_field_attribute'),
            )

            class set_field_attribute(nla):
                nla_map = (
                    ('NFTA_SET_FIELD_UNSPEC', 'none'),
                    ('NFTA_SET_FIELD_LEN', 'be32'),
                )


class nft_table_msg(nfgen_msg, nft_contains_expr):
    prefix = 'NFTA_TABLE_'
    nla_map = (
        ('NFTA_TABLE_UNSPEC', 'none'),
        ('NFTA_TABLE_NAME', 'asciiz'),
        ('NFTA_TABLE_FLAGS', 'be32'),
        ('NFTA_TABLE_USE', 'be32'),
        ('NFTA_TABLE_HANDLE', 'be64'),
        ('NFTA_TABLE_PAD', 'hex'),
        ('NFTA_TABLE_USERDATA', 'hex'),
    )


class nft_set_elem_list_msg(nfgen_msg):
    prefix = 'NFTA_SET_ELEM_LIST_'
    nla_map = (
        ('NFTA_SET_ELEM_LIST_UNSPEC', 'none'),
        ('NFTA_SET_ELEM_LIST_TABLE', 'asciiz'),
        ('NFTA_SET_ELEM_LIST_SET', 'asciiz'),
        ('NFTA_SET_ELEM_LIST_ELEMENTS', '*set_elem'),
        ('NFTA_SET_ELEM_LIST_SET_ID', 'be32'),
    )

    class set_elem(nla, nft_contains_expr):
        nla_map = (
            ('NFTA_SET_ELEM_UNSPEC', 'none'),
            ('NFTA_SET_ELEM_KEY', 'data_attributes'),
            ('NFTA_SET_ELEM_DATA', 'data_attributes'),
            ('NFTA_SET_ELEM_FLAGS', 'set_elem_flags'),
            ('NFTA_SET_ELEM_TIMEOUT', 'be64'),
            ('NFTA_SET_ELEM_EXPIRATION', 'be64'),
            ('NFTA_SET_ELEM_USERDATA', 'set_elem_udata'),
            ('NFTA_SET_ELEM_EXPR', 'nft_expr'),
            ('NFTA_SET_ELEM_PAD', 'hex'),
            ('NFTA_SET_ELEM_OBJREF', 'asciiz'),
            ('NFTA_SET_ELEM_KEY_END', 'data_attributes'),
            ('NFTA_SET_ELEM_EXPRESSIONS', '*nft_expr'),
        )

        class set_elem_udata(nftnl_udata):
            udata_types = (
                "NFTNL_UDATA_SET_ELEM_COMMENT",
                "NFTNL_UDATA_SET_ELEM_FLAGS",
            )

        class set_elem_flags(nft_flags_be32):
            ops = {1: 'NFT_SET_ELEM_INTERVAL_END'}

        class data_attributes(nla):
            nla_map = (
                ('NFTA_DATA_UNSPEC', 'none'),
                ('NFTA_DATA_VALUE', 'binary'),
                ('NFTA_DATA_VERDICT', 'verdict_attributes'),
            )

            class verdict_attributes(nla):
                nla_map = (
                    ('NFTA_VERDICT_UNSPEC', 'none'),
                    ('NFTA_VERDICT_CODE', 'verdict_code'),
                    ('NFTA_VERDICT_CHAIN', 'asciiz'),
                    ('NFTA_VERDICT_CHAIN_ID', 'be32'),
                )

                class verdict_code(nft_map_be32_signed):
                    ops = {
                        0: 'NF_DROP',
                        1: 'NF_ACCEPT',
                        2: 'NF_STOLEN',
                        3: 'NF_QUEUE',
                        4: 'NF_REPEAT',
                        5: 'NF_STOP',
                        -1: 'NFT_CONTINUE',
                        -2: 'NFT_BREAK',
                        -3: 'NFT_JUMP',
                        -4: 'NFT_GOTO',
                        -5: 'NFT_RETURN',
                    }


class nft_flowtable_msg(nfgen_msg):
    prefix = 'NFTA_FLOWTABLE_'
    nla_map = (
        ('NFTA_FLOWTABLE_UNSPEC', 'none'),
        ('NFTA_FLOWTABLE_TABLE', 'asciiz'),
        ('NFTA_FLOWTABLE_NAME', 'asciiz'),
        ('NFTA_FLOWTABLE_HOOK', 'flowtable_hook'),
        ('NFTA_FLOWTABLE_USE', 'be32'),
        ('NFTA_FLOWTABLE_HANDLE', 'be64'),
        ('NFTA_FLOWTABLE_PAD', 'hex'),
        ('NFTA_FLOWTABLE_FLAGS', 'nft_flowtable_flags'),
    )

    class nft_flowtable_flags(nft_flags_be32):
        ops = ('NFT_FLOWTABLE_HW_OFFLOAD', 'NFT_FLOWTABLE_COUNTER')

    class flowtable_hook(nft_device):
        nla_map = (
            ('NFTA_FLOWTABLE_HOOK_UNSPEC', 'none'),
            ('NFTA_FLOWTABLE_HOOK_NUM', 'be32'),
            ('NFTA_FLOWTABLE_HOOK_PRIORITY', 'be32'),
            ('NFTA_FLOWTABLE_HOOK_DEVS', 'device_attributes'),
        )


class NFTSocket(NetlinkSocket):
    '''
    NFNetlink socket (family=NETLINK_NETFILTER).

    Implements API to the nftables functionality.
    '''

    policy = {
        NFT_MSG_NEWTABLE: nft_table_msg,
        NFT_MSG_GETTABLE: nft_table_msg,
        NFT_MSG_DELTABLE: nft_table_msg,
        NFT_MSG_NEWCHAIN: nft_chain_msg,
        NFT_MSG_GETCHAIN: nft_chain_msg,
        NFT_MSG_DELCHAIN: nft_chain_msg,
        NFT_MSG_NEWRULE: nft_rule_msg,
        NFT_MSG_GETRULE: nft_rule_msg,
        NFT_MSG_DELRULE: nft_rule_msg,
        NFT_MSG_NEWSET: nft_set_msg,
        NFT_MSG_GETSET: nft_set_msg,
        NFT_MSG_DELSET: nft_set_msg,
        NFT_MSG_NEWGEN: nft_gen_msg,
        NFT_MSG_GETGEN: nft_gen_msg,
        NFT_MSG_NEWSETELEM: nft_set_elem_list_msg,
        NFT_MSG_GETSETELEM: nft_set_elem_list_msg,
        NFT_MSG_DELSETELEM: nft_set_elem_list_msg,
        NFT_MSG_NEWFLOWTABLE: nft_flowtable_msg,
        NFT_MSG_GETFLOWTABLE: nft_flowtable_msg,
        NFT_MSG_DELFLOWTABLE: nft_flowtable_msg,
    }

    def __init__(self, version=1, attr_revision=0, nfgen_family=2):
        super(NFTSocket, self).__init__(family=NETLINK_NETFILTER)
        policy = dict(
            [
                (x | (NFNL_SUBSYS_NFTABLES << 8), y)
                for (x, y) in self.policy.items()
            ]
        )
        self.register_policy(policy)
        self._proto_version = version
        self._attr_revision = attr_revision
        self._nfgen_family = nfgen_family
        self._ts = threading.local()
        self._write_lock = threading.RLock()

    def begin(self):
        with self._write_lock:
            if hasattr(self._ts, 'data'):
                # transaction is already started
                return False

            self._ts.data = b''
            self._ts.seqnum = (
                self.addr_pool.alloc(),  # begin
                self.addr_pool.alloc(),  # tx
                self.addr_pool.alloc(),
            )  # commit
            msg = nfgen_msg()
            msg['res_id'] = NFNL_SUBSYS_NFTABLES
            msg['header']['type'] = 0x10
            msg['header']['flags'] = NLM_F_REQUEST
            msg['header']['sequence_number'] = self._ts.seqnum[0]
            msg.encode()
            self._ts.data += msg.data
            return True

    def commit(self):
        with self._write_lock:
            msg = nfgen_msg()
            msg['res_id'] = NFNL_SUBSYS_NFTABLES
            msg['header']['type'] = 0x11
            msg['header']['flags'] = NLM_F_REQUEST
            msg['header']['sequence_number'] = self._ts.seqnum[2]
            msg.encode()
            self._ts.data += msg.data
            self.sendto(self._ts.data, (0, 0))
            for seqnum in self._ts.seqnum:
                self.addr_pool.free(seqnum, ban=10)
            del self._ts.data

    def request_get(
        self,
        msg,
        msg_type,
        msg_flags=NLM_F_REQUEST | NLM_F_DUMP,
        terminate=None,
    ):
        '''
        Read-only requests do not require transactions. Just run
        the request and get an answer.
        '''
        msg['nfgen_family'] = self._nfgen_family
        return tuple(
            self.nlm_request(
                msg,
                msg_type | (NFNL_SUBSYS_NFTABLES << 8),
                msg_flags,
                terminate=terminate,
            )
        )

    def request_put(self, msg, msg_type, msg_flags=NLM_F_REQUEST):
        '''
        Read-write requests.
        '''
        one_shot = self.begin()
        msg['header']['type'] = (NFNL_SUBSYS_NFTABLES << 8) | msg_type
        msg['header']['flags'] = msg_flags
        msg['header']['sequence_number'] = self._ts.seqnum[1]
        msg['nfgen_family'] = self._nfgen_family
        msg.encode()
        self._ts.data += msg.data
        if one_shot:
            self.commit()

    def _command(self, msg_class, commands, cmd, kwarg):
        flags = kwarg.pop('flags', NLM_F_ACK)
        cmd_name = cmd
        cmd_flags = {
            'add': NLM_F_CREATE | NLM_F_APPEND,
            'create': NLM_F_CREATE | NLM_F_APPEND | NLM_F_EXCL,
            'insert': NLM_F_CREATE,
            'replace': NLM_F_REPLACE,
        }
        flags |= cmd_flags.get(cmd, 0)
        flags |= NLM_F_REQUEST
        cmd = commands[cmd]
        msg = msg_class()
        msg['attrs'] = []
        #
        # a trick to pass keyword arguments as On rderedDict instance:
        #
        # ordered_args = OrderedDict()
        # ordered_args['arg1'] = value1
        # ordered_args['arg2'] = value2
        # ...
        # nft.rule('add', kwarg=ordered_args)
        #
        if 'kwarg' in kwarg:
            kwarg = kwarg['kwarg']
        #
        for key, value in kwarg.items():
            nla = msg_class.name2nla(key)
            msg['attrs'].append([nla, value])
        msg['header']['type'] = (NFNL_SUBSYS_NFTABLES << 8) | cmd
        msg['header']['flags'] = flags | NLM_F_REQUEST
        msg['nfgen_family'] = self._nfgen_family

        if cmd_name != 'get':
            trans_start = nfgen_msg()
            trans_start['res_id'] = NFNL_SUBSYS_NFTABLES
            trans_start['header']['type'] = 0x10
            trans_start['header']['flags'] = NLM_F_REQUEST

            trans_end = nfgen_msg()
            trans_end['res_id'] = NFNL_SUBSYS_NFTABLES
            trans_end['header']['type'] = 0x11
            trans_end['header']['flags'] = NLM_F_REQUEST

            messages = [trans_start, msg, trans_end]
            self.nlm_request_batch(messages, noraise=(flags & NLM_F_ACK) == 0)
            # Only throw an error when the request fails. For now,
            # do not return anything.
        else:
            return self.request_get(msg, msg['header']['type'], flags)[0]


# call nft describe "data_type" for more informations
DATA_TYPE_NAME_TO_INFO = {
    "verdict": (DATA_TYPE_VERDICT, 4, nft_data.nfta_data.verdict.verdict_code),
    "nf_proto": (DATA_TYPE_NFPROTO, 1, nlmsg_atoms.uint8),
    "bitmask": (DATA_TYPE_BITMASK, 4, nlmsg_atoms.uint32),
    "integer": (DATA_TYPE_INTEGER, 4, nlmsg_atoms.int32),
    "string": (DATA_TYPE_STRING, 0, nlmsg_atoms.asciiz),
    "lladdr": (DATA_TYPE_LLADDR, 0, nlmsg_atoms.lladdr),
    "ipv4_addr": (DATA_TYPE_IPADDR, 4, nlmsg_atoms.ip4addr),
    "ipv6_addr": (DATA_TYPE_IP6ADDR, 16, nlmsg_atoms.ip6addr),
    "ether_addr": (DATA_TYPE_ETHERADDR, 6, nlmsg_atoms.l2addr),
    "ether_type": (DATA_TYPE_ETHERADDR, 2, nlmsg_atoms.uint16),
    "inet_proto": (DATA_TYPE_INET_PROTOCOL, 1, nlmsg_atoms.uint8),
}
DATA_TYPE_ID_TO_NAME = {
    value[0]: key for key, value in DATA_TYPE_NAME_TO_INFO.items()
}
