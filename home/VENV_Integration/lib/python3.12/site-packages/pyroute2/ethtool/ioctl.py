import ctypes
import errno
import fcntl
import socket

from pyroute2.ethtool.common import LinkModeBits

# ethtool/ethtool-copy.h
IFNAMSIZ = 16
SIOCETHTOOL = 0x8946
ETHTOOL_GSET = 0x1
ETHTOOL_GCOALESCE = 0xE
ETHTOOL_SCOALESCE = 0xF
ETHTOOL_GSSET_INFO = 0x37
ETHTOOL_GWOL = 0x00000005

ETHTOOL_GFLAGS = 0x00000025
ETHTOOL_GFEATURES = 0x0000003A
ETHTOOL_SFEATURES = 0x0000003B
ETHTOOL_GLINKSETTINGS = 0x0000004C

ETHTOOL_GSTRINGS = 0x0000001B
ETHTOOL_GSTATS = 0x0000001D
ETH_GSTRING_LEN = 32

ETHTOOL_GRINGPARAM = 0x00000010
ETHTOOL_SRINGPARAM = 0x00000011

ETHTOOL_GRXCSUM = 0x00000014
ETHTOOL_SRXCSUM = 0x00000015
ETHTOOL_GTXCSUM = 0x00000016
ETHTOOL_STXCSUM = 0x00000017
ETHTOOL_GSG = 0x00000018
ETHTOOL_SSG = 0x00000019
ETHTOOL_GTSO = 0x0000001E
ETHTOOL_STSO = 0x0000001F
ETHTOOL_GUFO = 0x00000021
ETHTOOL_SUFO = 0x00000022
ETHTOOL_GGSO = 0x00000023
ETHTOOL_SGSO = 0x00000024
ETHTOOL_GGRO = 0x0000002B
ETHTOOL_SGRO = 0x0000002C

SOPASS_MAX = 6

ETH_SS_STATS = 1
ETH_SS_FEATURES = 4

ETH_FLAG_RXCSUM = 1 << 0
ETH_FLAG_TXCSUM = 1 << 1
ETH_FLAG_SG = 1 << 2
ETH_FLAG_TSO = 1 << 3
ETH_FLAG_UFO = 1 << 4
ETH_FLAG_GSO = 1 << 5
ETH_FLAG_GRO = 1 << 6
ETH_FLAG_TXVLAN = 1 << 7
ETH_FLAG_RXVLAN = 1 << 8
ETH_FLAG_LRO = 1 << 15
ETH_FLAG_NTUPLE = 1 << 27
ETH_FLAG_RXHASH = 1 << 28
ETH_FLAG_EXT_MASK = (
    ETH_FLAG_LRO
    | ETH_FLAG_RXVLAN
    | ETH_FLAG_TXVLAN
    | ETH_FLAG_NTUPLE
    | ETH_FLAG_RXHASH
)

SCHAR_MAX = 127
ETHTOOL_LINK_MODE_MASK_MAX_KERNEL_NU32 = SCHAR_MAX


# Wake-On-Lan options.
WAKE_PHY = 1 << 0
WAKE_UCAST = 1 << 1
WAKE_MCAST = 1 << 2
WAKE_BCAST = 1 << 3
WAKE_ARP = 1 << 4
WAKE_MAGIC = 1 << 5
WAKE_MAGICSECURE = 1 << 6  # only meaningful if WAKE_MAGIC
WAKE_FILTER = 1 << 7
WAKE_NAMES = {
    WAKE_PHY: "phy",
    WAKE_UCAST: "ucast",
    WAKE_MCAST: "mcast",
    WAKE_BCAST: "bcast",
    WAKE_ARP: "arp",
    WAKE_MAGIC: "magic",
    WAKE_MAGICSECURE: "magic_secure",
    WAKE_FILTER: "filter",
}


class EthtoolError(Exception):
    pass


class NotSupportedError(EthtoolError):
    pass


class NoSuchDevice(EthtoolError):
    pass


