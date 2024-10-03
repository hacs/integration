'''
NL80211 module
==============

TODO
'''

import datetime
import struct

from pyroute2.common import map_namespace
from pyroute2.netlink import genlmsg, nla, nla_base
from pyroute2.netlink.generic import GenericNetlinkSocket
from pyroute2.netlink.nlsocket import Marshal

# Define from uapi/linux/nl80211.h
NL80211_GENL_NAME = "nl80211"

# nl80211 commands

NL80211_CMD_UNSPEC = 0
NL80211_CMD_GET_WIPHY = 1
NL80211_CMD_SET_WIPHY = 2
NL80211_CMD_NEW_WIPHY = 3
NL80211_CMD_DEL_WIPHY = 4
NL80211_CMD_GET_INTERFACE = 5
NL80211_CMD_SET_INTERFACE = 6
NL80211_CMD_NEW_INTERFACE = 7
NL80211_CMD_DEL_INTERFACE = 8
NL80211_CMD_GET_KEY = 9
NL80211_CMD_SET_KEY = 10
NL80211_CMD_NEW_KEY = 11
NL80211_CMD_DEL_KEY = 12
NL80211_CMD_GET_BEACON = 13
NL80211_CMD_SET_BEACON = 14
NL80211_CMD_START_AP = 15
NL80211_CMD_NEW_BEACON = NL80211_CMD_START_AP
NL80211_CMD_STOP_AP = 16
NL80211_CMD_DEL_BEACON = NL80211_CMD_STOP_AP
NL80211_CMD_GET_STATION = 17
NL80211_CMD_SET_STATION = 18
NL80211_CMD_NEW_STATION = 19
NL80211_CMD_DEL_STATION = 20
NL80211_CMD_GET_MPATH = 21
NL80211_CMD_SET_MPATH = 22
NL80211_CMD_NEW_MPATH = 23
NL80211_CMD_DEL_MPATH = 24
NL80211_CMD_SET_BSS = 25
NL80211_CMD_SET_REG = 26
NL80211_CMD_REQ_SET_REG = 27
NL80211_CMD_GET_MESH_CONFIG = 28
NL80211_CMD_SET_MESH_CONFIG = 29
NL80211_CMD_SET_MGMT_EXTRA_IE = 30
NL80211_CMD_GET_REG = 31
NL80211_CMD_GET_SCAN = 32
NL80211_CMD_TRIGGER_SCAN = 33
NL80211_CMD_NEW_SCAN_RESULTS = 34
NL80211_CMD_SCAN_ABORTED = 35
NL80211_CMD_REG_CHANGE = 36
NL80211_CMD_AUTHENTICATE = 37
NL80211_CMD_ASSOCIATE = 38
NL80211_CMD_DEAUTHENTICATE = 39
NL80211_CMD_DISASSOCIATE = 40
NL80211_CMD_MICHAEL_MIC_FAILURE = 41
NL80211_CMD_REG_BEACON_HINT = 42
NL80211_CMD_JOIN_IBSS = 43
NL80211_CMD_LEAVE_IBSS = 44
NL80211_CMD_TESTMODE = 45
NL80211_CMD_CONNECT = 46
NL80211_CMD_ROAM = 47
NL80211_CMD_DISCONNECT = 48
NL80211_CMD_SET_WIPHY_NETNS = 49
NL80211_CMD_GET_SURVEY = 50
NL80211_CMD_NEW_SURVEY_RESULTS = 51
NL80211_CMD_SET_PMKSA = 52
NL80211_CMD_DEL_PMKSA = 53
NL80211_CMD_FLUSH_PMKSA = 54
NL80211_CMD_REMAIN_ON_CHANNEL = 55
NL80211_CMD_CANCEL_REMAIN_ON_CHANNEL = 56
NL80211_CMD_SET_TX_BITRATE_MASK = 57
NL80211_CMD_REGISTER_FRAME = 58
NL80211_CMD_REGISTER_ACTION = NL80211_CMD_REGISTER_FRAME
NL80211_CMD_FRAME = 59
NL80211_CMD_ACTION = NL80211_CMD_FRAME
NL80211_CMD_FRAME_TX_STATUS = 60
NL80211_CMD_ACTION_TX_STATUS = NL80211_CMD_FRAME_TX_STATUS
NL80211_CMD_SET_POWER_SAVE = 61
NL80211_CMD_GET_POWER_SAVE = 62
NL80211_CMD_SET_CQM = 63
NL80211_CMD_NOTIFY_CQM = 64
NL80211_CMD_SET_CHANNEL = 65
NL80211_CMD_SET_WDS_PEER = 66
NL80211_CMD_FRAME_WAIT_CANCEL = 67
NL80211_CMD_JOIN_MESH = 68
NL80211_CMD_LEAVE_MESH = 69
NL80211_CMD_UNPROT_DEAUTHENTICATE = 70
NL80211_CMD_UNPROT_DISASSOCIATE = 71
NL80211_CMD_NEW_PEER_CANDIDATE = 72
NL80211_CMD_GET_WOWLAN = 73
NL80211_CMD_SET_WOWLAN = 74
NL80211_CMD_START_SCHED_SCAN = 75
NL80211_CMD_STOP_SCHED_SCAN = 76
NL80211_CMD_SCHED_SCAN_RESULTS = 77
NL80211_CMD_SCHED_SCAN_STOPPED = 78
NL80211_CMD_SET_REKEY_OFFLOAD = 79
NL80211_CMD_PMKSA_CANDIDATE = 80
NL80211_CMD_TDLS_OPER = 81
NL80211_CMD_TDLS_MGMT = 82
NL80211_CMD_UNEXPECTED_FRAME = 83
NL80211_CMD_PROBE_CLIENT = 84
NL80211_CMD_REGISTER_BEACONS = 85
NL80211_CMD_UNEXPECTED_4ADDR_FRAME = 86
NL80211_CMD_SET_NOACK_MAP = 87
NL80211_CMD_CH_SWITCH_NOTIFY = 88
NL80211_CMD_START_P2P_DEVICE = 89
NL80211_CMD_STOP_P2P_DEVICE = 90
NL80211_CMD_CONN_FAILED = 91
NL80211_CMD_SET_MCAST_RATE = 92
NL80211_CMD_SET_MAC_ACL = 93
NL80211_CMD_RADAR_DETECT = 94
NL80211_CMD_GET_PROTOCOL_FEATURES = 95
NL80211_CMD_UPDATE_FT_IES = 96
NL80211_CMD_FT_EVENT = 97
NL80211_CMD_CRIT_PROTOCOL_START = 98
NL80211_CMD_CRIT_PROTOCOL_STOP = 99
NL80211_CMD_GET_COALESCE = 100
NL80211_CMD_SET_COALESCE = 101
NL80211_CMD_CHANNEL_SWITCH = 102
NL80211_CMD_VENDOR = 103
NL80211_CMD_SET_QOS_MAP = 104
NL80211_CMD_ADD_TX_TS = 105
NL80211_CMD_DEL_TX_TS = 106
NL80211_CMD_GET_MPP = 107
NL80211_CMD_JOIN_OCB = 108
NL80211_CMD_LEAVE_OCB = 109
NL80211_CMD_CH_SWITCH_STARTED_NOTIFY = 110
NL80211_CMD_TDLS_CHANNEL_SWITCH = 111
NL80211_CMD_TDLS_CANCEL_CHANNEL_SWITCH = 112
NL80211_CMD_WIPHY_REG_CHANGE = 113
NL80211_CMD_MAX = NL80211_CMD_WIPHY_REG_CHANGE
(NL80211_NAMES, NL80211_VALUES) = map_namespace('NL80211_CMD_', globals())

NL80211_BSS_ELEMENTS_SSID = 0
NL80211_BSS_ELEMENTS_SUPPORTED_RATES = 1
NL80211_BSS_ELEMENTS_CHANNEL = 3
NL80211_BSS_ELEMENTS_TIM = 5
NL80211_BSS_ELEMENTS_RSN = 48
NL80211_BSS_ELEMENTS_HT_OPERATION = 61
NL80211_BSS_ELEMENTS_EXTENDED_RATE = 50
NL80211_BSS_ELEMENTS_VHT_OPERATION = 192
NL80211_BSS_ELEMENTS_VENDOR = 221

BSS_HT_OPER_CHAN_WIDTH_20 = "20 Mhz"
BSS_HT_OPER_CHAN_WIDTH_20_OR_40 = "20 or 40 MHz"
BSS_VHT_OPER_CHAN_WIDTH_20_OR_40 = BSS_HT_OPER_CHAN_WIDTH_20_OR_40
BSS_VHT_OPER_CHAN_WIDTH_80 = "80 MHz"
BSS_VHT_OPER_CHAN_WIDTH_80P80 = "80+80 MHz"
BSS_VHT_OPER_CHAN_WIDTH_160 = "160 MHz"

BSS_MEMBERSHIP_SELECTOR_HT_PHY = 127
BSS_MEMBERSHIP_SELECTOR_VHT_PHY = 126

# interface types
NL80211_IFTYPE_UNSPECIFIED = 0
NL80211_IFTYPE_ADHOC = 1
NL80211_IFTYPE_STATION = 2
NL80211_IFTYPE_AP = 3
NL80211_IFTYPE_AP_VLAN = 4
NL80211_IFTYPE_WDS = 5
NL80211_IFTYPE_MONITOR = 6
NL80211_IFTYPE_MESH_POINT = 7
NL80211_IFTYPE_P2P_CLIENT = 8
NL80211_IFTYPE_P2P_GO = 9
NL80211_IFTYPE_P2P_DEVICE = 10
NL80211_IFTYPE_OCB = 11
(IFTYPE_NAMES, IFTYPE_VALUES) = map_namespace(
    'NL80211_IFTYPE_', globals(), normalize=True
)

# channel width
NL80211_CHAN_WIDTH_20_NOHT = 0  # 20 MHz non-HT channel
NL80211_CHAN_WIDTH_20 = 1  # 20 MHz HT channel
NL80211_CHAN_WIDTH_40 = 2  # 40 MHz HT channel
NL80211_CHAN_WIDTH_80 = 3  # 80 MHz channel
NL80211_CHAN_WIDTH_80P80 = 4  # 80+80 MHz channel
NL80211_CHAN_WIDTH_160 = 5  # 160 MHz channel
NL80211_CHAN_WIDTH_5 = 6  # 5 MHz OFDM channel
NL80211_CHAN_WIDTH_10 = 7  # 10 MHz OFDM channel
(CHAN_WIDTH, WIDTH_VALUES) = map_namespace(
    'NL80211_CHAN_WIDTH_', globals(), normalize=True
)

