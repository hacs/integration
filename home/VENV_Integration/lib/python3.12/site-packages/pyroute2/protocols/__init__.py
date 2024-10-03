import struct
from socket import AF_INET, inet_ntop, inet_pton

from pyroute2.common import basestring, hexdump

#
# IEEE = 802.3 Ethernet magic constants. The frame sizes omit
# the preamble and FCS/CRC (frame check sequence).
#

ETH_ALEN = 6  # Octets in one ethernet addr
ETH_HLEN = 14  # Total octets in header.
ETH_ZLEN = 60  # Min. octets in frame sans FCS
ETH_DATA_LEN = 1500  # Max. octets in payload
ETH_FRAME_LEN = 1514  # Max. octets in frame sans FCS
ETH_FCS_LEN = 4  # Octets in the FCS

#
# These are the defined Ethernet Protocol ID's.
#

ETH_P_LOOP = 0x0060  # Ethernet Loopback packet
ETH_P_PUP = 0x0200  # Xerox PUP packet
ETH_P_PUPAT = 0x0201  # Xerox PUP Addr Trans packet
ETH_P_IP = 0x0800  # Internet Protocol packet
ETH_P_X25 = 0x0805  # CCITT X.25
ETH_P_ARP = 0x0806  # Address Resolution packet
ETH_P_BPQ = 0x08FF  # G8BPQ AX.25 Ethernet Packet
# ^^^ [ NOT AN OFFICIALLY REGISTERED ID ]
ETH_P_IEEEPUP = 0x0A00  # Xerox IEEE802.3 PUP packet
ETH_P_IEEEPUPAT = 0x0A01  # Xerox IEEE802.3 PUP Addr Trans packet
ETH_P_DEC = 0x6000  # DEC Assigned proto
ETH_P_DNA_DL = 0x6001  # DEC DNA Dump/Load
ETH_P_DNA_RC = 0x6002  # DEC DNA Remote Console
ETH_P_DNA_RT = 0x6003  # DEC DNA Routing
ETH_P_LAT = 0x6004  # DEC LAT
ETH_P_DIAG = 0x6005  # DEC Diagnostics
ETH_P_CUST = 0x6006  # DEC Customer use
ETH_P_SCA = 0x6007  # DEC Systems Comms Arch
ETH_P_TEB = 0x6558  # Trans Ether Bridging
ETH_P_RARP = 0x8035  # Reverse Addr Res packet
ETH_P_ATALK = 0x809B  # Appletalk DDP
ETH_P_AARP = 0x80F3  # Appletalk AARP
ETH_P_8021Q = 0x8100  # = 802.1Q VLAN Extended Header
ETH_P_IPX = 0x8137  # IPX over DIX
ETH_P_IPV6 = 0x86DD  # IPv6 over bluebook
ETH_P_PAUSE = 0x8808  # IEEE Pause frames. See = 802.3 = 31B
ETH_P_SLOW = 0x8809  # Slow Protocol. See = 802.3ad = 43B
ETH_P_WCCP = 0x883E  # Web-cache coordination protocol
# defined in draft-wilson-wrec-wccp-v2-00.txt
ETH_P_PPP_DISC = 0x8863  # PPPoE discovery messages
ETH_P_PPP_SES = 0x8864  # PPPoE session messages
ETH_P_MPLS_UC = 0x8847  # MPLS Unicast traffic
ETH_P_MPLS_MC = 0x8848  # MPLS Multicast traffic
ETH_P_ATMMPOA = 0x884C  # MultiProtocol Over ATM
ETH_P_LINK_CTL = 0x886C  # HPNA, wlan link local tunnel
ETH_P_ATMFATE = 0x8884  # Frame-based ATM Transport over Ethernet

ETH_P_PAE = 0x888E  # Port Access Entity (IEEE = 802.1X)
ETH_P_AOE = 0x88A2  # ATA over Ethernet
ETH_P_8021AD = 0x88A8  # = 802.1ad Service VLAN
ETH_P_802_EX1 = 0x88B5  # = 802.1 Local Experimental = 1.
ETH_P_TIPC = 0x88CA  # TIPC
ETH_P_8021AH = 0x88E7  # = 802.1ah Backbone Service Tag
ETH_P_1588 = 0x88F7  # IEEE = 1588 Timesync
ETH_P_FCOE = 0x8906  # Fibre Channel over Ethernet
ETH_P_TDLS = 0x890D  # TDLS
ETH_P_FIP = 0x8914  # FCoE Initialization Protocol
ETH_P_QINQ1 = 0x9100  # deprecated QinQ VLAN
# ^^^ [ NOT AN OFFICIALLY REGISTERED ID ]
ETH_P_QINQ2 = 0x9200  # deprecated QinQ VLAN
# ^^^ [ NOT AN OFFICIALLY REGISTERED ID ]
ETH_P_QINQ3 = 0x9300  # deprecated QinQ VLAN
# ^^^ [ NOT AN OFFICIALLY REGISTERED ID ]
ETH_P_EDSA = 0xDADA  # Ethertype DSA
# ^^^ [ NOT AN OFFICIALLY REGISTERED ID ]
ETH_P_AF_IUCV = 0xFBFB  # IBM af_iucv
# ^^^ [ NOT AN OFFICIALLY REGISTERED ID ]

#
# Non DIX types. Won't clash for = 1500 types.
#

