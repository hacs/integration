from pyroute2.common import map_namespace

# ARP protocol HARDWARE identifiers.
ARPHRD_NETROM = 0  # from KA9Q: NET/ROM pseudo
ARPHRD_ETHER = 1  # Ethernet 10Mbps
ARPHRD_EETHER = 2  # Experimental Ethernet
ARPHRD_AX25 = 3  # AX.25 Level 2
ARPHRD_PRONET = 4  # PROnet token ring
ARPHRD_CHAOS = 5  # Chaosnet
ARPHRD_IEEE802 = 6  # IEEE 802.2 Ethernet/TR/TB
ARPHRD_ARCNET = 7  # ARCnet
ARPHRD_APPLETLK = 8  # APPLEtalk
ARPHRD_DLCI = 15  # Frame Relay DLCI
ARPHRD_ATM = 19  # ATM
ARPHRD_METRICOM = 23  # Metricom STRIP (new IANA id)
ARPHRD_IEEE1394 = 24  # IEEE 1394 IPv4 - RFC 2734
ARPHRD_EUI64 = 27  # EUI-64
ARPHRD_INFINIBAND = 32  # InfiniBand

# Dummy types for non ARP hardware
ARPHRD_SLIP = 256
ARPHRD_CSLIP = 257
ARPHRD_SLIP6 = 258
ARPHRD_CSLIP6 = 259
ARPHRD_RSRVD = 260  # Notional KISS type
ARPHRD_ADAPT = 264
ARPHRD_ROSE = 270
ARPHRD_X25 = 271  # CCITT X.25
ARPHRD_HWX25 = 272  # Boards with X.25 in firmware
ARPHRD_PPP = 512
ARPHRD_CISCO = 513  # Cisco HDLC
ARPHRD_HDLC = ARPHRD_CISCO
ARPHRD_LAPB = 516  # LAPB
ARPHRD_DDCMP = 517  # Digital's DDCMP protocol
ARPHRD_RAWHDLC = 518  # Raw HDLC

ARPHRD_TUNNEL = 768  # IPIP tunnel
ARPHRD_TUNNEL6 = 769  # IP6IP6 tunnel
ARPHRD_FRAD = 770  # Frame Relay Access Device
ARPHRD_SKIP = 771  # SKIP vif
ARPHRD_LOOPBACK = 772  # Loopback device
ARPHRD_LOCALTLK = 773  # Localtalk device
ARPHRD_FDDI = 774  # Fiber Distributed Data Interface
ARPHRD_BIF = 775  # AP1000 BIF
ARPHRD_SIT = 776  # sit0 device - IPv6-in-IPv4
ARPHRD_IPDDP = 777  # IP over DDP tunneller
ARPHRD_IPGRE = 778  # GRE over IP
ARPHRD_PIMREG = 779  # PIMSM register interface
ARPHRD_HIPPI = 780  # High Performance Parallel Interface
ARPHRD_ASH = 781  # Nexus 64Mbps Ash
ARPHRD_ECONET = 782  # Acorn Econet
ARPHRD_IRDA = 783  # Linux-IrDA
# ARP works differently on different FC media .. so
ARPHRD_FCPP = 784  # Point to point fibrechannel
ARPHRD_FCAL = 785  # Fibrechannel arbitrated loop
ARPHRD_FCPL = 786  # Fibrechannel public loop
ARPHRD_FCFABRIC = 787  # Fibrechannel fabric
# 787->799 reserved for fibrechannel media types
ARPHRD_IEEE802_TR = 800  # Magic type ident for TR
ARPHRD_IEEE80211 = 801  # IEEE 802.11
ARPHRD_IEEE80211_PRISM = 802  # IEEE 802.11 + Prism2 header
ARPHRD_IEEE80211_RADIOTAP = 803  # IEEE 802.11 + radiotap header
ARPHRD_MPLS_TUNNEL = 899  # MPLS Tunnel Interface

ARPHRD_VOID = 0xFFFF  # Void type, nothing is known
ARPHRD_NONE = 0xFFFE  # zero header length

(ARPHRD_NAMES, ARPHRD_VALUES) = map_namespace("ARPHRD_", globals())