class DictStruct(ctypes.Structure):
    def __init__(self, *args, **kwargs):
        super(DictStruct, self).__init__(*args, **kwargs)
        self._fields_as_dict = {
            name: [
                lambda k: getattr(self, k),
                lambda k, v: setattr(self, k, v),
            ]
            for name, ct in self._fields_
        }

    def __getitem__(self, key):
        return self._fields_as_dict[key][0](key)

    def __setitem__(self, key, value):
        return self._fields_as_dict[key][1](key, value)

    def __iter__(self):
        return iter(self._fields_as_dict)

    def items(self):
        for k, f in self._fields_as_dict.items():
            getter, _ = f
            yield k, getter(k)

    def keys(self):
        return self._fields_as_dict.keys()

    def __contains__(self, key):
        return key in self._fields_as_dict


class EthtoolWolInfo(DictStruct):
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("supported", ctypes.c_uint32),
        ("wolopts", ctypes.c_uint32),
        ("sopass", ctypes.c_uint8 * SOPASS_MAX),
    ]


class EthtoolCmd(DictStruct):
    _pack_ = 1
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("supported", ctypes.c_uint32),
        ("advertising", ctypes.c_uint32),
        ("speed", ctypes.c_uint16),
        ("duplex", ctypes.c_uint8),
        ("port", ctypes.c_uint8),
        ("phy_address", ctypes.c_uint8),
        ("transceiver", ctypes.c_uint8),
        ("autoneg", ctypes.c_uint8),
        ("mdio_support", ctypes.c_uint8),
        ("maxtxpkt", ctypes.c_uint32),
        ("maxrxpkt", ctypes.c_uint32),
        ("speed_hi", ctypes.c_uint16),
        ("eth_tp_mdix", ctypes.c_uint8),
        ("reserved2", ctypes.c_uint8),
        ("lp_advertising", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 2),
    ]


class IoctlEthtoolLinkSettings(DictStruct):
    _pack_ = 1
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("speed", ctypes.c_uint32),
        ("duplex", ctypes.c_uint8),
        ("port", ctypes.c_uint8),
        ("phy_address", ctypes.c_uint8),
        ("autoneg", ctypes.c_uint8),
        ("mdio_support", ctypes.c_uint8),
        ("eth_tp_mdix", ctypes.c_uint8),
        ("eth_tp_mdix_ctrl", ctypes.c_uint8),
        ("link_mode_masks_nwords", ctypes.c_int8),
        ("transceiver", ctypes.c_uint8),
        ("reserved1", ctypes.c_uint8 * 3),
        ("reserved", ctypes.c_uint32 * 7),
        (
            "link_mode_data",
            ctypes.c_uint32 * (3 * ETHTOOL_LINK_MODE_MASK_MAX_KERNEL_NU32),
        ),
    ]


