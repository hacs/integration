from pyroute2.netlink import (
    NLA_F_NESTED,
    NLM_F_ACK,
    NLM_F_REQUEST,
    genlmsg,
    nla,
)
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.generic import GenericNetlinkSocket

ETHTOOL_GENL_NAME = "ethtool"
ETHTOOL_GENL_VERSION = 1

ETHTOOL_MSG_USER_NONE = 0
ETHTOOL_MSG_STRSET_GET = 1
ETHTOOL_MSG_LINKINFO_GET = 2
ETHTOOL_MSG_LINKINFO_SET = 3
ETHTOOL_MSG_LINKMODES_GET = 4
ETHTOOL_MSG_LINKMODES_SET = 5
ETHTOOL_MSG_LINKSTATE_GET = 6
ETHTOOL_MSG_DEBUG_GET = 7
ETHTOOL_MSG_DEBUG_SET = 8
ETHTOOL_MSG_WOL_GET = 9
ETHTOOL_MSG_WOL_SET = 10
ETHTOOL_MSG_FEATURES_GET = 11
ETHTOOL_MSG_FEATURES_SET = 12
ETHTOOL_MSG_PRIVFLAGS_GET = 13
ETHTOOL_MSG_PRIVFLAGS_SET = 14
ETHTOOL_MSG_RINGS_GET = 15
ETHTOOL_MSG_RINGS_SET = 16


class ethtoolheader(nla):
    nla_flags = NLA_F_NESTED
    nla_map = (
        ('ETHTOOL_A_HEADER_UNSPEC', 'none'),
        ('ETHTOOL_A_HEADER_DEV_INDEX', 'uint32'),
        ('ETHTOOL_A_HEADER_DEV_NAME', 'asciiz'),
        ('ETHTOOL_A_HEADER_FLAGS', 'uint32'),
    )


class ethtoolbitset(nla):
    nla_flags = NLA_F_NESTED
    nla_map = (
        ("ETHTOOL_A_BITSET_UNSPEC", 'none'),
        ("ETHTOOL_A_BITSET_NOMASK", "flag"),
        ("ETHTOOL_A_BITSET_SIZE", 'uint32'),
        ("ETHTOOL_A_BITSET_BITS", 'bitset_bits'),
        ("ETHTOOL_A_BITSET_VALUE", 'hex'),
        ("ETHTOOL_A_BITSET_MASK", 'hex'),
    )

    class bitset_bits(nla):
        nla_flags = NLA_F_NESTED
        nla_map = (
            ('ETHTOOL_A_BITSET_BIT_UNSPEC', 'none'),
            ('ETHTOOL_A_BITSET_BITS_BIT', 'bitset_bits_bit'),
        )

        class bitset_bits_bit(nla):
            nla_flags = NLA_F_NESTED
            nla_map = (
                ('ETHTOOL_A_BITSET_BIT_UNSPEC', 'none'),
                ('ETHTOOL_A_BITSET_BIT_INDEX', 'uint32'),
                ('ETHTOOL_A_BITSET_BIT_NAME', 'asciiz'),
                ('ETHTOOL_A_BITSET_BIT_VALUE', 'flag'),
            )


class ethtool_strset_msg(genlmsg):
    nla_map = (
        ('ETHTOOL_A_STRSET_UNSPEC', 'none'),
        ('ETHTOOL_A_STRSET_HEADER', 'ethtoolheader'),
        ('ETHTOOL_A_STRSET_STRINGSETS', 'strings_sets'),
        ('ETHTOOL_A_STRSET_COUNTS_ONLY', 'flag'),
    )

    ethtoolheader = ethtoolheader

    class strings_sets(nla):
        nla_flags = NLA_F_NESTED
        nla_map = (
            ('ETHTOOL_A_STRINGSETS_UNSPEC', 'none'),
            ('ETHTOOL_A_STRINGSETS_STRINGSET', 'string_set'),
        )

        class string_set(nla):
            nla_flags = NLA_F_NESTED
            nla_map = (
                ('ETHTOOL_A_STRINGSET_UNSPEC', 'none'),
                ('ETHTOOL_A_STRINGSET_ID', 'uint32'),
                ('ETHTOOL_A_STRINGSET_COUNT', 'uint32'),
                ('ETHTOOL_A_STRINGSET_STRINGS', 'stringset_strings'),
            )

            class stringset_strings(nla):
                nla_flags = NLA_F_NESTED
                nla_map = (
                    ('ETHTOOL_A_STRINGS_UNSPEC', 'none'),
                    ('ETHTOOL_A_STRINGS_STRING', 'strings_string'),
                )

                class strings_string(nla):
                    nla_flags = NLA_F_NESTED
                    nla_map = (
                        ('ETHTOOL_A_STRING_UNSPEC', 'none'),
                        ('ETHTOOL_A_STRING_INDEX', 'uint32'),
                        ('ETHTOOL_A_STRING_VALUE', 'asciiz'),
                    )


