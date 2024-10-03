import logging
from collections import namedtuple
from ctypes import c_uint16, c_uint32

from pyroute2.ethtool.common import (
    LINK_DUPLEX_NAMES,
    LINK_PORT_NAMES,
    LINK_TP_MDI_NAMES,
    LINK_TRANSCEIVER_NAMES,
    LinkModeBits_by_index,
    LMBTypeMode,
    LMBTypePort,
)
from pyroute2.ethtool.ioctl import WAKE_NAMES, IoctlEthtool
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.generic.ethtool import NlEthtool, ethtool_rings_msg

INT32MINUS_UINT32 = c_uint32(-1).value
INT16MINUS_UINT16 = c_uint16(-1).value

log = logging.getLogger(__name__)

EthtoolBitsetBit = namedtuple(
    'EthtoolBitsetBit', ('index', 'name', 'enable', 'set')
)


class UseIoctl(Exception):
    pass


class EthtoolCoalesce(object):
    @staticmethod
    def from_ioctl(ioctl_coalesce):
        return {name: int(value) for name, value in ioctl_coalesce.items()}

    @staticmethod
    def to_ioctl(ioctl_coalesce, coalesce):
        for name, value in coalesce.items():
            if ioctl_coalesce[name] != value:
                ioctl_coalesce[name] = value


class EthtoolFeature(object):
    __slots__ = ('set', 'index', 'name', 'enable', 'available')

    def __init__(self, set, index, name, enable, available):
        self.set = set
        self.index = index
        self.name = name
        self.enable = enable
        self.available = available


class EthtoolFeatures(namedtuple('EthtoolFeatures', ('features',))):
    @classmethod
    def from_ioctl(cls, features):
        return cls(
            {
                name: EthtoolFeature(set, index, name, enable, available)
                for name, enable, available, set, index in features
            }
        )

    @staticmethod
    def to_ioctl(ioctl_features, eth_features):
        for feature in eth_features.features.values():
            enable = ioctl_features[feature.name]
            if feature.enable == enable:
                continue
            ioctl_features[feature.name] = feature.enable


class EthtoolWakeOnLan(namedtuple('EthtoolWolMode', ('modes', 'sopass'))):
    @classmethod
    def from_netlink(cls, nl_wol):
        nl_wol = nl_wol[0].get_attr('ETHTOOL_A_WOL_MODES')
        wol_modes = {}
        for mode in nl_wol.get_attr('ETHTOOL_A_BITSET_BITS')['attrs']:
            mode = mode[1]
            index = mode.get_attr('ETHTOOL_A_BITSET_BIT_INDEX')
            name = mode.get_attr('ETHTOOL_A_BITSET_BIT_NAME')
            enable = mode.get_attr('ETHTOOL_A_BITSET_BIT_VALUE')
            wol_modes[name] = EthtoolBitsetBit(
                index, name, True if enable is True else False, set=None
            )
        return EthtoolWakeOnLan(modes=wol_modes, sopass=None)

    @classmethod
    def from_ioctl(cls, wol_mode):
        dict_wol_modes = {}
        for bit_index, name in WAKE_NAMES.items():
            if wol_mode.supported & bit_index:
                dict_wol_modes[name] = EthtoolBitsetBit(
                    bit_index,
                    name,
                    wol_mode.wolopts & bit_index != 0,
                    set=None,
                )
        return EthtoolWakeOnLan(modes=dict_wol_modes, sopass=None)