class EthtoolCoalesce(DictStruct):
    _pack_ = 1
    _fields_ = [
        # ETHTOOL_{G,S}COALESCE
        ("cmd", ctypes.c_uint32),
        # How many usecs to delay an RX interrupt after
        # a packet arrives.  If 0, only rx_max_coalesced_frames
        # is used.
        ("rx_coalesce_usecs", ctypes.c_uint32),
        # How many packets to delay an RX interrupt after
        # a packet arrives.  If 0, only rx_coalesce_usecs is
        # used.  It is illegal to set both usecs and max frames
        # to zero as this would cause RX interrupts to never be
        # generated.
        ("rx_max_coalesced_frames", ctypes.c_uint32),
        # Same as above two parameters, except that these values
        # apply while an IRQ is being serviced by the host.  Not
        # all cards support this feature and the values are ignored
        # in that case.
        ("rx_coalesce_usecs_irq", ctypes.c_uint32),
        ("rx_max_coalesced_frames_irq", ctypes.c_uint32),
        # How many usecs to delay a TX interrupt after
        # a packet is sent.  If 0, only tx_max_coalesced_frames
        # is used.
        ("tx_coalesce_usecs", ctypes.c_uint32),
        # How many packets to delay a TX interrupt after
        # a packet is sent.  If 0, only tx_coalesce_usecs is
        # used.  It is illegal to set both usecs and max frames
        # to zero as this would cause TX interrupts to never be
        # generated.
        ("tx_max_coalesced_frames", ctypes.c_uint32),
        # Same as above two parameters, except that these values
        # apply while an IRQ is being serviced by the host.  Not
        # all cards support this feature and the values are ignored
        # in that case.
        ("tx_coalesce_usecs_irq", ctypes.c_uint32),
        ("tx_max_coalesced_frames_irq", ctypes.c_uint32),
        # How many usecs to delay in-memory statistics
        # block updates.  Some drivers do not have an in-memory
        # statistic block, and in such cases this value is ignored.
        # This value must not be zero.
        ("stats_block_coalesce_usecs", ctypes.c_uint32),
        # Adaptive RX/TX coalescing is an algorithm implemented by
        # some drivers to improve latency under low packet rates and
        # improve throughput under high packet rates.  Some drivers
        # only implement one of RX or TX adaptive coalescing.  Anything
        # not implemented by the driver causes these values to be
        # silently ignored.
        ("use_adaptive_rx_coalesce", ctypes.c_uint32),
        ("use_adaptive_tx_coalesce", ctypes.c_uint32),
        # When the packet rate (measured in packets per second)
        # is below pkt_rate_low, the {rx,tx}_*_low parameters are
        # used.
        ("pkt_rate_low", ctypes.c_uint32),
        ("rx_coalesce_usecs_low", ctypes.c_uint32),
        ("rx_max_coalesced_frames_low", ctypes.c_uint32),
        ("tx_coalesce_usecs_low", ctypes.c_uint32),
        ("tx_max_coalesced_frames_low", ctypes.c_uint32),
        # When the packet rate is below pkt_rate_high but above
        # pkt_rate_low (both measured in packets per second) the
        # normal {rx,tx}_* coalescing parameters are used.
        # When the packet rate is (measured in packets per second)
        # is above pkt_rate_high, the {rx,tx}_*_high parameters are
        # used.
        ("pkt_rate_high", ctypes.c_uint32),
        ("rx_coalesce_usecs_high", ctypes.c_uint32),
        ("rx_max_coalesced_frames_high", ctypes.c_uint32),
        ("tx_coalesce_usecs_high", ctypes.c_uint32),
        ("tx_max_coalesced_frames_high", ctypes.c_uint32),
        # How often to do adaptive coalescing packet rate sampling,
        # measured in seconds.  Must not be zero.
        ("rate_sample_interval", ctypes.c_uint32),
    ]


class EthtoolValue(ctypes.Structure):
    _fields_ = [("cmd", ctypes.c_uint32), ("data", ctypes.c_uint32)]


class EthtoolSsetInfo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("sset_mask", ctypes.c_uint64),
        ("data", ctypes.c_uint32),
    ]


def generate_EthtoolGstrings(gstrings_length):
    class EthtoolGstrings(ctypes.Structure):
        _fields_ = [
            ("cmd", ctypes.c_uint32),
            ("string_set", ctypes.c_uint32),
            ("len", ctypes.c_uint32),
            ("strings", ctypes.c_ubyte * ETH_GSTRING_LEN * gstrings_length),
        ]

    return EthtoolGstrings


class EthtoolGetFeaturesBlock(ctypes.Structure):
    _fields_ = [
        ("available", ctypes.c_uint32),
        ("requested", ctypes.c_uint32),
        ("active", ctypes.c_uint32),
        ("never_changed", ctypes.c_uint32),
    ]


class EthtoolSetFeaturesBlock(ctypes.Structure):
    _fields_ = [("changed", ctypes.c_uint32), ("active", ctypes.c_uint32)]


def generate_EthtoolGStats(stats_length):
    class EthtoolGStats(ctypes.Structure):
        _fields_ = [
            ("cmd", ctypes.c_uint32),
            ("size", ctypes.c_uint32),
            ("data", ctypes.c_uint64 * stats_length),
        ]

    return EthtoolGStats