# BSS "status"
NL80211_BSS_STATUS_AUTHENTICATED = 0  # Authenticated with this BS
NL80211_BSS_STATUS_ASSOCIATED = 1  # Associated with this BSS
NL80211_BSS_STATUS_IBSS_JOINED = 2  # Joined to this IBSS
(BSS_STATUS_NAMES, BSS_STATUS_VALUES) = map_namespace(
    'NL80211_BSS_STATUS_', globals(), normalize=True
)

# TX power adjustment
NL80211_TX_POWER_AUTOMATIC = 0  # automatically determine transmit power
NL80211_TX_POWER_LIMITED = 1  # limit TX power by the mBm parameter
NL80211_TX_POWER_FIXED = 2  # fix TX power to the mBm parameter
(TX_POWER_NAMES, TX_POWER_VALUES) = map_namespace(
    'NL80211_TX_POWER_', globals(), normalize=True
)

NL80211_SCAN_FLAG_LOW_PRIORITY = 1 << 0
NL80211_SCAN_FLAG_FLUSH = 1 << 1
NL80211_SCAN_FLAG_AP = 1 << 2
NL80211_SCAN_FLAG_RANDOM_ADDR = 1 << 3
NL80211_SCAN_FLAG_FILS_MAX_CHANNEL_TIME = 1 << 4
NL80211_SCAN_FLAG_ACCEPT_BCAST_PROBE_RESP = 1 << 5
NL80211_SCAN_FLAG_OCE_PROBE_REQ_HIGH_TX_RATE = 1 << 6
NL80211_SCAN_FLAG_OCE_PROBE_REQ_DEFERRAL_SUPPRESSION = 1 << 7
(SCAN_FLAGS_NAMES, SCAN_FLAGS_VALUES) = map_namespace(
    'NL80211_SCAN_FLAG_', globals()
)

NL80211_STA_FLAG_AUTHORIZED = 1 << 1
NL80211_STA_FLAG_SHORT_PREAMBLE = 1 << 2
NL80211_STA_FLAG_WME = 1 << 3
NL80211_STA_FLAG_MFP = 1 << 4
NL80211_STA_FLAG_AUTHENTICATED = 1 << 5
NL80211_STA_FLAG_TDLS_PEER = 1 << 6
NL80211_STA_FLAG_ASSOCIATED = 1 << 7
(STA_FLAG_NAMES, STA_FLAG_VALUES) = map_namespace(
    'NL80211_STA_FLAG_', globals()
)

# Cipher suites
WLAN_CIPHER_SUITE_USE_GROUP = 0x00FAC00
WLAN_CIPHER_SUITE_WEP40 = 0x00FAC01
WLAN_CIPHER_SUITE_TKIP = 0x00FAC02
WLAN_CIPHER_SUITE_RESERVED = 0x00FAC03
WLAN_CIPHER_SUITE_CCMP = 0x00FAC04
WLAN_CIPHER_SUITE_WEP104 = 0x00FAC05
WLAN_CIPHER_SUITE_AES_CMAC = 0x00FAC06
WLAN_CIPHER_SUITE_GCMP = 0x00FAC08
WLAN_CIPHER_SUITE_GCMP_256 = 0x00FAC09
WLAN_CIPHER_SUITE_CCMP_256 = 0x00FAC0A
WLAN_CIPHER_SUITE_BIP_GMAC_128 = 0x00FAC0B
WLAN_CIPHER_SUITE_BIP_GMAC_256 = 0x00FAC0C
WLAN_CIPHER_SUITE_BIP_CMAC_256 = 0x00FAC0D
(WLAN_CIPHER_SUITE_NAMES, WLAN_CIPHER_SUITE_VALUES) = map_namespace(
    'WLAN_CIPHER_SUITE_', globals()
)