class EthtoolStringBit(
    namedtuple('EthtoolStringBit', ('set', 'index', 'name'))
):
    @classmethod
    def from_netlink(cls, nl_string_sets):
        nl_string_sets = nl_string_sets[0]
        ethtool_strings_set = set()
        for i in nl_string_sets.get_attr('ETHTOOL_A_STRSET_STRINGSETS')[
            'attrs'
        ]:
            i = i[1]

            set_id = i.get_attr('ETHTOOL_A_STRINGSET_ID')
            i = i.get_attr('ETHTOOL_A_STRINGSET_STRINGS')
            for i in i['attrs']:
                i = i[1]
                ethtool_strings_set.add(
                    cls(
                        set=set_id,
                        index=i.get_attr('ETHTOOL_A_STRING_INDEX'),
                        name=i.get_attr('ETHTOOL_A_STRING_VALUE'),
                    )
                )
        return ethtool_strings_set

    @classmethod
    def from_ioctl(cls, string_sets):
        return {
            cls(i // 32, i % 32, string)
            for i, string in enumerate(string_sets)
        }


class EthtoolLinkInfo(
    namedtuple(
        'EthtoolLinkInfo',
        ('port', 'phyaddr', 'tp_mdix', 'tp_mdix_ctrl', 'transceiver'),
    )
):
    def __new__(cls, port, phyaddr, tp_mdix, tp_mdix_ctrl, transceiver):
        port = LINK_PORT_NAMES.get(port, None)
        transceiver = LINK_TRANSCEIVER_NAMES.get(transceiver, None)

        tp_mdix = LINK_TP_MDI_NAMES.get(tp_mdix, None)
        tp_mdix_ctrl = LINK_TP_MDI_NAMES.get(tp_mdix_ctrl, None)
        return super(EthtoolLinkInfo, cls).__new__(
            cls, port, phyaddr, tp_mdix, tp_mdix_ctrl, transceiver
        )

    @classmethod
    def from_ioctl(cls, link_settings):
        return cls(
            port=link_settings.port,
            phyaddr=link_settings.phy_address,
            tp_mdix=link_settings.eth_tp_mdix,
            tp_mdix_ctrl=link_settings.eth_tp_mdix_ctrl,
            transceiver=link_settings.transceiver,
        )

    @classmethod
    def from_netlink(cls, nl_link_mode):
        nl_link_mode = nl_link_mode[0]
        return cls(
            port=nl_link_mode.get_attr('ETHTOOL_A_LINKINFO_PORT'),
            phyaddr=nl_link_mode.get_attr('ETHTOOL_A_LINKINFO_PHYADDR'),
            tp_mdix=nl_link_mode.get_attr('ETHTOOL_A_LINKINFO_TP_MDIX'),
            tp_mdix_ctrl=(
                nl_link_mode.get_attr('ETHTOOL_A_LINKINFO_TP_MDIX_CTR')
            ),
            transceiver=(
                nl_link_mode.get_attr('ETHTOOL_A_LINKINFO_TRANSCEIVER')
            ),
        )


class EthtoolLinkMode(
    namedtuple(
        'EthtoolLinkMode',
        ('speed', 'duplex', 'autoneg', 'supported_ports', 'supported_modes'),
    )
):
    def __new__(cls, speed, duplex, autoneg, supported_ports, supported_modes):
        if (
            speed == 0
            or speed == INT32MINUS_UINT32
            or speed == INT16MINUS_UINT16
        ):
            speed = None
        duplex = LINK_DUPLEX_NAMES.get(duplex, None)

        return super(EthtoolLinkMode, cls).__new__(
            cls, speed, duplex, bool(autoneg), supported_ports, supported_modes
        )

    @classmethod
    def from_ioctl(cls, link_settings):
        (map_supported, map_advertising, map_lp_advertising) = (
            IoctlEthtool.get_link_mode_masks(link_settings)
        )
        bits_supported = IoctlEthtool.get_link_mode_bits(map_supported)
        supported_ports = []
        supported_modes = []

        for bit in bits_supported:
            if bit.type == LMBTypePort:
                supported_ports.append(bit.name)
            elif bit.type == LMBTypeMode:
                supported_modes.append(bit.name)
        return cls(
            speed=link_settings.speed,
            duplex=link_settings.duplex,
            autoneg=link_settings.autoneg,
            supported_ports=supported_ports,
            supported_modes=supported_modes,
        )

    @classmethod
    def from_netlink(cls, nl_link_mode):
        nl_link_mode = nl_link_mode[0]
        supported_ports = []
        supported_modes = []

        for bitset_bit in nl_link_mode.get_attr(
            'ETHTOOL_A_LINKMODES_OURS'
        ).get_attr('ETHTOOL_A_BITSET_BITS')['attrs']:
            bitset_bit = bitset_bit[1]
            bit_index = bitset_bit.get_attr('ETHTOOL_A_BITSET_BIT_INDEX')
            bit_name = bitset_bit.get_attr('ETHTOOL_A_BITSET_BIT_NAME')
            bit_value = bitset_bit.get_attr('ETHTOOL_A_BITSET_BIT_VALUE')
            if bit_value is not True:
                continue

            bit = LinkModeBits_by_index[bit_index]
            if bit.name != bit_name:
                log.error(
                    "Bit name is not the same as the target: %s <> %s",
                    bit.name,
                    bit_name,
                )
                continue

            if bit.type == LMBTypePort:
                supported_ports.append(bit.name)
            elif bit.type == LMBTypeMode:
                supported_modes.append(bit.name)

        return cls(
            speed=nl_link_mode.get_attr("ETHTOOL_A_LINKMODES_SPEED"),
            duplex=nl_link_mode.get_attr("ETHTOOL_A_LINKMODES_DUPLEX"),
            autoneg=nl_link_mode.get_attr("ETHTOOL_A_LINKMODES_AUTONEG"),
            supported_ports=supported_ports,
            supported_modes=supported_modes,
        )


class EthtoolRings(
    namedtuple(
        'EthtoolRings',
        (
            "rx_max",
            "rx_mini_max",
            "rx_jumbo_max",
            "tx_max",
            "rx",
            "rx_mini",
            "rx_jumbo",
            "tx",
            "rx_buf_len",
            "tcp_data_split",
            "cqe_size",
            "tx_push",
            "rx_push",
            "tx_push_buf_len",
            "tx_push_buf_len_max",
        ),
    )
):
    nl_attributs_dict = {
        "rx_max": 'ETHTOOL_A_RINGS_RX_MAX',
        "rx_mini_max": 'ETHTOOL_A_RINGS_RX_MINI_MAX',
        "rx_jumbo_max": 'ETHTOOL_A_RINGS_RX_JUMBO_MAX',
        "tx_max": 'ETHTOOL_A_RINGS_TX_MAX',
        "rx": 'ETHTOOL_A_RINGS_RX',
        "rx_mini": 'ETHTOOL_A_RINGS_RX_MINI',
        "rx_jumbo": 'ETHTOOL_A_RINGS_RX_JUMBO',
        "tx": 'ETHTOOL_A_RINGS_TX',
        "rx_buf_len": 'ETHTOOL_A_RINGS_RX_BUF_LEN',
        "tcp_data_split": 'ETHTOOL_A_RINGS_TCP_DATA_SPLIT',
        "cqe_size": 'ETHTOOL_A_RINGS_CQE_SIZE',
        "tx_push": 'ETHTOOL_A_RINGS_TX_PUSH',
        "rx_push": 'ETHTOOL_A_RINGS_RX_PUSH',
        "tx_push_buf_len": 'ETHTOOL_A_RINGS_TX_PUSH_BUF_LEN',
        "tx_push_buf_len_max": 'ETHTOOL_A_RINGS_TX_PUSH_BUF_LEN_MAX',
    }

    def __new__(
        cls,
        rx_max=None,
        rx_mini_max=None,
        rx_jumbo_max=None,
        tx_max=None,
        rx=None,
        rx_mini=None,
        rx_jumbo=None,
        tx=None,
        rx_buf_len=None,
        tcp_data_split=None,
        cqe_size=None,
        tx_push=None,
        rx_push=None,
        tx_push_buf_len=None,
        tx_push_buf_len_max=None,
    ):
        return super(EthtoolRings, cls).__new__(
            cls,
            rx_max,
            rx_mini_max,
            rx_jumbo_max,
            tx_max,
            rx,
            rx_mini,
            rx_jumbo,
            tx,
            rx_buf_len,
            tcp_data_split,
            cqe_size,
            tx_push,
            rx_push,
            tx_push_buf_len,
            tx_push_buf_len_max,
        )

    @classmethod
    def from_netlink(cls, nl_rings):
        nl_rings = nl_rings[0]
        return cls(
            **{
                cls_attr: nl_rings.get_attr(netlink_attr)
                for cls_attr, netlink_attr in cls.nl_attributs_dict.items()
            }
        )

    def to_netlink(self):
        nl_rings_attrs = ethtool_rings_msg()
        for cls_attr, netlink_attr in self.nl_attributs_dict.items():
            attr = getattr(self, cls_attr)
            if attr is not None:
                nl_rings_attrs["attrs"].append((netlink_attr, attr))
        return nl_rings_attrs

    @classmethod
    def from_ioctl(cls, ioctl_rings):
        ioctl_rings = dict(ioctl_rings)
        ioctl_rings.pop("cmd")
        return cls(**ioctl_rings)


class Ethtool:
    def __init__(self):
        self._with_ioctl = IoctlEthtool()
        self._with_nl = NlEthtool()
        self._with_nl.module_err_level = 'debug'
        self._is_nl_working = self._with_nl.is_nlethtool_in_kernel()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _nl_exec(self, f, with_netlink, *args, **kwargs):
        if with_netlink is None:
            with_netlink = self._is_nl_working
        if with_netlink is False:
            raise UseIoctl()

        try:
            return f(*args, **kwargs)
        except NetlinkError:
            raise UseIoctl()

    def get_link_mode(self, ifname, with_netlink=None):
        try:
            link_mode = self._nl_exec(
                self._with_nl.get_linkmode, with_netlink, ifname
            )
            link_mode = EthtoolLinkMode.from_netlink(link_mode)
        except UseIoctl:
            self._with_ioctl.change_ifname(ifname)
            link_settings = self._with_ioctl.get_link_settings()
            link_mode = EthtoolLinkMode.from_ioctl(link_settings)
        return link_mode

    def get_link_info(self, ifname, with_netlink=None):
        try:
            link_info = self._nl_exec(
                self._with_nl.get_linkinfo, with_netlink, ifname
            )
            link_info = EthtoolLinkInfo.from_netlink(link_info)
        except UseIoctl:
            self._with_ioctl.change_ifname(ifname)
            link_settings = self._with_ioctl.get_link_settings()
            link_info = EthtoolLinkInfo.from_ioctl(link_settings)
        return link_info

    def get_strings_set(self, ifname, with_netlink=None):
        try:
            stringsets = self._nl_exec(
                self._with_nl.get_stringset, with_netlink, ifname
            )
            return EthtoolStringBit.from_netlink(stringsets)
        except UseIoctl:
            self._with_ioctl.change_ifname(ifname)
            stringsets = self._with_ioctl.get_stringset()
            return EthtoolStringBit.from_ioctl(stringsets)

    def get_wol(self, ifname):
        nl_working = self._is_nl_working
        if nl_working is True:
            try:
                wol = self._with_nl.get_wol(ifname)
                return EthtoolWakeOnLan.from_netlink(wol)
            except NetlinkError:
                nl_working = False

        if nl_working is False:
            self._with_ioctl.change_ifname(ifname)
            wol_mode = self._with_ioctl.get_wol()
            return EthtoolWakeOnLan.from_ioctl(wol_mode)

    def get_rings(self, ifname, with_netlink=None):
        try:
            rings = self._nl_exec(
                self._with_nl.get_rings, with_netlink, ifname
            )
            rings = EthtoolRings.from_netlink(rings)
        except UseIoctl:
            self._with_ioctl.change_ifname(ifname)
            rings_info = self._with_ioctl.get_rings()
            rings = EthtoolRings.from_ioctl(rings_info)
        return rings

    def set_rings(self, ifname, with_netlink=None, **kwargs):
        try:
            rings = EthtoolRings(**kwargs).to_netlink()
            self._nl_exec(self._with_nl.set_rings, with_netlink, rings, ifname)
        except UseIoctl:
            self._with_ioctl.change_ifname(ifname)
            ioctl_rings = self._with_ioctl.get_rings()
            for name, value in kwargs.items():
                if name in ioctl_rings.keys() and ioctl_rings[name] != value:
                    ioctl_rings[name] = value

            self._with_ioctl.set_rings(ioctl_rings)

    def get_features(self, ifname):
        self._with_ioctl.change_ifname(ifname)
        return EthtoolFeatures.from_ioctl(self._with_ioctl.get_features())

    def set_features(self, ifname, features):
        self._with_ioctl.change_ifname(ifname)
        ioctl_features = self._with_ioctl.get_features()
        EthtoolFeatures.to_ioctl(ioctl_features, features)
        self._with_ioctl.set_features(ioctl_features)

    def get_coalesce(self, ifname):
        self._with_ioctl.change_ifname(ifname)
        return EthtoolCoalesce.from_ioctl(self._with_ioctl.get_coalesce())

    def set_coalesce(self, ifname, coalesce):
        self._with_ioctl.change_ifname(ifname)
        ioctl_coalesce = self._with_ioctl.get_coalesce()
        EthtoolCoalesce.to_ioctl(ioctl_coalesce, coalesce)
        self._with_ioctl.set_coalesce(ioctl_coalesce)

    def close(self):
        self._with_ioctl.close()
        self._with_nl.close()