def div_round_up(n, d):
    return int(((n) + (d) - 1) / (d))


def feature_bits_to_blocks(n_bits):
    return div_round_up(n_bits, 32)


class EthtoolGfeatures(ctypes.Structure):
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("size", ctypes.c_uint32),
        ("features", EthtoolGetFeaturesBlock * feature_bits_to_blocks(256)),
    ]


class EthtoolSfeatures(ctypes.Structure):
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("size", ctypes.c_uint32),
        ("features", EthtoolSetFeaturesBlock * feature_bits_to_blocks(256)),
    ]


class FeatureState(ctypes.Structure):
    _fields_ = [("off_flags", ctypes.c_uint32), ("features", EthtoolGfeatures)]


class EthtoolRingParam(DictStruct):
    _pack_ = 1
    _fields_ = [
        ("cmd", ctypes.c_uint32),
        ("rx_max", ctypes.c_uint32),
        ("rx_mini_max", ctypes.c_uint32),
        ("rx_jumbo_max", ctypes.c_uint32),
        ("tx_max", ctypes.c_uint32),
        ("rx", ctypes.c_uint32),
        ("rx_mini", ctypes.c_uint32),
        ("rx_jumbo", ctypes.c_uint32),
        ("tx", ctypes.c_uint32),
    ]


class IfReqData(ctypes.Union):
    dummy = generate_EthtoolGstrings(0)
    _fields_ = [
        ("ifr_data", ctypes.POINTER(EthtoolCmd)),
        ("coalesce", ctypes.POINTER(EthtoolCoalesce)),
        ("value", ctypes.POINTER(EthtoolValue)),
        ("sset_info", ctypes.POINTER(EthtoolSsetInfo)),
        ("gstrings", ctypes.POINTER(None)),
        ("gstats", ctypes.POINTER(None)),
        ("gfeatures", ctypes.POINTER(EthtoolGfeatures)),
        ("sfeatures", ctypes.POINTER(EthtoolSfeatures)),
        ("glinksettings", ctypes.POINTER(IoctlEthtoolLinkSettings)),
        ("wolinfo", ctypes.POINTER(EthtoolWolInfo)),
        ("rings", ctypes.POINTER(EthtoolRingParam)),
    ]


class IfReq(ctypes.Structure):
    _pack_ = 1
    _anonymous_ = ("u",)
    _fields_ = [("ifr_name", ctypes.c_uint8 * IFNAMSIZ), ("u", IfReqData)]


class IfReqSsetInfo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("ifr_name", ctypes.c_uint8 * IFNAMSIZ),
        ("info", ctypes.POINTER(EthtoolSsetInfo)),
    ]


class EthtoolFeaturesList:
    def __init__(self, cmd, stringsset):
        self._offsets = {}
        self._cmd = cmd
        self._cmd_set = EthtoolSfeatures(cmd=ETHTOOL_SFEATURES, size=cmd.size)
        self._gfeatures = cmd.features
        self._sfeatures = self._cmd_set.features

        feature_i = 0
        for i, name in enumerate(stringsset):
            feature_i = i // 32
            flag_bit = 1 << (i % 32)
            self._offsets[name] = (feature_i, flag_bit)

        while feature_i:
            feature_i -= 1
            self._sfeatures[feature_i].active = self._gfeatures[
                feature_i
            ].active
            self._sfeatures[feature_i].changed = 0

    def is_available(self, name):
        feature_i, flag_bit = self._offsets[name]
        return self._gfeatures[feature_i].available & flag_bit != 0

    def is_active(self, name):
        feature_i, flag_bit = self._offsets[name]
        return self._gfeatures[feature_i].active & flag_bit != 0

    def is_requested(self, name):
        feature_i, flag_bit = self._offsets[name]
        return self._gfeatures[feature_i].requested & flag_bit != 0

    def is_never_changed(self, name):
        feature_i, flag_bit = self._offsets[name]
        return self._gfeatures[feature_i].never_changed & flag_bit != 0

    def __iter__(self):
        for name in self._offsets:
            feature_i, flag_bit = self._offsets[name]
            yield (
                name,
                self.get_value(name),
                self.is_available(name),
                feature_i,
                flag_bit,
            )

    def keys(self):
        return self._offsets.keys()

    def __contains__(self, name):
        return name in self._offsets

    def __getitem__(self, key):
        return self.get_value(key)

    def __setitem__(self, key, value):
        return self.set_value(key, value)

    def get_value(self, name):
        return self.is_active(name)

    def set_value(self, name, value):
        if value not in (1, 0, True, False):
            raise ValueError("Need a boolean value")

        feature_i, flag_bit = self._offsets[name]
        if value:
            self._gfeatures[feature_i].active |= flag_bit
            self._sfeatures[feature_i].active |= flag_bit
        else:
            # active is ctypes.c_uint32
            self._gfeatures[feature_i].active &= flag_bit ^ 0xFFFFFFFF
            self._sfeatures[feature_i].active &= flag_bit ^ 0xFFFFFFFF
        self._sfeatures[feature_i].changed |= flag_bit


