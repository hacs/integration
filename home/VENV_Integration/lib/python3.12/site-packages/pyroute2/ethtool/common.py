from collections import namedtuple

# from ethtool/ethtool-copy.h of ethtool repo

DUPLEX_HALF = 0x0
DUPLEX_FULL = 0x1
DUPLEX_UNKNOWN = 0xFF

LINK_DUPLEX_NAMES = {
    DUPLEX_HALF: "Half",
    DUPLEX_FULL: "Full",
    DUPLEX_UNKNOWN: "Unknown",
}

# Which connector port.
PORT_TP = 0x00
PORT_AUI = 0x01
PORT_MII = 0x02
PORT_FIBRE = 0x03
PORT_BNC = 0x04
PORT_DA = 0x05
PORT_NONE = 0xEF
PORT_OTHER = 0xFF
LINK_PORT_NAMES = {
    PORT_TP: "Twisted Pair",
    PORT_AUI: "AUI",
    PORT_MII: "MII",
    PORT_FIBRE: "FIBRE",
    PORT_BNC: "BNC",
    PORT_DA: "Direct Attach Copper",
    PORT_NONE: "NONE",
    PORT_OTHER: "Other",
}

# Which transceiver to use.
XCVR_INTERNAL = 0x00  # PHY and MAC are in the same package
XCVR_EXTERNAL = 0x01  # PHY and MAC are in different packages
LINK_TRANSCEIVER_NAMES = {XCVR_INTERNAL: "Internal", XCVR_EXTERNAL: "External"}

# Enable or disable autonegotiation.
AUTONEG_DISABLE = 0x00
AUTONEG_ENABLE = 0x01
LINK_AUTONEG_NAMES = {AUTONEG_DISABLE: "off", AUTONEG_ENABLE: "on"}

# MDI or MDI-X status/control - if MDI/MDI_X/AUTO is set then
# the driver is required to renegotiate link
ETH_TP_MDI_INVALID = 0x00  # status: unknown; control: unsupported
ETH_TP_MDI = 0x01  # status: MDI; control: force MDI
ETH_TP_MDI_X = 0x02  # status: MDI-X; control: force MDI-X
ETH_TP_MDI_AUTO = 0x03  # control: auto-select
LINK_TP_MDI_NAMES = {
    ETH_TP_MDI: "off",
    ETH_TP_MDI_X: "on",
    ETH_TP_MDI_AUTO: "auto",
}


LMBTypePort = 0
LMBTypeMode = 1
LMBTypeOther = -1
LinkModeBit = namedtuple('LinkModeBit', ('bit_index', 'name', 'type'))
LinkModeBits = (
    LinkModeBit(bit_index=0, name='10baseT/Half', type=LMBTypeMode),
    LinkModeBit(bit_index=1, name='10baseT/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=2, name='100baseT/Half', type=LMBTypeMode),
    LinkModeBit(bit_index=3, name='100baseT/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=4, name='1000baseT/Half', type=LMBTypeMode),
    LinkModeBit(bit_index=5, name='1000baseT/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=6, name='Autoneg', type=LMBTypeOther),
    LinkModeBit(bit_index=7, name='TP', type=LMBTypePort),
    LinkModeBit(bit_index=8, name='AUI', type=LMBTypePort),
    LinkModeBit(bit_index=9, name='MII', type=LMBTypePort),
    LinkModeBit(bit_index=10, name='FIBRE', type=LMBTypePort),
    LinkModeBit(bit_index=11, name='BNC', type=LMBTypePort),
    LinkModeBit(bit_index=12, name='10000baseT/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=13, name='Pause', type=LMBTypeOther),
    LinkModeBit(bit_index=14, name='Asym_Pause', type=LMBTypeOther),
    LinkModeBit(bit_index=15, name='2500baseX/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=16, name='Backplane', type=LMBTypeOther),
    LinkModeBit(bit_index=17, name='1000baseKX/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=18, name='10000baseKX4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=19, name='10000baseKR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=20, name='10000baseR_FEC', type=LMBTypeMode),
    LinkModeBit(bit_index=21, name='20000baseMLD2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=22, name='20000baseKR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=23, name='40000baseKR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=24, name='40000baseCR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=25, name='40000baseSR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=26, name='40000baseLR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=27, name='56000baseKR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=28, name='56000baseCR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=29, name='56000baseSR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=30, name='56000baseLR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=31, name='25000baseCR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=32, name='25000baseKR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=33, name='25000baseSR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=34, name='50000baseCR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=35, name='50000baseKR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=36, name='100000baseKR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=37, name='100000baseSR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=38, name='100000baseCR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=39, name='100000baseLR4_ER4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=40, name='50000baseSR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=41, name='1000baseX/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=42, name='10000baseCR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=43, name='10000baseSR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=44, name='10000baseLR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=45, name='10000baseLRM/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=46, name='10000baseER/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=47, name='2500baseT/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=48, name='5000baseT/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=49, name='FEC_NONE', type=LMBTypeOther),
    LinkModeBit(bit_index=50, name='FEC_RS', type=LMBTypeOther),
    LinkModeBit(bit_index=51, name='FEC_BASER', type=LMBTypeOther),
    LinkModeBit(bit_index=52, name='50000baseKR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=53, name='50000baseSR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=54, name='50000baseCR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=55, name='50000baseLR_ER_FR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=56, name='50000baseDR/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=57, name='100000baseKR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=58, name='100000baseSR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=59, name='100000baseCR2/Full', type=LMBTypeMode),
    LinkModeBit(
        bit_index=60, name='100000baseLR2_ER2_FR2/Full', type=LMBTypeMode
    ),
    LinkModeBit(bit_index=61, name='100000baseDR2/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=62, name='200000baseKR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=63, name='200000baseSR4/Full', type=LMBTypeMode),
    LinkModeBit(
        bit_index=64, name='200000baseLR4_ER4_FR4/Full', type=LMBTypeMode
    ),
    LinkModeBit(bit_index=65, name='200000baseDR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=66, name='200000baseCR4/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=67, name='100baseT1/Full', type=LMBTypeMode),
    LinkModeBit(bit_index=68, name='1000baseT1/Full', type=LMBTypeMode),
)
LinkModeBits_by_index = {bit.bit_index: bit for bit in LinkModeBits}