class nl80211cmd(genlmsg):
    prefix = 'NL80211_ATTR_'
    nla_map = (
        ('NL80211_ATTR_UNSPEC', 'none'),
        ('NL80211_ATTR_WIPHY', 'uint32'),
        ('NL80211_ATTR_WIPHY_NAME', 'asciiz'),
        ('NL80211_ATTR_IFINDEX', 'uint32'),
        ('NL80211_ATTR_IFNAME', 'asciiz'),
        ('NL80211_ATTR_IFTYPE', 'uint32'),
        ('NL80211_ATTR_MAC', 'l2addr'),
        ('NL80211_ATTR_KEY_DATA', 'hex'),
        ('NL80211_ATTR_KEY_IDX', 'hex'),
        ('NL80211_ATTR_KEY_CIPHER', 'uint32'),
        ('NL80211_ATTR_KEY_SEQ', 'hex'),
        ('NL80211_ATTR_KEY_DEFAULT', 'hex'),
        ('NL80211_ATTR_BEACON_INTERVAL', 'hex'),
        ('NL80211_ATTR_DTIM_PERIOD', 'hex'),
        ('NL80211_ATTR_BEACON_HEAD', 'hex'),
        ('NL80211_ATTR_BEACON_TAIL', 'hex'),
        ('NL80211_ATTR_STA_AID', 'hex'),
        ('NL80211_ATTR_STA_FLAGS', 'hex'),
        ('NL80211_ATTR_STA_LISTEN_INTERVAL', 'hex'),
        ('NL80211_ATTR_STA_SUPPORTED_RATES', 'hex'),
        ('NL80211_ATTR_STA_VLAN', 'hex'),
        ('NL80211_ATTR_STA_INFO', 'STAInfo'),
        ('NL80211_ATTR_WIPHY_BANDS', '*band'),
        ('NL80211_ATTR_MNTR_FLAGS', 'hex'),
        ('NL80211_ATTR_MESH_ID', 'hex'),
        ('NL80211_ATTR_STA_PLINK_ACTION', 'hex'),
        ('NL80211_ATTR_MPATH_NEXT_HOP', 'hex'),
        ('NL80211_ATTR_MPATH_INFO', 'hex'),
        ('NL80211_ATTR_BSS_CTS_PROT', 'hex'),
        ('NL80211_ATTR_BSS_SHORT_PREAMBLE', 'hex'),
        ('NL80211_ATTR_BSS_SHORT_SLOT_TIME', 'hex'),
        ('NL80211_ATTR_HT_CAPABILITY', 'hex'),
        ('NL80211_ATTR_SUPPORTED_IFTYPES', 'supported_iftypes'),
        ('NL80211_ATTR_REG_ALPHA2', 'asciiz'),
        ('NL80211_ATTR_REG_RULES', '*reg_rule'),
        ('NL80211_ATTR_MESH_CONFIG', 'hex'),
        ('NL80211_ATTR_BSS_BASIC_RATES', 'hex'),
        ('NL80211_ATTR_WIPHY_TXQ_PARAMS', 'hex'),
        ('NL80211_ATTR_WIPHY_FREQ', 'uint32'),
        ('NL80211_ATTR_WIPHY_CHANNEL_TYPE', 'hex'),
        ('NL80211_ATTR_KEY_DEFAULT_MGMT', 'hex'),
        ('NL80211_ATTR_MGMT_SUBTYPE', 'hex'),
        ('NL80211_ATTR_IE', 'hex'),
        ('NL80211_ATTR_MAX_NUM_SCAN_SSIDS', 'uint8'),
        ('NL80211_ATTR_SCAN_FREQUENCIES', 'hex'),
        ('NL80211_ATTR_SCAN_SSIDS', '*string'),
        ('NL80211_ATTR_GENERATION', 'uint32'),
        ('NL80211_ATTR_BSS', 'bss'),
        ('NL80211_ATTR_REG_INITIATOR', 'hex'),
        ('NL80211_ATTR_REG_TYPE', 'hex'),
        ('NL80211_ATTR_SUPPORTED_COMMANDS', 'supported_commands'),
        ('NL80211_ATTR_FRAME', 'hex'),
        ('NL80211_ATTR_SSID', 'string'),
        ('NL80211_ATTR_AUTH_TYPE', 'uint32'),
        ('NL80211_ATTR_REASON_CODE', 'uint16'),
        ('NL80211_ATTR_KEY_TYPE', 'hex'),
        ('NL80211_ATTR_MAX_SCAN_IE_LEN', 'uint16'),
        ('NL80211_ATTR_CIPHER_SUITES', 'cipher_suites'),
        ('NL80211_ATTR_FREQ_BEFORE', 'hex'),
        ('NL80211_ATTR_FREQ_AFTER', 'hex'),
        ('NL80211_ATTR_FREQ_FIXED', 'hex'),
        ('NL80211_ATTR_WIPHY_RETRY_SHORT', 'uint8'),
        ('NL80211_ATTR_WIPHY_RETRY_LONG', 'uint8'),
        ('NL80211_ATTR_WIPHY_FRAG_THRESHOLD', 'hex'),
        ('NL80211_ATTR_WIPHY_RTS_THRESHOLD', 'hex'),
        ('NL80211_ATTR_TIMED_OUT', 'hex'),
        ('NL80211_ATTR_USE_MFP', 'hex'),
        ('NL80211_ATTR_STA_FLAGS2', 'hex'),
        ('NL80211_ATTR_CONTROL_PORT', 'hex'),
        ('NL80211_ATTR_TESTDATA', 'hex'),
        ('NL80211_ATTR_PRIVACY', 'hex'),
        ('NL80211_ATTR_DISCONNECTED_BY_AP', 'hex'),
        ('NL80211_ATTR_STATUS_CODE', 'hex'),
        ('NL80211_ATTR_CIPHER_SUITES_PAIRWISE', 'hex'),
        ('NL80211_ATTR_CIPHER_SUITE_GROUP', 'hex'),
        ('NL80211_ATTR_WPA_VERSIONS', 'hex'),
        ('NL80211_ATTR_AKM_SUITES', 'hex'),
        ('NL80211_ATTR_REQ_IE', 'hex'),
        ('NL80211_ATTR_RESP_IE', 'hex'),
        ('NL80211_ATTR_PREV_BSSID', 'hex'),
        ('NL80211_ATTR_KEY', 'hex'),
        ('NL80211_ATTR_KEYS', 'hex'),
        ('NL80211_ATTR_PID', 'uint32'),
        ('NL80211_ATTR_4ADDR', 'hex'),
        ('NL80211_ATTR_SURVEY_INFO', 'survey_info'),
        ('NL80211_ATTR_PMKID', 'hex'),
        ('NL80211_ATTR_MAX_NUM_PMKIDS', 'uint8'),
        ('NL80211_ATTR_DURATION', 'hex'),
        ('NL80211_ATTR_COOKIE', 'hex'),
        ('NL80211_ATTR_WIPHY_COVERAGE_CLASS', 'uint8'),
        ('NL80211_ATTR_TX_RATES', 'hex'),
        ('NL80211_ATTR_FRAME_MATCH', 'hex'),
        ('NL80211_ATTR_ACK', 'hex'),
        ('NL80211_ATTR_PS_STATE', 'hex'),
        ('NL80211_ATTR_CQM', 'hex'),
        ('NL80211_ATTR_LOCAL_STATE_CHANGE', 'hex'),
        ('NL80211_ATTR_AP_ISOLATE', 'hex'),
        ('NL80211_ATTR_WIPHY_TX_POWER_SETTING', 'uint32'),
        ('NL80211_ATTR_WIPHY_TX_POWER_LEVEL', 'uint32'),
        ('NL80211_ATTR_TX_FRAME_TYPES', 'hex'),
        ('NL80211_ATTR_RX_FRAME_TYPES', 'hex'),
        ('NL80211_ATTR_FRAME_TYPE', 'hex'),
        ('NL80211_ATTR_CONTROL_PORT_ETHERTYPE', 'hex'),
        ('NL80211_ATTR_CONTROL_PORT_NO_ENCRYPT', 'hex'),
        ('NL80211_ATTR_SUPPORT_IBSS_RSN', 'hex'),
        ('NL80211_ATTR_WIPHY_ANTENNA_TX', 'uint32'),
        ('NL80211_ATTR_WIPHY_ANTENNA_RX', 'uint32'),
        ('NL80211_ATTR_MCAST_RATE', 'hex'),
        ('NL80211_ATTR_OFFCHANNEL_TX_OK', 'hex'),
        ('NL80211_ATTR_BSS_HT_OPMODE', 'hex'),
        ('NL80211_ATTR_KEY_DEFAULT_TYPES', 'hex'),
        ('NL80211_ATTR_MAX_REMAIN_ON_CHANNEL_DURATION', 'hex'),
        ('NL80211_ATTR_MESH_SETUP', 'hex'),
        ('NL80211_ATTR_WIPHY_ANTENNA_AVAIL_TX', 'uint32'),
        ('NL80211_ATTR_WIPHY_ANTENNA_AVAIL_RX', 'uint32'),
        ('NL80211_ATTR_SUPPORT_MESH_AUTH', 'hex'),
        ('NL80211_ATTR_STA_PLINK_STATE', 'hex'),
        ('NL80211_ATTR_WOWLAN_TRIGGERS', 'hex'),
        ('NL80211_ATTR_WOWLAN_TRIGGERS_SUPPORTED', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_INTERVAL', 'hex'),
        ('NL80211_ATTR_INTERFACE_COMBINATIONS', 'hex'),
        ('NL80211_ATTR_SOFTWARE_IFTYPES', 'hex'),
        ('NL80211_ATTR_REKEY_DATA', 'hex'),
        ('NL80211_ATTR_MAX_NUM_SCHED_SCAN_SSIDS', 'uint8'),
        ('NL80211_ATTR_MAX_SCHED_SCAN_IE_LEN', 'uint16'),
        ('NL80211_ATTR_SCAN_SUPP_RATES', 'hex'),
        ('NL80211_ATTR_HIDDEN_SSID', 'hex'),
        ('NL80211_ATTR_IE_PROBE_RESP', 'hex'),
        ('NL80211_ATTR_IE_ASSOC_RESP', 'hex'),
        ('NL80211_ATTR_STA_WME', 'hex'),
        ('NL80211_ATTR_SUPPORT_AP_UAPSD', 'hex'),
        ('NL80211_ATTR_ROAM_SUPPORT', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_MATCH', 'hex'),
        ('NL80211_ATTR_MAX_MATCH_SETS', 'uint8'),
        ('NL80211_ATTR_PMKSA_CANDIDATE', 'hex'),
        ('NL80211_ATTR_TX_NO_CCK_RATE', 'hex'),
        ('NL80211_ATTR_TDLS_ACTION', 'hex'),
        ('NL80211_ATTR_TDLS_DIALOG_TOKEN', 'hex'),
        ('NL80211_ATTR_TDLS_OPERATION', 'hex'),
        ('NL80211_ATTR_TDLS_SUPPORT', 'hex'),
        ('NL80211_ATTR_TDLS_EXTERNAL_SETUP', 'hex'),
        ('NL80211_ATTR_DEVICE_AP_SME', 'hex'),
        ('NL80211_ATTR_DONT_WAIT_FOR_ACK', 'hex'),
        ('NL80211_ATTR_FEATURE_FLAGS', 'hex'),
        ('NL80211_ATTR_PROBE_RESP_OFFLOAD', 'hex'),
        ('NL80211_ATTR_PROBE_RESP', 'hex'),
        ('NL80211_ATTR_DFS_REGION', 'hex'),
        ('NL80211_ATTR_DISABLE_HT', 'hex'),
        ('NL80211_ATTR_HT_CAPABILITY_MASK', 'hex'),
        ('NL80211_ATTR_NOACK_MAP', 'hex'),
        ('NL80211_ATTR_INACTIVITY_TIMEOUT', 'hex'),
        ('NL80211_ATTR_RX_SIGNAL_DBM', 'hex'),
        ('NL80211_ATTR_BG_SCAN_PERIOD', 'hex'),
        ('NL80211_ATTR_WDEV', 'uint64'),
        ('NL80211_ATTR_USER_REG_HINT_TYPE', 'hex'),
        ('NL80211_ATTR_CONN_FAILED_REASON', 'hex'),
        ('NL80211_ATTR_SAE_DATA', 'hex'),
        ('NL80211_ATTR_VHT_CAPABILITY', 'hex'),
        ('NL80211_ATTR_SCAN_FLAGS', 'uint32'),
        ('NL80211_ATTR_CHANNEL_WIDTH', 'uint32'),
        ('NL80211_ATTR_CENTER_FREQ1', 'uint32'),
        ('NL80211_ATTR_CENTER_FREQ2', 'uint32'),
        ('NL80211_ATTR_P2P_CTWINDOW', 'hex'),
        ('NL80211_ATTR_P2P_OPPPS', 'hex'),
        ('NL80211_ATTR_LOCAL_MESH_POWER_MODE', 'hex'),
        ('NL80211_ATTR_ACL_POLICY', 'hex'),
        ('NL80211_ATTR_MAC_ADDRS', 'hex'),
        ('NL80211_ATTR_MAC_ACL_MAX', 'hex'),
        ('NL80211_ATTR_RADAR_EVENT', 'hex'),
        ('NL80211_ATTR_EXT_CAPA', 'array(uint8)'),
        ('NL80211_ATTR_EXT_CAPA_MASK', 'array(uint8)'),
        ('NL80211_ATTR_STA_CAPABILITY', 'hex'),
        ('NL80211_ATTR_STA_EXT_CAPABILITY', 'hex'),
        ('NL80211_ATTR_PROTOCOL_FEATURES', 'hex'),
        ('NL80211_ATTR_SPLIT_WIPHY_DUMP', 'hex'),
        ('NL80211_ATTR_DISABLE_VHT', 'hex'),
        ('NL80211_ATTR_VHT_CAPABILITY_MASK', 'array(uint8)'),
        ('NL80211_ATTR_MDID', 'hex'),
        ('NL80211_ATTR_IE_RIC', 'hex'),
        ('NL80211_ATTR_CRIT_PROT_ID', 'hex'),
        ('NL80211_ATTR_MAX_CRIT_PROT_DURATION', 'hex'),
        ('NL80211_ATTR_PEER_AID', 'hex'),
        ('NL80211_ATTR_COALESCE_RULE', 'hex'),
        ('NL80211_ATTR_CH_SWITCH_COUNT', 'hex'),
        ('NL80211_ATTR_CH_SWITCH_BLOCK_TX', 'hex'),
        ('NL80211_ATTR_CSA_IES', 'hex'),
        ('NL80211_ATTR_CSA_C_OFF_BEACON', 'hex'),
        ('NL80211_ATTR_CSA_C_OFF_PRESP', 'hex'),
        ('NL80211_ATTR_RXMGMT_FLAGS', 'hex'),
        ('NL80211_ATTR_STA_SUPPORTED_CHANNELS', 'hex'),
        ('NL80211_ATTR_STA_SUPPORTED_OPER_CLASSES', 'hex'),
        ('NL80211_ATTR_HANDLE_DFS', 'hex'),
        ('NL80211_ATTR_SUPPORT_5_MHZ', 'hex'),
        ('NL80211_ATTR_SUPPORT_10_MHZ', 'hex'),
        ('NL80211_ATTR_OPMODE_NOTIF', 'hex'),
        ('NL80211_ATTR_VENDOR_ID', 'hex'),
        ('NL80211_ATTR_VENDOR_SUBCMD', 'hex'),
        ('NL80211_ATTR_VENDOR_DATA', 'hex'),
        ('NL80211_ATTR_VENDOR_EVENTS', 'hex'),
        ('NL80211_ATTR_QOS_MAP', 'hex'),
        ('NL80211_ATTR_MAC_HINT', 'hex'),
        ('NL80211_ATTR_WIPHY_FREQ_HINT', 'hex'),
        ('NL80211_ATTR_MAX_AP_ASSOC_STA', 'hex'),
        ('NL80211_ATTR_TDLS_PEER_CAPABILITY', 'hex'),
        ('NL80211_ATTR_SOCKET_OWNER', 'hex'),
        ('NL80211_ATTR_CSA_C_OFFSETS_TX', 'hex'),
        ('NL80211_ATTR_MAX_CSA_COUNTERS', 'hex'),
        ('NL80211_ATTR_TDLS_INITIATOR', 'hex'),
        ('NL80211_ATTR_USE_RRM', 'hex'),
        ('NL80211_ATTR_WIPHY_DYN_ACK', 'hex'),
        ('NL80211_ATTR_TSID', 'hex'),
        ('NL80211_ATTR_USER_PRIO', 'hex'),
        ('NL80211_ATTR_ADMITTED_TIME', 'hex'),
        ('NL80211_ATTR_SMPS_MODE', 'hex'),
        ('NL80211_ATTR_OPER_CLASS', 'hex'),
        ('NL80211_ATTR_MAC_MASK', 'hex'),
        ('NL80211_ATTR_WIPHY_SELF_MANAGED_REG', 'hex'),
        ('NL80211_ATTR_EXT_FEATURES', 'hex'),
        ('NL80211_ATTR_SURVEY_RADIO_STATS', 'hex'),
        ('NL80211_ATTR_NETNS_FD', 'uint32'),
        ('NL80211_ATTR_SCHED_SCAN_DELAY', 'hex'),
        ('NL80211_ATTR_REG_INDOOR', 'hex'),
        ('NL80211_ATTR_MAX_NUM_SCHED_SCAN_PLANS', 'hex'),
        ('NL80211_ATTR_MAX_SCAN_PLAN_INTERVAL', 'hex'),
        ('NL80211_ATTR_MAX_SCAN_PLAN_ITERATIONS', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_PLANS', 'hex'),
        ('NL80211_ATTR_PBSS', 'hex'),
        ('NL80211_ATTR_BSS_SELECT', 'hex'),
        ('NL80211_ATTR_STA_SUPPORT_P2P_PS', 'hex'),
        ('NL80211_ATTR_PAD', 'hex'),
        ('NL80211_ATTR_IFTYPE_EXT_CAPA', 'hex'),
        ('NL80211_ATTR_MU_MIMO_GROUP_DATA', 'hex'),
        ('NL80211_ATTR_MU_MIMO_FOLLOW_MAC_ADDR', 'hex'),
        ('NL80211_ATTR_SCAN_START_TIME_TSF', 'hex'),
        ('NL80211_ATTR_SCAN_START_TIME_TSF_BSSID', 'hex'),
        ('NL80211_ATTR_MEASUREMENT_DURATION', 'hex'),
        ('NL80211_ATTR_MEASUREMENT_DURATION_MANDATORY', 'hex'),
        ('NL80211_ATTR_MESH_PEER_AID', 'hex'),
        ('NL80211_ATTR_NAN_MASTER_PREF', 'hex'),
        ('NL80211_ATTR_BANDS', 'hex'),
        ('NL80211_ATTR_NAN_FUNC', 'hex'),
        ('NL80211_ATTR_NAN_MATCH', 'hex'),
        ('NL80211_ATTR_FILS_KEK', 'hex'),
        ('NL80211_ATTR_FILS_NONCES', 'hex'),
        ('NL80211_ATTR_MULTICAST_TO_UNICAST_ENABLED', 'hex'),
        ('NL80211_ATTR_BSSID', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_RELATIVE_RSSI', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_RSSI_ADJUST', 'hex'),
        ('NL80211_ATTR_TIMEOUT_REASON', 'hex'),
        ('NL80211_ATTR_FILS_ERP_USERNAME', 'hex'),
        ('NL80211_ATTR_FILS_ERP_REALM', 'hex'),
        ('NL80211_ATTR_FILS_ERP_NEXT_SEQ_NUM', 'hex'),
        ('NL80211_ATTR_FILS_ERP_RRK', 'hex'),
        ('NL80211_ATTR_FILS_CACHE_ID', 'hex'),
        ('NL80211_ATTR_PMK', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_MULTI', 'hex'),
        ('NL80211_ATTR_SCHED_SCAN_MAX_REQS', 'hex'),
        ('NL80211_ATTR_WANT_1X_4WAY_HS', 'hex'),
        ('NL80211_ATTR_PMKR0_NAME', 'hex'),
        ('NL80211_ATTR_PORT_AUTHORIZED', 'hex'),
        ('NL80211_ATTR_EXTERNAL_AUTH_ACTION', 'hex'),
        ('NL80211_ATTR_EXTERNAL_AUTH_SUPPORT', 'hex'),
        ('NL80211_ATTR_NSS', 'hex'),
        ('NL80211_ATTR_ACK_SIGNAL', 'hex'),
        ('NL80211_ATTR_CONTROL_PORT_OVER_NL80211', 'hex'),
        ('NL80211_ATTR_TXQ_STATS', 'hex'),
        ('NL80211_ATTR_TXQ_LIMIT', 'hex'),
        ('NL80211_ATTR_TXQ_MEMORY_LIMIT', 'hex'),
        ('NL80211_ATTR_TXQ_QUANTUM', 'hex'),
        ('NL80211_ATTR_HE_CAPABILITY', 'hex'),
        ('NL80211_ATTR_FTM_RESPONDER', 'hex'),
        ('NL80211_ATTR_FTM_RESPONDER_STATS', 'hex'),
        ('NL80211_ATTR_TIMEOUT', 'hex'),
        ('NL80211_ATTR_PEER_MEASUREMENTS', 'hex'),
        ('NL80211_ATTR_AIRTIME_WEIGHT', 'hex'),
        ('NL80211_ATTR_STA_TX_POWER_SETTING', 'hex'),
        ('NL80211_ATTR_STA_TX_POWER', 'hex'),
        ('NL80211_ATTR_SAE_PASSWORD', 'hex'),
        ('NL80211_ATTR_TWT_RESPONDER', 'hex'),
        ('NL80211_ATTR_HE_OBSS_PD', 'hex'),
        ('NL80211_ATTR_WIPHY_EDMG_CHANNELS', 'hex'),
        ('NL80211_ATTR_WIPHY_EDMG_BW_CONFIG', 'hex'),
        ('NL80211_ATTR_VLAN_ID', 'hex'),
        ('NL80211_ATTR_HE_BSS_COLOR', 'hex'),
        ('NL80211_ATTR_IFTYPE_AKM_SUITES', 'hex'),
        ('NL80211_ATTR_TID_CONFIG', 'hex'),
        ('NL80211_ATTR_CONTROL_PORT_NO_PREAUTH', 'hex'),
        ('NL80211_ATTR_PMK_LIFETIME', 'hex'),
        ('NL80211_ATTR_PMK_REAUTH_THRESHOLD', 'hex'),
        ('NL80211_ATTR_RECEIVE_MULTICAST', 'hex'),
        ('NL80211_ATTR_WIPHY_FREQ_OFFSET', 'hex'),
        ('NL80211_ATTR_CENTER_FREQ1_OFFSET', 'hex'),
        ('NL80211_ATTR_SCAN_FREQ_KHZ', 'hex'),
        ('NL80211_ATTR_HE_6GHZ_CAPABILITY', 'hex'),
        ('NL80211_ATTR_FILS_DISCOVERY', 'hex'),
        ('NL80211_ATTR_UNSOL_BCAST_PROBE_RESP', 'hex'),
        ('NL80211_ATTR_S1G_CAPABILITY', 'hex'),
        ('NL80211_ATTR_S1G_CAPABILITY_MASK', 'hex'),
        ('NL80211_ATTR_SAE_PWE', 'hex'),
        ('NL80211_ATTR_RECONNECT_REQUESTED', 'hex'),
        ('NL80211_ATTR_SAR_SPEC', 'hex'),
        ('NL80211_ATTR_DISABLE_HE', 'hex'),
        ('NUM_NL80211_ATTR', 'hex'),
    )

    class survey_info(nla):
        prefix = 'NL80211_SURVEY_INFO_'
        nla_map = (
            ('__NL80211_SURVEY_INFO_INVALID', 'none'),
            ('NL80211_SURVEY_INFO_FREQUENCY', 'uint32'),
            ('NL80211_SURVEY_INFO_NOISE', 'uint8'),
            ('NL80211_SURVEY_INFO_IN_USE', 'flag'),
            ('NL80211_SURVEY_INFO_TIME', 'uint64'),
            ('NL80211_SURVEY_INFO_TIME_BUSY', 'uint64'),
            ('NL80211_SURVEY_INFO_TIME_EXT_BUSY', 'uint64'),
            ('NL80211_SURVEY_INFO_TIME_RX', 'uint64'),
            ('NL80211_SURVEY_INFO_TIME_TX', 'uint64'),
            ('NL80211_SURVEY_INFO_TIME_SCAN', 'uint64'),
            ('NL80211_SURVEY_INFO_PAD', 'hex'),
            ('NL80211_SURVEY_INFO_TIME_BSS_RX', 'uint64'),
            ('NL80211_SURVEY_INFO_FREQUENCY_OFFSET', 'hex'),
        )

    class band(nla):
        class bitrate(nla):
            prefix = 'NL80211_BITRATE_ATTR_'
            nla_map = (
                ('__NL80211_BITRATE_ATTR_INVALID', 'hex'),
                ('NL80211_BITRATE_ATTR_RATE', 'uint32'),  # 10x Mbps
                ('NL80211_BITRATE_ATTR_2GHZ_SHORTPREAMBLE', 'flag'),
            )

        class frequency(nla):
            class wmm_rule(nla):
                prefix = 'NL80211_WMMR_'
                nla_map = (
                    ('__NL80211_WMMR_INVALID', 'hex'),
                    ('NL80211_WMMR_CW_MIN', 'uint16'),
                    ('NL80211_WMMR_CW_MAX', 'uint16'),
                    ('NL80211_WMMR_AIFSN', 'uint8'),
                    ('NL80211_WMMR_TXOP', 'uint16'),
                )

            prefix = 'NL80211_FREQUENCY_ATTR_'
            nla_map = (
                ('__NL80211_FREQUENCY_ATTR_INVALID', 'hex'),
                ('NL80211_FREQUENCY_ATTR_FREQ', 'uint32'),
                ('NL80211_FREQUENCY_ATTR_DISABLED', 'flag'),
                ('NL80211_FREQUENCY_ATTR_NO_IR', 'flag'),
                ('__NL80211_FREQUENCY_ATTR_NO_IBSS', 'flag'),
                ('NL80211_FREQUENCY_ATTR_RADAR', 'flag'),
                ('NL80211_FREQUENCY_ATTR_MAX_TX_POWER', 'uint32'),
                ('NL80211_FREQUENCY_ATTR_DFS_STATE', 'uint32'),
                ('NL80211_FREQUENCY_ATTR_DFS_TIME', 'uint32'),
                ('NL80211_FREQUENCY_ATTR_NO_HT40_MINUS', 'flag'),
                ('NL80211_FREQUENCY_ATTR_NO_HT40_PLUS', 'flag'),
                ('NL80211_FREQUENCY_ATTR_NO_80MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_NO_160MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_DFS_CAC_TIME', 'uint32'),
                ('NL80211_FREQUENCY_ATTR_INDOOR_ONLY', 'flag'),
                ('NL80211_FREQUENCY_ATTR_IR_CONCURRENT', 'flag'),
                ('NL80211_FREQUENCY_ATTR_NO_20MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_NO_10MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_WMM', '*wmm_rule'),
                ('NL80211_FREQUENCY_ATTR_NO_HE', 'flag'),
                ('NL80211_FREQUENCY_ATTR_OFFSET', 'uint32'),
                ('NL80211_FREQUENCY_ATTR_1MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_2MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_4MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_8MHZ', 'flag'),
                ('NL80211_FREQUENCY_ATTR_16MHZ', 'flag'),
            )

        class iftype_data(nla):
            class iftype(nla):
                prefix = 'NL80211_IFTYPE_'
                nla_map = (
                    ('NL80211_IFTYPE_UNSPECIFIED', 'flag'),
                    ('NL80211_IFTYPE_ADHOC', 'flag'),
                    ('NL80211_IFTYPE_STATION', 'flag'),
                    ('NL80211_IFTYPE_AP', 'flag'),
                    ('NL80211_IFTYPE_AP_VLAN', 'flag'),
                    ('NL80211_IFTYPE_WDS', 'flag'),
                    ('NL80211_IFTYPE_MONITOR', 'flag'),
                    ('NL80211_IFTYPE_MESH_POINT', 'flag'),
                    ('NL80211_IFTYPE_P2P_CLIENT', 'flag'),
                    ('NL80211_IFTYPE_P2P_GO', 'flag'),
                    ('NL80211_IFTYPE_P2P_DEVICE', 'flag'),
                    ('NL80211_IFTYPE_OCB', 'flag'),
                    ('NL80211_IFTYPE_NAN', 'flag'),
                )

            class mcs_nss(nla):
                '''
                HE Tx/Rx HE MCS NSS Support Field

                C structure::

                struct ieee80211_he_mcs_nss_supp {
                    __le16 rx_mcs_80;
                    __le16 tx_mcs_80;
                    __le16 rx_mcs_160;
                    __le16 tx_mcs_160;
                    __le16 rx_mcs_80p80;
                    __le16 tx_mcs_80p80;
                } __packed;
                '''

                fields = (
                    ('rx_mcs_80', '<H'),
                    ('tx_mcs_80', '<H'),
                    ('rx_mcs_160', '<H'),
                    ('tx_mcs_160', '<H'),
                    ('rx_mcs_80p80', '<H'),
                    ('tx_mcs_80p80', '<H'),
                )

            class he_6ghz_capa(nla):
                '''
                HE 6 GHz band capabilities

                C structure::

                struct ieee80211_he_6ghz_capa {
                    __le16 capa;
                } __packed;
                '''

                fields = (('capa', '<H'),)

            prefix = 'NL80211_BAND_IFTYPE_ATTR_'
            nla_map = (
                ('__NL80211_BAND_IFTYPE_ATTR_INVALID', 'hex'),
                ('NL80211_BAND_IFTYPE_ATTR_IFTYPES', 'iftype'),
                ('NL80211_BAND_IFTYPE_ATTR_HE_CAP_MAC', 'array(uint8)'),
                ('NL80211_BAND_IFTYPE_ATTR_HE_CAP_PHY', 'array(uint8)'),
                ('NL80211_BAND_IFTYPE_ATTR_HE_CAP_MCS_SET', 'mcs_nss'),
                ('NL80211_BAND_IFTYPE_ATTR_HE_CAP_PPE', 'array(uint8)'),
                ('NL80211_BAND_IFTYPE_ATTR_HE_6GHZ_CAPA', 'he_6ghz_capa'),
            )

        class mcs(nla):
            '''
            MCS information

            C structure::

            struct ieee80211_mcs_info {
                u8 rx_mask[IEEE80211_HT_MCS_MASK_LEN];
                __le16 rx_highest;
                u8 tx_params;
                u8 reserved[3];
            } __packed;
            '''

            fields = (
                ('rx_mask', '=10B'),
                ('rx_highest', '<H'),
                ('tx_params', '=B'),
                ('reserved', '=3B'),
            )

        class vht_mcs(nla):
            '''
            VHT MCS information

            C structure::

            struct ieee80211_vht_mcs_info {
                __le16 rx_mcs_map;
                __le16 rx_highest;
                __le16 tx_mcs_map;
                __le16 tx_highest;
            } __packed;
            '''

            fields = (
                ('rx_mcs_map', '<H'),
                ('rx_highest', '<H'),
                ('tx_mcs_map', '<H'),
                ('tx_highest', '<H'),
            )

        prefix = 'NL80211_BAND_ATTR_'
        nla_map = (
            ('__NL80211_BAND_ATTR_INVALID', 'hex'),
            ('NL80211_BAND_ATTR_FREQS', '*frequency'),
            ('NL80211_BAND_ATTR_RATES', '*bitrate'),
            ('NL80211_BAND_ATTR_HT_MCS_SET', 'mcs'),
            ('NL80211_BAND_ATTR_HT_CAPA', 'uint16'),
            ('NL80211_BAND_ATTR_HT_AMPDU_FACTOR', 'uint8'),
            ('NL80211_BAND_ATTR_HT_AMPDU_DENSITY', 'uint8'),
            ('NL80211_BAND_ATTR_VHT_MCS_SET', 'vht_mcs'),
            ('NL80211_BAND_ATTR_VHT_CAPA', 'uint32'),
            ('NL80211_BAND_ATTR_IFTYPE_DATA', '*iftype_data'),
            ('NL80211_BAND_ATTR_EDMG_CHANNELS', 'uint8'),
            ('NL80211_BAND_ATTR_EDMG_BW_CONFIG', 'uint8'),
        )

    class bss(nla):
        class elementsBinary(nla_base):
            def binary_rates(self, offset, length):
                init = offset
                string = ""
                while (offset - init) < length:
                    (byte,) = struct.unpack_from('B', self.data, offset)
                    r = byte & 0x7F
                    if r == BSS_MEMBERSHIP_SELECTOR_VHT_PHY and byte & 0x80:
                        string += "VHT"
                    elif r == BSS_MEMBERSHIP_SELECTOR_HT_PHY and byte & 0x80:
                        string += "HT"
                    else:
                        string += "%d.%d" % (r / 2, 5 * (r & 1))
                    offset += 1
                    string += "%s " % ("*" if byte & 0x80 else "")
                return string

            def binary_tim(self, offset):
                (count, period, bitmapc, bitmap0) = struct.unpack_from(
                    'BBBB', self.data, offset
                )
                return (
                    "DTIM Count {0} DTIM Period {1} Bitmap Control 0x{2} "
                    "Bitmap[0] 0x{3}".format(count, period, bitmapc, bitmap0)
                )

            def _get_cipher_list(self, data):
                ms_oui = bytes((0x00, 0x50, 0xF2))
                ieee80211_oui = bytes((0x00, 0x0F, 0xAC))
                if data[:3] == ms_oui:
                    cipher_list = [
                        "Use group cipher suite",
                        "WEP-40",
                        "TKIP",
                        None,
                        "CCMP",
                        "WEP-104",
                    ]
                elif data[:3] == ieee80211_oui:
                    cipher_list = [
                        "Use group cipher suite",
                        "WEP-40",
                        "TKIP",
                        None,
                        "CCMP",
                        "WEP-104",
                        "AES-128-CMAC",
                        "NO-GROUP",
                        "GCMP",
                    ]
                else:
                    cipher_list = []
                try:
                    return cipher_list[data[3]]
                except IndexError:
                    return data[:4].hex('-', 1)

            def _get_auth_list(self, data):
                ms_oui = bytes((0x00, 0x50, 0xF2))
                ieee80211_oui = bytes((0x00, 0x0F, 0xAC))
                wfa_oui = bytes((0x50, 0x6F, 0x9A))
                if data[:3] == ms_oui:
                    auth_list = [None, "IEEE 802.1X", "PSK"]
                elif data[:3] == ieee80211_oui:
                    auth_list = [
                        None,
                        "IEEE 802.1X",
                        "PSK",
                        "FT/IEEE 802.1X",
                        "FT/PSK",
                        "IEEE 802.1X/SHA-256",
                        "PSK/SHA-256",
                        "TDLS/TPK",
                        "SAE",
                        "FT/SAE",
                        "IEEE 802.1X/SUITE-B",
                        "IEEE 802.1X/SUITE-B-192",
                        "FT/IEEE 802.1X/SHA-384",
                        "FILS/SHA-256",
                        "FILS/SHA-384",
                        "FT/FILS/SHA-256",
                        "FT/FILS/SHA-384",
                        "OWE",
                    ]
                elif data[:3] == wfa_oui:
                    auth_list = [None, "OSEN", "DPP"]
                else:
                    auth_list = []
                try:
                    return auth_list[data[3]]
                except IndexError:
                    return data[:4].hex('-', 1)

            def binary_rsn(self, offset, length, defcipher, defauth):
                data = self.data[offset : offset + length]
                version = data[0] + (data[1] << 8)
                data = data[2:]
                rsn_values = {
                    "version": version,
                    "group_cipher": None,
                    "pairwise_cipher": [],
                    "auth_suites": [],
                    "capabilities": [],
                    "pmkid_ids": None,
                    "group_mgmt_cipher_suite": None,
                }

                if len(data) < 4:
                    rsn_values["group_cipher"] = defcipher
                    rsn_values["pairwise_cipher"] = defcipher
                    return rsn_values

                rsn_values["group_cipher"] = self._get_cipher_list(data)

                data = data[4:]
                if len(data) < 4:
                    rsn_values["pairwise_cipher"] = defcipher
                    return rsn_values

                count = data[0] | (data[1] << 8)
                if 2 + (count * 4) > len(data):
                    # raise Exception(f"* bogus tail data ({count}):")
                    return rsn_values

                data = data[2:]
                for _ in range(count):
                    rsn_values["pairwise_cipher"].append(
                        self._get_cipher_list(data)
                    )
                    data = data[4:]

                if len(data) < 2:
                    rsn_values["auth_suites"] = [defauth]

                count = data[0] | (data[1] << 8)
                if 2 + (count * 4) > len(data):
                    # raise Exception(f"* bogus tail data ({count}):")
                    return rsn_values

                data = data[2:]
                for _ in range(count):
                    rsn_values["auth_suites"].append(self._get_auth_list(data))
                    data = data[4:]

                if len(data) >= 2:
                    capabilities = []
                    capa = data[0] | (data[1] << 8)
                    data = data[2:]
                    if capa & 0x0001:
                        capabilities.append("PreAuth")
                    if capa & 0x0002:
                        capabilities.append("NoPairwise")
                    capabilities.append(
                        [
                            "1-PTKSA-RC",
                            "2-PTKSA-RC",
                            "4-PTKSA-RC",
                            "16-PTKSA-RC",
                        ][(capa & 0x000C) >> 2]
                    )
                    capabilities.append(
                        [
                            "1-GTKSA-RC",
                            "2-GTKSA-RC",
                            "4-GTKSA-RC",
                            "16-GTKSA-RC",
                        ][(capa & 0x0030) >> 4]
                    )
                    if capa & 0x0040:
                        capabilities.append("MFP-required")
                    if capa & 0x0080:
                        capabilities.append("MFP-capable")
                    if capa & 0x0200:
                        capabilities.append("Peerkey-enabled")
                    if capa & 0x0400:
                        capabilities.append("SPP-AMSDU-capable")
                    if capa & 0x0800:
                        capabilities.append("SPP-AMSDU-required")
                    if capa & 0x2000:
                        capabilities.append("Extended-Key-ID")
                    rsn_values["capabilities"] = capabilities

                if len(data) >= 2:
                    pmkid_count = data[0] | (data[1] << 8)
                    if len(data) < 2 + 16 * pmkid_count:
                        # raise Exception("invalid")
                        return rsn_values
                    data = data[2:]
                    for _ in range(pmkid_count):
                        rsn_values["pmkid_ids"].append(data[:16])
                        data = data[16:]

                if len(data) >= 4:
                    rsn_values["group_mgmt_cipher_suite"] = (
                        self._get_cipher_list(data)
                    )
                    data = data[4:]

                return rsn_values

            def binary_ht_operation(self, offset, length):
                data = self.data[offset : offset + length]
                ht_operation = {}
                ht_operation["PRIMARY_CHANNEL"] = data[0]
                ht_operation["SECONDARY_CHANNEL"] = data[1] & 0x3
                try:
                    ht_operation["CHANNEL_WIDTH"] = [
                        BSS_HT_OPER_CHAN_WIDTH_20,
                        BSS_HT_OPER_CHAN_WIDTH_20_OR_40,
                    ][(data[1] & 0x4) >> 2]
                except IndexError:
                    ht_operation["CHANNEL_WIDTH"] = None
                try:
                    ht_operation["HT_PROTECTION"] = [
                        "no",
                        "nonmember",
                        "20 MHz",
                        "non-HT mixed",
                    ][data[2] & 0x3]
                except IndexError:
                    ht_operation["HT_PROTECTION"] = None

                ht_operation.update(
                    {
                        "RIFS": (data[1] & 0x8) >> 3,
                        "NON_GF_PRESENT": (data[2] & 0x4) >> 2,
                        "OBSS_NON_GF_PRESENT": (data[2] & 0x10) >> 4,
                        "DUAL_BEACON": (data[4] & 0x40) >> 6,
                        "DUAL_CTS_PROTECTION": (data[4] & 0x80) >> 7,
                        "STBC_BEACON": data[5] & 0x1,
                        "L_SIG_TXOP_PROT": (data[5] & 0x2) >> 1,
                        "PCO_ACTIVE": (data[5] & 0x4) >> 2,
                        "PCO_PHASE": (data[5] & 0x8) >> 3,
                    }
                )
                return ht_operation

            def binary_vht_operation(self, offset, length):
                data = self.data[offset : offset + length]
                vht_operation = {
                    "CENTER_FREQ_SEG_1": data[1],
                    "CENTER_FREQ_SEG_2": data[1],
                    "VHT_BASIC_MCS_SET": (data[4], data[3]),
                }
                try:
                    vht_operation["CHANNEL_WIDTH"] = [
                        BSS_VHT_OPER_CHAN_WIDTH_20_OR_40,
                        BSS_VHT_OPER_CHAN_WIDTH_80,
                        BSS_VHT_OPER_CHAN_WIDTH_80P80,
                        BSS_VHT_OPER_CHAN_WIDTH_160,
                    ][data[0]]
                except IndexError:
                    vht_operation["CHANNEL_WIDTH"] = None

                return vht_operation

            def decode_nlas(self):
                return

            def decode(self):
                nla_base.decode(self)

                self.value = {}

                init = offset = self.offset + 4

                while (offset - init) < (self.length - 4):
                    (msg_type, length) = struct.unpack_from(
                        'BB', self.data, offset
                    )
                    if msg_type == NL80211_BSS_ELEMENTS_SSID:
                        (self.value["SSID"],) = struct.unpack_from(
                            '%is' % length, self.data, offset + 2
                        )

                    if msg_type == NL80211_BSS_ELEMENTS_SUPPORTED_RATES:
                        supported_rates = self.binary_rates(offset + 2, length)
                        self.value["SUPPORTED_RATES"] = supported_rates

                    if msg_type == NL80211_BSS_ELEMENTS_CHANNEL:
                        (channel,) = struct.unpack_from(
                            'B', self.data, offset + 2
                        )
                        self.value["CHANNEL"] = channel

                    if msg_type == NL80211_BSS_ELEMENTS_TIM:
                        self.value["TRAFFIC INDICATION MAP"] = self.binary_tim(
                            offset + 2
                        )

                    if msg_type == NL80211_BSS_ELEMENTS_RSN:
                        self.value["RSN"] = self.binary_rsn(
                            offset + 2, length, "CCMP", "IEEE 802.1X"
                        )

                    if msg_type == NL80211_BSS_ELEMENTS_EXTENDED_RATE:
                        extended_rates = self.binary_rates(offset + 2, length)
                        self.value["EXTENDED_RATES"] = extended_rates

                    if msg_type == NL80211_BSS_ELEMENTS_VENDOR:
                        # There may be multiple vendor IEs, create a list
                        if "VENDOR" not in self.value.keys():
                            self.value["VENDOR"] = []
                        (vendor_ie,) = struct.unpack_from(
                            '%is' % length, self.data, offset + 2
                        )
                        self.value["VENDOR"].append(vendor_ie)

                    if msg_type == NL80211_BSS_ELEMENTS_HT_OPERATION:
                        self.value["HT_OPERATION"] = self.binary_ht_operation(
                            offset + 2, length
                        )

                    if msg_type == NL80211_BSS_ELEMENTS_VHT_OPERATION:
                        self.value["VHT_OPERATION"] = (
                            self.binary_vht_operation(offset + 2, length)
                        )

                    offset += length + 2

        class TSF(nla_base):
            """Timing Synchronization Function"""

            def decode(self):
                nla_base.decode(self)

                offset = self.offset + 4
                self.value = {}
                (tsf,) = struct.unpack_from('Q', self.data, offset)
                self.value["VALUE"] = tsf
                # TSF is in microseconds
                self.value["TIME"] = datetime.timedelta(microseconds=tsf)

        class SignalMBM(nla_base):
            def decode(self):
                nla_base.decode(self)
                offset = self.offset + 4
                self.value = {}
                (ss,) = struct.unpack_from('i', self.data, offset)
                self.value["VALUE"] = ss
                self.value["SIGNAL_STRENGTH"] = {
                    "VALUE": ss / 100.0,
                    "UNITS": "dBm",
                }

        class capability(nla_base):
            # iw scan.c
            WLAN_CAPABILITY_ESS = 1 << 0
            WLAN_CAPABILITY_IBSS = 1 << 1
            WLAN_CAPABILITY_CF_POLLABLE = 1 << 2
            WLAN_CAPABILITY_CF_POLL_REQUEST = 1 << 3
            WLAN_CAPABILITY_PRIVACY = 1 << 4
            WLAN_CAPABILITY_SHORT_PREAMBLE = 1 << 5
            WLAN_CAPABILITY_PBCC = 1 << 6
            WLAN_CAPABILITY_CHANNEL_AGILITY = 1 << 7
            WLAN_CAPABILITY_SPECTRUM_MGMT = 1 << 8
            WLAN_CAPABILITY_QOS = 1 << 9
            WLAN_CAPABILITY_SHORT_SLOT_TIME = 1 << 10
            WLAN_CAPABILITY_APSD = 1 << 11
            WLAN_CAPABILITY_RADIO_MEASURE = 1 << 12
            WLAN_CAPABILITY_DSSS_OFDM = 1 << 13
            WLAN_CAPABILITY_DEL_BACK = 1 << 14
            WLAN_CAPABILITY_IMM_BACK = 1 << 15

            #            def decode_nlas(self):
            #                return

            def decode(self):
                nla_base.decode(self)

                offset = self.offset + 4
                self.value = {}
                (capa,) = struct.unpack_from('H', self.data, offset)
                self.value["VALUE"] = capa

                s = []
                if capa & self.WLAN_CAPABILITY_ESS:
                    s.append("ESS")
                if capa & self.WLAN_CAPABILITY_IBSS:
                    s.append("IBSS")
                if capa & self.WLAN_CAPABILITY_CF_POLLABLE:
                    s.append("CfPollable")
                if capa & self.WLAN_CAPABILITY_CF_POLL_REQUEST:
                    s.append("CfPollReq")
                if capa & self.WLAN_CAPABILITY_PRIVACY:
                    s.append("Privacy")
                if capa & self.WLAN_CAPABILITY_SHORT_PREAMBLE:
                    s.append("ShortPreamble")
                if capa & self.WLAN_CAPABILITY_PBCC:
                    s.append("PBCC")
                if capa & self.WLAN_CAPABILITY_CHANNEL_AGILITY:
                    s.append("ChannelAgility")
                if capa & self.WLAN_CAPABILITY_SPECTRUM_MGMT:
                    s.append("SpectrumMgmt")
                if capa & self.WLAN_CAPABILITY_QOS:
                    s.append("QoS")
                if capa & self.WLAN_CAPABILITY_SHORT_SLOT_TIME:
                    s.append("ShortSlotTime")
                if capa & self.WLAN_CAPABILITY_APSD:
                    s.append("APSD")
                if capa & self.WLAN_CAPABILITY_RADIO_MEASURE:
                    s.append("RadioMeasure")
                if capa & self.WLAN_CAPABILITY_DSSS_OFDM:
                    s.append("DSSS-OFDM")
                if capa & self.WLAN_CAPABILITY_DEL_BACK:
                    s.append("DelayedBACK")
                if capa & self.WLAN_CAPABILITY_IMM_BACK:
                    s.append("ImmediateBACK")

                self.value['CAPABILITIES'] = " ".join(s)

        prefix = 'NL80211_BSS_'
        nla_map = (
            ('__NL80211_BSS_INVALID', 'hex'),
            ('NL80211_BSS_BSSID', 'hex'),
            ('NL80211_BSS_FREQUENCY', 'uint32'),
            ('NL80211_BSS_TSF', 'TSF'),
            ('NL80211_BSS_BEACON_INTERVAL', 'uint16'),
            ('NL80211_BSS_CAPABILITY', 'capability'),
            ('NL80211_BSS_INFORMATION_ELEMENTS', 'elementsBinary'),
            ('NL80211_BSS_SIGNAL_MBM', 'SignalMBM'),
            ('NL80211_BSS_SIGNAL_UNSPEC', 'uint8'),
            ('NL80211_BSS_STATUS', 'uint32'),
            ('NL80211_BSS_SEEN_MS_AGO', 'uint32'),
            ('NL80211_BSS_BEACON_IES', 'elementsBinary'),
            ('NL80211_BSS_CHAN_WIDTH', 'uint32'),
            ('NL80211_BSS_BEACON_TSF', 'uint64'),
            ('NL80211_BSS_PRESP_DATA', 'hex'),
            ('NL80211_BSS_MAX', 'hex'),
        )

    class reg_rule(nla):
        prefix = 'NL80211_ATTR_'
        nla_map = (
            ('__NL80211_REG_RULE_ATTR_INVALID', 'hex'),
            ('NL80211_ATTR_REG_RULE_FLAGS', 'uint32'),
            ('NL80211_ATTR_FREQ_RANGE_START', 'uint32'),
            ('NL80211_ATTR_FREQ_RANGE_END', 'uint32'),
            ('NL80211_ATTR_FREQ_RANGE_MAX_BW', 'uint32'),
            ('NL80211_ATTR_POWER_RULE_MAX_ANT_GAIN', 'uint32'),
            ('NL80211_ATTR_POWER_RULE_MAX_EIRP', 'uint32'),
            ('NL80211_ATTR_DFS_CAC_TIME', 'uint32'),
        )

    class STAInfo(nla):
        class STAFlags(nla_base):
            '''
            Decode the flags that may be set.
            See nl80211.h: struct nl80211_sta_flag_update,
            NL80211_STA_INFO_STA_FLAGS
            '''

            def decode_nlas(self):
                return

            def decode(self):
                nla_base.decode(self)
                self.value = {}
                self.value["AUTHORIZED"] = False
                self.value["SHORT_PREAMBLE"] = False
                self.value["WME"] = False
                self.value["MFP"] = False
                self.value["AUTHENTICATED"] = False
                self.value["TDLS_PEER"] = False
                self.value["ASSOCIATED"] = False

                offset = self.offset + 4
                mask, set_ = struct.unpack_from('II', self.data, offset)

                if mask & NL80211_STA_FLAG_AUTHORIZED:
                    if set_ & NL80211_STA_FLAG_AUTHORIZED:
                        self.value["AUTHORIZED"] = True

                if mask & NL80211_STA_FLAG_SHORT_PREAMBLE:
                    if set_ & NL80211_STA_FLAG_SHORT_PREAMBLE:
                        self.value["SHORT_PREAMBLE"] = True

                if mask & NL80211_STA_FLAG_WME:
                    if set_ & NL80211_STA_FLAG_WME:
                        self.value["WME"] = True

                if mask & NL80211_STA_FLAG_MFP:
                    if set_ & NL80211_STA_FLAG_MFP:
                        self.value["MFP"] = True

                if mask & NL80211_STA_FLAG_AUTHENTICATED:
                    if set_ & NL80211_STA_FLAG_AUTHENTICATED:
                        self.value["AUTHENTICATED"] = True

                if mask & NL80211_STA_FLAG_TDLS_PEER:
                    if set_ & NL80211_STA_FLAG_TDLS_PEER:
                        self.value["TDLS_PEER"] = True

                if mask & NL80211_STA_FLAG_ASSOCIATED:
                    if set_ & NL80211_STA_FLAG_ASSOCIATED:
                        self.value["ASSOCIATED"] = True

        class rate_info(nla):
            '''
            Decode the data rate information
            See nl80211.h: enum nl80211_sta_info,
            NL80211_STA_INFO_TX_BITRATE
            NL80211_STA_INFO_RX_BITRATE
            '''

            prefix = "NL80211_RATE_INFO_"
            nla_map = (
                ('__NL80211_RATE_INFO_INVALID', 'hex'),
                ('NL80211_RATE_INFO_BITRATE', 'uint16'),
                ('NL80211_RATE_INFO_MCS', 'uint8'),
                ('NL80211_RATE_INFO_40_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_SHORT_GI', 'flag'),
                ('NL80211_RATE_INFO_BITRATE32', 'uint32'),
                ('NL80211_RATE_INFO_VHT_MCS', 'uint8'),
                ('NL80211_RATE_INFO_VHT_NSS', 'uint8'),
                ('NL80211_RATE_INFO_80_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_80P80_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_160_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_10_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_5_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_HE_MCS', 'uint8'),
                ('NL80211_RATE_INFO_HE_NSS', 'uint8'),
                ('NL80211_RATE_INFO_HE_GI', 'uint8'),
                ('NL80211_RATE_INFO_HE_DCM', 'uint8'),
                ('NL80211_RATE_INFO_HE_RU_ALLOC', 'uint8'),
                ('NL80211_RATE_INFO_320_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_EHT_MCS', 'uint8'),
                ('NL80211_RATE_INFO_EHT_NSS', 'uint8'),
                ('NL80211_RATE_INFO_EHT_GI', 'uint8'),
                ('NL80211_RATE_INFO_EHT_RU_ALLOC', 'uint8'),
                ('NL80211_RATE_INFO_S1G_MCS', 'uint8'),
                ('NL80211_RATE_INFO_S1G_NSS', 'uint8'),
                ('NL80211_RATE_INFO_1_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_2_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_4_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_8_MHZ_WIDTH', 'flag'),
                ('NL80211_RATE_INFO_16_MHZ_WIDTH', 'flag'),
            )

        class bss_param(nla):
            '''
            Decode the BSS information
            See nl80211.h: enum nl80211_sta_bss_param,
            NL80211_STA_INFO_BSS_PARAM
            '''

            prefix = "NL80211_STA_BSS_PARAM_"
            nla_map = (
                ('__NL80211_STA_BSS_PARAM_INVALID', 'hex'),
                ('NL80211_STA_BSS_PARAM_CTS_PROT', 'flag'),
                ('NL80211_STA_BSS_PARAM_SHORT_PREAMBLE', 'flag'),
                ('NL80211_STA_BSS_PARAM_SHORT_SLOT_TIME', 'flag'),
                ('NL80211_STA_BSS_PARAM_DTIM_PERIOD', 'uint8'),
                ('NL80211_STA_BSS_PARAM_BEACON_INTERVAL', 'uint16'),
            )

        prefix = 'NL80211_STA_INFO_'
        nla_map = (
            ('__NL80211_STA_INFO_INVALID', 'hex'),
            ('NL80211_STA_INFO_INACTIVE_TIME', 'uint32'),
            ('NL80211_STA_INFO_RX_BYTES', 'uint32'),
            ('NL80211_STA_INFO_TX_BYTES', 'uint32'),
            ('NL80211_STA_INFO_LLID', 'uint16'),
            ('NL80211_STA_INFO_PLID', 'uint16'),
            ('NL80211_STA_INFO_PLINK_STATE', 'uint8'),
            ('NL80211_STA_INFO_SIGNAL', 'int8'),
            ('NL80211_STA_INFO_TX_BITRATE', 'rate_info'),
            ('NL80211_STA_INFO_RX_PACKETS', 'uint32'),
            ('NL80211_STA_INFO_TX_PACKETS', 'uint32'),
            ('NL80211_STA_INFO_TX_RETRIES', 'uint32'),
            ('NL80211_STA_INFO_TX_FAILED', 'uint32'),
            ('NL80211_STA_INFO_SIGNAL_AVG', 'int8'),
            ('NL80211_STA_INFO_RX_BITRATE', 'rate_info'),
            ('NL80211_STA_INFO_BSS_PARAM', 'bss_param'),
            ('NL80211_STA_INFO_CONNECTED_TIME', 'uint32'),
            ('NL80211_STA_INFO_STA_FLAGS', 'STAFlags'),
            ('NL80211_STA_INFO_BEACON_LOSS', 'uint32'),
            ('NL80211_STA_INFO_T_OFFSET', 'int64'),
            ('NL80211_STA_INFO_LOCAL_PM', 'hex'),
            ('NL80211_STA_INFO_PEER_PM', 'hex'),
            ('NL80211_STA_INFO_NONPEER_PM', 'hex'),
            ('NL80211_STA_INFO_RX_BYTES64', 'uint64'),
            ('NL80211_STA_INFO_TX_BYTES64', 'uint64'),
            ('NL80211_STA_INFO_CHAIN_SIGNAL', '*int8'),
            ('NL80211_STA_INFO_CHAIN_SIGNAL_AVG', '*int8'),
            ('NL80211_STA_INFO_EXPECTED_THROUGHPUT', 'uint32'),
            ('NL80211_STA_INFO_RX_DROP_MISC', 'uint32'),
            ('NL80211_STA_INFO_BEACON_RX', 'uint64'),
            ('NL80211_STA_INFO_BEACON_SIGNAL_AVG', 'int8'),
            ('NL80211_STA_INFO_TID_STATS', 'hex'),
            ('NL80211_STA_INFO_RX_DURATION', 'uint64'),
            ('NL80211_STA_INFO_PAD', 'hex'),
            ('NL80211_STA_INFO_MAX', 'hex'),
        )

    class supported_commands(nla_base):
        '''
        Supported commands format

        NLA structure header::
        +++++++++++++++++++++++
        | uint16_t | uint16_t |
        |  length  | NLA type |
        +++++++++++++++++++++++

        followed by multiple command entries::
        ++++++++++++++++++++++++++++++++++
        | uint16_t | uint16_t | uint32_t |
        |   type   |  index   |   cmd    |
        ++++++++++++++++++++++++++++++++++
        '''

        def decode(self):
            nla_base.decode(self)
            self.value = []

            # Skip the first four bytes: NLA length and NLA type
            length = self.length - 4
            offset = self.offset + 4
            while length > 0:
                (msg_type, index, cmd_index) = struct.unpack_from(
                    'HHI', self.data, offset
                )
                length -= 8
                offset += 8

                # Lookup for command name or assign a default name
                name = NL80211_VALUES.get(
                    cmd_index, 'NL80211_CMD_{}'.format(cmd_index)
                )
                self.value.append(name)

    class cipher_suites(nla_base):
        '''
        Cipher suites format

        NLA structure header::
        +++++++++++++++++++++++
        | uint16_t | uint16_t |
        |  length  | NLA type |
        +++++++++++++++++++++++

        followed by multiple entries::
        ++++++++++++
        | uint32_t |
        |  cipher  |
        ++++++++++++
        '''

        def decode(self):
            nla_base.decode(self)
            self.value = []

            # Skip the first four bytes: NLA length and NLA type
            length = self.length - 4
            offset = self.offset + 4
            while length > 0:
                (cipher,) = struct.unpack_from('<I', self.data, offset)
                length -= 4
                offset += 4

                # Lookup for cipher name or assign a default name
                name = WLAN_CIPHER_SUITE_VALUES.get(
                    cipher, 'WLAN_CIPHER_SUITE_{:08X}'.format(cipher)
                )
                self.value.append(name)

    class supported_iftypes(nla_base):
        '''
        Supported iftypes format

        NLA structure header::
        +++++++++++++++++++++++
        | uint16_t | uint16_t |
        |  length  | NLA type |
        +++++++++++++++++++++++

        followed by multiple iftype entries::
        +++++++++++++++++++++++
        | uint16_t | uint16_t |
        |  length  |  iftype  |
        +++++++++++++++++++++++
        '''

        def decode(self):
            nla_base.decode(self)
            self.value = []

            # Skip the first four bytes: NLA length and NLA type
            length = self.length - 4
            offset = self.offset + 4
            while length > 0:
                (iflen, iftype) = struct.unpack_from('<HH', self.data, offset)
                length -= 4
                offset += 4

                # Lookup for iftype name or assign a default name
                name = IFTYPE_VALUES.get(
                    iftype, 'NL80211_IFTYPE_{}'.format(iftype)
                )
                self.value.append(name)


class MarshalNl80211(Marshal):
    msg_map = {
        NL80211_CMD_UNSPEC: nl80211cmd,
        NL80211_CMD_GET_WIPHY: nl80211cmd,
        NL80211_CMD_SET_WIPHY: nl80211cmd,
        NL80211_CMD_NEW_WIPHY: nl80211cmd,
        NL80211_CMD_DEL_WIPHY: nl80211cmd,
        NL80211_CMD_GET_INTERFACE: nl80211cmd,
        NL80211_CMD_SET_INTERFACE: nl80211cmd,
        NL80211_CMD_NEW_INTERFACE: nl80211cmd,
        NL80211_CMD_DEL_INTERFACE: nl80211cmd,
        NL80211_CMD_GET_KEY: nl80211cmd,
        NL80211_CMD_SET_KEY: nl80211cmd,
        NL80211_CMD_NEW_KEY: nl80211cmd,
        NL80211_CMD_DEL_KEY: nl80211cmd,
        NL80211_CMD_GET_BEACON: nl80211cmd,
        NL80211_CMD_SET_BEACON: nl80211cmd,
        NL80211_CMD_START_AP: nl80211cmd,
        NL80211_CMD_NEW_BEACON: nl80211cmd,
        NL80211_CMD_STOP_AP: nl80211cmd,
        NL80211_CMD_DEL_BEACON: nl80211cmd,
        NL80211_CMD_GET_STATION: nl80211cmd,
        NL80211_CMD_SET_STATION: nl80211cmd,
        NL80211_CMD_NEW_STATION: nl80211cmd,
        NL80211_CMD_DEL_STATION: nl80211cmd,
        NL80211_CMD_GET_MPATH: nl80211cmd,
        NL80211_CMD_SET_MPATH: nl80211cmd,
        NL80211_CMD_NEW_MPATH: nl80211cmd,
        NL80211_CMD_DEL_MPATH: nl80211cmd,
        NL80211_CMD_SET_BSS: nl80211cmd,
        NL80211_CMD_SET_REG: nl80211cmd,
        NL80211_CMD_REQ_SET_REG: nl80211cmd,
        NL80211_CMD_GET_MESH_CONFIG: nl80211cmd,
        NL80211_CMD_SET_MESH_CONFIG: nl80211cmd,
        NL80211_CMD_SET_MGMT_EXTRA_IE: nl80211cmd,
        NL80211_CMD_GET_REG: nl80211cmd,
        NL80211_CMD_GET_SCAN: nl80211cmd,
        NL80211_CMD_TRIGGER_SCAN: nl80211cmd,
        NL80211_CMD_NEW_SCAN_RESULTS: nl80211cmd,
        NL80211_CMD_SCAN_ABORTED: nl80211cmd,
        NL80211_CMD_REG_CHANGE: nl80211cmd,
        NL80211_CMD_AUTHENTICATE: nl80211cmd,
        NL80211_CMD_ASSOCIATE: nl80211cmd,
        NL80211_CMD_DEAUTHENTICATE: nl80211cmd,
        NL80211_CMD_DISASSOCIATE: nl80211cmd,
        NL80211_CMD_MICHAEL_MIC_FAILURE: nl80211cmd,
        NL80211_CMD_REG_BEACON_HINT: nl80211cmd,
        NL80211_CMD_JOIN_IBSS: nl80211cmd,
        NL80211_CMD_LEAVE_IBSS: nl80211cmd,
        NL80211_CMD_TESTMODE: nl80211cmd,
        NL80211_CMD_CONNECT: nl80211cmd,
        NL80211_CMD_ROAM: nl80211cmd,
        NL80211_CMD_DISCONNECT: nl80211cmd,
        NL80211_CMD_SET_WIPHY_NETNS: nl80211cmd,
        NL80211_CMD_GET_SURVEY: nl80211cmd,
        NL80211_CMD_NEW_SURVEY_RESULTS: nl80211cmd,
        NL80211_CMD_SET_PMKSA: nl80211cmd,
        NL80211_CMD_DEL_PMKSA: nl80211cmd,
        NL80211_CMD_FLUSH_PMKSA: nl80211cmd,
        NL80211_CMD_REMAIN_ON_CHANNEL: nl80211cmd,
        NL80211_CMD_CANCEL_REMAIN_ON_CHANNEL: nl80211cmd,
        NL80211_CMD_SET_TX_BITRATE_MASK: nl80211cmd,
        NL80211_CMD_REGISTER_FRAME: nl80211cmd,
        NL80211_CMD_REGISTER_ACTION: nl80211cmd,
        NL80211_CMD_FRAME: nl80211cmd,
        NL80211_CMD_ACTION: nl80211cmd,
        NL80211_CMD_FRAME_TX_STATUS: nl80211cmd,
        NL80211_CMD_ACTION_TX_STATUS: nl80211cmd,
        NL80211_CMD_SET_POWER_SAVE: nl80211cmd,
        NL80211_CMD_GET_POWER_SAVE: nl80211cmd,
        NL80211_CMD_SET_CQM: nl80211cmd,
        NL80211_CMD_NOTIFY_CQM: nl80211cmd,
        NL80211_CMD_SET_CHANNEL: nl80211cmd,
        NL80211_CMD_SET_WDS_PEER: nl80211cmd,
        NL80211_CMD_FRAME_WAIT_CANCEL: nl80211cmd,
        NL80211_CMD_JOIN_MESH: nl80211cmd,
        NL80211_CMD_LEAVE_MESH: nl80211cmd,
        NL80211_CMD_UNPROT_DEAUTHENTICATE: nl80211cmd,
        NL80211_CMD_UNPROT_DISASSOCIATE: nl80211cmd,
        NL80211_CMD_NEW_PEER_CANDIDATE: nl80211cmd,
        NL80211_CMD_GET_WOWLAN: nl80211cmd,
        NL80211_CMD_SET_WOWLAN: nl80211cmd,
        NL80211_CMD_START_SCHED_SCAN: nl80211cmd,
        NL80211_CMD_STOP_SCHED_SCAN: nl80211cmd,
        NL80211_CMD_SCHED_SCAN_RESULTS: nl80211cmd,
        NL80211_CMD_SCHED_SCAN_STOPPED: nl80211cmd,
        NL80211_CMD_SET_REKEY_OFFLOAD: nl80211cmd,
        NL80211_CMD_PMKSA_CANDIDATE: nl80211cmd,
        NL80211_CMD_TDLS_OPER: nl80211cmd,
        NL80211_CMD_TDLS_MGMT: nl80211cmd,
        NL80211_CMD_UNEXPECTED_FRAME: nl80211cmd,
        NL80211_CMD_PROBE_CLIENT: nl80211cmd,
        NL80211_CMD_REGISTER_BEACONS: nl80211cmd,
        NL80211_CMD_UNEXPECTED_4ADDR_FRAME: nl80211cmd,
        NL80211_CMD_SET_NOACK_MAP: nl80211cmd,
        NL80211_CMD_CH_SWITCH_NOTIFY: nl80211cmd,
        NL80211_CMD_START_P2P_DEVICE: nl80211cmd,
        NL80211_CMD_STOP_P2P_DEVICE: nl80211cmd,
        NL80211_CMD_CONN_FAILED: nl80211cmd,
        NL80211_CMD_SET_MCAST_RATE: nl80211cmd,
        NL80211_CMD_SET_MAC_ACL: nl80211cmd,
        NL80211_CMD_RADAR_DETECT: nl80211cmd,
        NL80211_CMD_GET_PROTOCOL_FEATURES: nl80211cmd,
        NL80211_CMD_UPDATE_FT_IES: nl80211cmd,
        NL80211_CMD_FT_EVENT: nl80211cmd,
        NL80211_CMD_CRIT_PROTOCOL_START: nl80211cmd,
        NL80211_CMD_CRIT_PROTOCOL_STOP: nl80211cmd,
        NL80211_CMD_GET_COALESCE: nl80211cmd,
        NL80211_CMD_SET_COALESCE: nl80211cmd,
        NL80211_CMD_CHANNEL_SWITCH: nl80211cmd,
        NL80211_CMD_VENDOR: nl80211cmd,
        NL80211_CMD_SET_QOS_MAP: nl80211cmd,
        NL80211_CMD_ADD_TX_TS: nl80211cmd,
        NL80211_CMD_DEL_TX_TS: nl80211cmd,
        NL80211_CMD_GET_MPP: nl80211cmd,
        NL80211_CMD_JOIN_OCB: nl80211cmd,
        NL80211_CMD_LEAVE_OCB: nl80211cmd,
        NL80211_CMD_CH_SWITCH_STARTED_NOTIFY: nl80211cmd,
        NL80211_CMD_TDLS_CHANNEL_SWITCH: nl80211cmd,
        NL80211_CMD_TDLS_CANCEL_CHANNEL_SWITCH: nl80211cmd,
        NL80211_CMD_WIPHY_REG_CHANGE: nl80211cmd,
    }

    def fix_message(self, msg):
        try:
            msg['event'] = NL80211_VALUES[msg['cmd']]
        except Exception:
            pass


class NL80211(GenericNetlinkSocket):
    def __init__(self, *args, **kwargs):
        GenericNetlinkSocket.__init__(self, *args, **kwargs)
        self.marshal = MarshalNl80211()

    def bind(self, groups=0, **kwarg):
        GenericNetlinkSocket.bind(
            self, NL80211_GENL_NAME, nl80211cmd, groups, None, **kwarg
        )