class IoctlEthtool:
    def __init__(self, ifname=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ifname = None
        self.ifreq = None
        self.stat_names = None

        if ifname is not None:
            self.change_ifname(ifname)

    def close(self):
        self.sock.close()

    def change_ifname(self, ifname):
        self.ifname = bytearray(ifname, 'utf-8')
        self.ifname.extend(b"\0" * (IFNAMSIZ - len(self.ifname)))
        self.ifreq = IfReq()
        self.ifreq.ifr_name = (ctypes.c_uint8 * IFNAMSIZ)(*self.ifname)
        self.stat_names = None

    def ioctl(self):
        try:
            if fcntl.ioctl(self.sock, SIOCETHTOOL, self.ifreq):
                raise NotSupportedError()
        except OSError as e:
            if e.errno == errno.ENOTSUP:
                raise NotSupportedError(self.ifname.decode("utf-8"))
            elif e.errno == errno.ENODEV:
                raise NoSuchDevice(self.ifname.decode("utf-8"))
            raise

    def get_statistics(self):
        """Statistics in raw format, without names"""
        if not self.stat_names:
            self.stat_names = self.get_stringset(set_id=ETH_SS_STATS)
        gstats = generate_EthtoolGStats(len(self.stat_names))(
            cmd=ETHTOOL_GSTATS
        )
        self.ifreq.gstats = ctypes.cast(
            ctypes.pointer(gstats), ctypes.POINTER(None)
        )
        self.ioctl()
        assert len(self.stat_names) == len(gstats.data)
        return list(zip(self.stat_names, gstats.data))

    def get_stringset_length(self, set_id):
        sset_info = EthtoolSsetInfo(
            cmd=ETHTOOL_GSSET_INFO, reserved=0, sset_mask=1 << set_id
        )
        ifreq_sset = IfReqSsetInfo()
        ifreq_sset.ifr_name = (ctypes.c_uint8 * IFNAMSIZ)(*self.ifname)
        ifreq_sset.info = ctypes.pointer(sset_info)
        fcntl.ioctl(self.sock, SIOCETHTOOL, ifreq_sset)
        assert sset_info.sset_mask
        return sset_info.data

    def get_stringset(
        self, set_id=ETH_SS_FEATURES, drvinfo_offset=0, null_terminate=1
    ):
        # different sets have potentially different lengthts,
        # obtain size dynamically
        gstrings_length = self.get_stringset_length(set_id)
        EthtoolGstringsType = generate_EthtoolGstrings(gstrings_length)
        gstrings = EthtoolGstringsType(
            cmd=ETHTOOL_GSTRINGS, string_set=set_id, len=gstrings_length
        )
        self.ifreq.gstrings = ctypes.cast(
            ctypes.pointer(gstrings), ctypes.POINTER(None)
        )
        self.ioctl()

        strings_found = []
        for i in range(gstrings_length):
            buf = ''
            for j in range(ETH_GSTRING_LEN):
                code = gstrings.strings[i][j]
                if code == 0:
                    break
                buf += chr(code)
            strings_found.append(buf)
        return strings_found

    def get_features(self):
        stringsset = self.get_stringset(set_id=ETH_SS_FEATURES)
        cmd = EthtoolGfeatures()
        cmd.cmd = ETHTOOL_GFEATURES
        cmd.size = feature_bits_to_blocks(len(stringsset))
        self.ifreq.gfeatures = ctypes.pointer(cmd)
        self.ioctl()
        return EthtoolFeaturesList(cmd, stringsset)

    def set_features(self, features):
        self.ifreq.sfeatures = ctypes.pointer(features._cmd_set)
        return self.ioctl()

    def get_cmd(self):
        cmd = EthtoolCmd(cmd=ETHTOOL_GSET)
        self.ifreq.ifr_data = ctypes.pointer(cmd)
        self.ioctl()
        return cmd

    @staticmethod
    def get_link_mode_bits(map_bits):
        for bit in LinkModeBits:
            map_i = bit.bit_index // 32
            map_bit = bit.bit_index % 32
            if map_i >= len(map_bits):
                continue

            if map_bits[map_i] & (1 << map_bit):
                yield bit

    @staticmethod
    def get_link_mode_masks(ecmd):
        map_supported = []
        map_advertising = []
        map_lp_advertising = []
        i = 0
        while i != ecmd.link_mode_masks_nwords:
            map_supported.append(ecmd.link_mode_data[i])
            i += 1
        while i != ecmd.link_mode_masks_nwords * 2:
            map_advertising.append(ecmd.link_mode_data[i])
            i += 1
        while i != ecmd.link_mode_masks_nwords * 3:
            map_lp_advertising.append(ecmd.link_mode_data[i])
            i += 1

        return (map_supported, map_advertising, map_lp_advertising)

    def get_link_settings(self):
        ecmd = IoctlEthtoolLinkSettings()
        ecmd.cmd = ETHTOOL_GLINKSETTINGS
        self.ifreq.glinksettings = ctypes.pointer(ecmd)

        # Handshake with kernel to determine number of words for link
        # mode bitmaps. When requested number of bitmap words is not
        # the one expected by kernel, the latter returns the integer
        # opposite of what it is expecting. We request length 0 below
        # (aka. invalid bitmap length) to get this info.
        self.ioctl()

        # see above: we expect a strictly negative value from kernel.
        if (
            ecmd.link_mode_masks_nwords >= 0
            or ecmd.cmd != ETHTOOL_GLINKSETTINGS
        ):
            raise NotSupportedError()

        # got the real ecmd.req.link_mode_masks_nwords,
        # now send the real request
        ecmd.link_mode_masks_nwords = -ecmd.link_mode_masks_nwords
        self.ioctl()

        if (
            ecmd.link_mode_masks_nwords <= 0
            or ecmd.cmd != ETHTOOL_GLINKSETTINGS
        ):
            raise NotSupportedError()

        return ecmd

    def get_coalesce(self):
        cmd = EthtoolCoalesce(cmd=ETHTOOL_GCOALESCE)
        self.ifreq.coalesce = ctypes.pointer(cmd)
        self.ioctl()
        return cmd

    def set_coalesce(self, coalesce):
        coalesce.cmd = ETHTOOL_SCOALESCE
        self.ifreq.coalesce = ctypes.pointer(coalesce)
        self.ioctl()
        return

    def get_wol(self):
        cmd = EthtoolWolInfo(cmd=ETHTOOL_GWOL)
        self.ifreq.wolinfo = ctypes.pointer(cmd)
        self.ioctl()
        return cmd

    def get_rings(self):
        cmd = EthtoolRingParam(cmd=ETHTOOL_GRINGPARAM)
        self.ifreq.rings = ctypes.pointer(cmd)
        self.ioctl()
        return cmd

    def set_rings(self, rings):
        rings.cmd = ETHTOOL_SRINGPARAM
        self.ifreq.rings = ctypes.pointer(rings)
        self.ioctl()