class ethtool_linkinfo_msg(genlmsg):
    nla_map = (
        ('ETHTOOL_A_LINKINFO_UNSPEC', 'none'),
        ('ETHTOOL_A_LINKINFO_HEADER', 'ethtoolheader'),
        ('ETHTOOL_A_LINKINFO_PORT', 'uint8'),
        ('ETHTOOL_A_LINKINFO_PHYADDR', 'uint8'),
        ('ETHTOOL_A_LINKINFO_TP_MDIX', 'uint8'),
        ('ETHTOOL_A_LINKINFO_TP_MDIX_CTR', 'uint8'),
        ('ETHTOOL_A_LINKINFO_TRANSCEIVER', 'uint8'),
    )

    ethtoolheader = ethtoolheader


class ethtool_linkmode_msg(genlmsg):
    nla_map = (
        ('ETHTOOL_A_LINKMODES_UNSPEC', 'none'),
        ('ETHTOOL_A_LINKMODES_HEADER', 'ethtoolheader'),
        ('ETHTOOL_A_LINKMODES_AUTONEG', 'uint8'),
        ('ETHTOOL_A_LINKMODES_OURS', 'ethtoolbitset'),
        ('ETHTOOL_A_LINKMODES_PEER', 'ethtoolbitset'),
        ('ETHTOOL_A_LINKMODES_SPEED', 'uint32'),
        ('ETHTOOL_A_LINKMODES_DUPLEX', 'uint8'),
    )

    ethtoolheader = ethtoolheader
    ethtoolbitset = ethtoolbitset


class ethtool_linkstate_msg(genlmsg):
    nla_map = (
        ('ETHTOOL_A_LINKSTATE_UNSPEC', 'none'),
        ('ETHTOOL_A_LINKSTATE_HEADER', 'ethtoolheader'),
        ('ETHTOOL_A_LINKSTATE_LINK', 'uint8'),
    )

    ethtoolheader = ethtoolheader


class ethtool_wol_msg(genlmsg):
    nla_map = (
        ('ETHTOOL_A_WOL_UNSPE', 'none'),
        ('ETHTOOL_A_WOL_HEADER', 'ethtoolheader'),
        ('ETHTOOL_A_WOL_MODES', 'ethtoolbitset'),
        ('ETHTOOL_A_WOL_SOPASS', 'hex'),
    )

    ethtoolheader = ethtoolheader
    ethtoolbitset = ethtoolbitset


class ethtool_rings_msg(genlmsg):
    nla_map = (
        ('ETHTOOL_A_RINGS_UNSPEC', 'none'),
        ('ETHTOOL_A_RINGS_HEADER', 'ethtoolheader'),
        ('ETHTOOL_A_RINGS_RX_MAX', 'uint32'),
        ('ETHTOOL_A_RINGS_RX_MINI_MAX', 'uint32'),
        ('ETHTOOL_A_RINGS_RX_JUMBO_MAX', 'uint32'),
        ('ETHTOOL_A_RINGS_TX_MAX', 'uint32'),
        ('ETHTOOL_A_RINGS_RX', 'uint32'),
        ('ETHTOOL_A_RINGS_RX_MINI', 'uint32'),
        ('ETHTOOL_A_RINGS_RX_JUMBO', 'uint32'),
        ('ETHTOOL_A_RINGS_TX', 'uint32'),
        ('ETHTOOL_A_RINGS_RX_BUF_LEN', 'uint32'),
        ('ETHTOOL_A_RINGS_TCP_DATA_SPLIT', 'uint8'),
        ('ETHTOOL_A_RINGS_CQE_SIZE', 'uint32'),
        ('ETHTOOL_A_RINGS_TX_PUSH', 'uint8'),
        ('ETHTOOL_A_RINGS_RX_PUSH', 'uint8'),
        ('ETHTOOL_A_RINGS_TX_PUSH_BUF_LEN', 'uint32'),
        ('ETHTOOL_A_RINGS_TX_PUSH_BUF_LEN_MAX', 'uint32'),
    )

    ethtoolheader = ethtoolheader