ETH_P_802_3 = 0x0001  # Dummy type for = 802.3 frames
ETH_P_AX25 = 0x0002  # Dummy protocol id for AX.25
ETH_P_ALL = 0x0003  # Every packet (be careful!!!)
ETH_P_802_2 = 0x0004  # = 802.2 frames
ETH_P_SNAP = 0x0005  # Internal only
ETH_P_DDCMP = 0x0006  # DEC DDCMP: Internal only
ETH_P_WAN_PPP = 0x0007  # Dummy type for WAN PPP frames*/
ETH_P_PPP_MP = 0x0008  # Dummy type for PPP MP frames
ETH_P_LOCALTALK = 0x0009  # Localtalk pseudo type
ETH_P_CAN = 0x000C  # Controller Area Network
ETH_P_PPPTALK = 0x0010  # Dummy type for Atalk over PPP*/
ETH_P_TR_802_2 = 0x0011  # = 802.2 frames
ETH_P_MOBITEX = 0x0015  # Mobitex (kaz@cafe.net)
ETH_P_CONTROL = 0x0016  # Card specific control frames
ETH_P_IRDA = 0x0017  # Linux-IrDA
ETH_P_ECONET = 0x0018  # Acorn Econet
ETH_P_HDLC = 0x0019  # HDLC frames
ETH_P_ARCNET = 0x001A  # = 1A for ArcNet :-)
ETH_P_DSA = 0x001B  # Distributed Switch Arch.
ETH_P_TRAILER = 0x001C  # Trailer switch tagging
ETH_P_PHONET = 0x00F5  # Nokia Phonet frames
ETH_P_IEEE802154 = 0x00F6  # IEEE802.15.4 frame
ETH_P_CAIF = 0x00F7  # ST-Ericsson CAIF protocol


class msg(dict):
    buf = None
    data_len = None
    fields = ()
    _fields_names = ()
    types = {
        'uint8': 'B',
        'uint16': 'H',
        'uint32': 'I',
        'be16': '>H',
        'ip4addr': {
            'format': '4s',
            'decode': lambda x: inet_ntop(AF_INET, x),
            'encode': lambda x: [inet_pton(AF_INET, x)],
        },
        'l2addr': {
            'format': '6B',
            'decode': lambda x: ':'.join(['%x' % i for i in x]),
            'encode': lambda x: [int(i, 16) for i in x.split(':')],
        },
        'l2paddr': {
            'format': '6B10s',
            'decode': lambda x: ':'.join(['%x' % i for i in x[:6]]),
            'encode': lambda x: [int(i, 16) for i in x.split(':')]
            + [10 * b'\x00'],
        },
    }

    def __init__(self, content=None, buf=b'', offset=0, value=None):
        content = content or {}
        dict.__init__(self, content)
        self.buf = buf
        self.offset = offset
        self.value = value
        self._register_fields()

    def _register_fields(self):
        self._fields_names = tuple([x[0] for x in self.fields])

    def _get_routine(self, mode, fmt):
        fmt = self.types.get(fmt, fmt)
        if isinstance(fmt, dict):
            return (fmt['format'], fmt.get(mode, lambda x: x))
        else:
            return (fmt, lambda x: x)

    def reset(self):
        self.buf = b''

    def decode(self):
        self._register_fields()
        for field in self.fields:
            name, sfmt = field[:2]
            fmt, routine = self._get_routine('decode', sfmt)
            size = struct.calcsize(fmt)
            value = struct.unpack(
                fmt, self.buf[self.offset : self.offset + size]
            )
            if len(value) == 1:
                value = value[0]
            if isinstance(value, basestring) and sfmt[-1] == 's':
                value = value[: value.find(b'\x00')]
            if isinstance(sfmt, str) and sfmt[-1] == 's':
                try:
                    value = value.decode('utf-8')
                except UnicodeDecodeError:
                    value = hexdump(value)
            self[name] = routine(value)
            self.offset += size
        return self

    def encode(self):
        self._register_fields()
        for field in self.fields:
            name, fmt = field[:2]
            default = b'\x00' if len(field) <= 2 else field[2]
            fmt, routine = self._get_routine('encode', fmt)
            # special case: string
            if fmt == 'string':
                self.buf += routine(self[name])[0]
            else:
                size = struct.calcsize(fmt)
                if self[name] is None:
                    if not isinstance(default, basestring):
                        self.buf += struct.pack(fmt, default)
                    else:
                        self.buf += default * (size // len(default))
                else:
                    value = routine(self[name])
                    if not isinstance(value, (set, tuple, list)):
                        value = [value]
                    self.buf += struct.pack(fmt, *value)
        return self

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if key in self._fields_names:
                return None
            raise


class ethmsg(msg):
    fields = (('dst', 'l2addr'), ('src', 'l2addr'), ('type', 'be16'))


class ip6msg(msg):
    fields = (
        ('version', 'uint8', 6 << 4),
        ('_flow0', 'uint8'),
        ('_flow1', 'uint8'),
        ('_flow2', 'uint8'),
        ('plen', 'uin16'),
        ('next_header', 'uint8'),
        ('hop_limit', 'uint8'),
        ('src', 'ip6addr'),
        ('dst', 'ip6addr'),
    )


class ip4msg(msg):
    fields = (
        ('verlen', 'uint8', 0x45),
        ('dsf', 'uint8'),
        ('len', 'be16'),
        ('id', 'be16'),
        ('flags', 'uint16'),
        ('ttl', 'uint8', 128),
        ('proto', 'uint8'),
        ('csum', 'be16'),
        ('src', 'ip4addr'),
        ('dst', 'ip4addr'),
    )


class udp4_pseudo_header(msg):
    fields = (
        ('src', 'ip4addr'),
        ('dst', 'ip4addr'),
        ('pad', 'uint8'),
        ('proto', 'uint8', 17),
        ('len', 'be16'),
    )


class udpmsg(msg):
    fields = (
        ('sport', 'be16'),
        ('dport', 'be16'),
        ('len', 'be16'),
        ('csum', 'be16'),
    )