class NlEthtool(GenericNetlinkSocket):
    def _do_request(self, msg, msg_flags=NLM_F_REQUEST):
        return self.nlm_request(msg, msg_type=self.prid, msg_flags=msg_flags)

    def is_nlethtool_in_kernel(self):
        try:
            self.bind(ETHTOOL_GENL_NAME, ethtool_linkinfo_msg)
        except NetlinkError:
            return False
        return True

    def _get_dev_header(self, ifname=None, ifindex=None):
        if ifindex is not None:
            return {'attrs': [['ETHTOOL_A_HEADER_DEV_INDEX', ifindex]]}
        elif ifname is not None:
            return {'attrs': [['ETHTOOL_A_HEADER_DEV_NAME', ifname]]}
        else:
            raise ValueError("Need ifname or ifindex")

    def get_linkinfo(self, ifname=None, ifindex=None):
        msg = ethtool_linkinfo_msg()
        msg["cmd"] = ETHTOOL_MSG_LINKINFO_GET
        msg['version'] = ETHTOOL_GENL_VERSION
        msg["attrs"].append(
            (
                'ETHTOOL_A_LINKINFO_HEADER',
                self._get_dev_header(ifname, ifindex),
            )
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_linkinfo_msg)
        return self._do_request(msg)

    def get_linkmode(self, ifname=None, ifindex=None):
        msg = ethtool_linkmode_msg()
        msg["cmd"] = ETHTOOL_MSG_LINKMODES_GET
        msg['version'] = ETHTOOL_GENL_VERSION
        msg["attrs"].append(
            (
                'ETHTOOL_A_LINKMODES_HEADER',
                self._get_dev_header(ifname, ifindex),
            )
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_linkmode_msg)
        return self._do_request(msg)

    def get_stringset(self, ifname=None, ifindex=None):
        msg = ethtool_strset_msg()
        msg["cmd"] = ETHTOOL_MSG_STRSET_GET
        msg['version'] = ETHTOOL_GENL_VERSION
        msg["attrs"].append(
            ('ETHTOOL_A_STRSET_HEADER', self._get_dev_header(ifname, ifindex))
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_strset_msg)
        return self._do_request(msg)

    def get_linkstate(self, ifname=None, ifindex=None):
        msg = ethtool_linkstate_msg()
        msg["cmd"] = ETHTOOL_MSG_LINKSTATE_GET
        msg['version'] = ETHTOOL_GENL_VERSION
        msg["attrs"].append(
            (
                'ETHTOOL_A_LINKSTATE_HEADER',
                self._get_dev_header(ifname, ifindex),
            )
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_linkstate_msg)
        return self._do_request(msg)

    def get_wol(self, ifname=None, ifindex=None):
        msg = ethtool_wol_msg()
        msg["cmd"] = ETHTOOL_MSG_WOL_GET
        msg['version'] = ETHTOOL_GENL_VERSION
        msg["attrs"].append(
            ('ETHTOOL_A_WOL_HEADER', self._get_dev_header(ifname, ifindex))
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_wol_msg)
        return self._do_request(msg)

    def get_rings(self, ifname=None, ifindex=None):
        msg = ethtool_rings_msg()
        msg["cmd"] = ETHTOOL_MSG_RINGS_GET
        msg["version"] = ETHTOOL_GENL_VERSION
        msg["attrs"].append(
            ('ETHTOOL_A_RINGS_HEADER', self._get_dev_header(ifname, ifindex))
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_rings_msg)
        return self._do_request(msg)

    def set_rings(self, rings, ifname=None, ifindex=None):
        rings["cmd"] = ETHTOOL_MSG_RINGS_SET
        rings["version"] = ETHTOOL_GENL_VERSION
        rings["attrs"].append(
            ('ETHTOOL_A_RINGS_HEADER', self._get_dev_header(ifname, ifindex))
        )

        self.bind(ETHTOOL_GENL_NAME, ethtool_rings_msg)
        return self._do_request(rings, msg_flags=NLM_F_REQUEST | NLM_F_ACK)
