'''
devlink module
==============
'''

from pyroute2.common import map_namespace
from pyroute2.netlink import genlmsg, nla
from pyroute2.netlink.generic import GenericNetlinkSocket
from pyroute2.netlink.nlsocket import Marshal

# devlink commands
DEVLINK_CMD_UNSPEC = 0
DEVLINK_CMD_GET = 1
DEVLINK_CMD_SET = 2
DEVLINK_CMD_NEW = 3
DEVLINK_CMD_DEL = 4
DEVLINK_CMD_PORT_GET = 5
DEVLINK_CMD_PORT_SET = 6
DEVLINK_CMD_PORT_NEW = 7
DEVLINK_CMD_PORT_DEL = 8
DEVLINK_CMD_PORT_SPLIT = 9
DEVLINK_CMD_PORT_UNSPLIT = 10
DEVLINK_CMD_SB_GET = 11
DEVLINK_CMD_SB_SET = 12
DEVLINK_CMD_SB_NEW = 13
DEVLINK_CMD_SB_DEL = 14
DEVLINK_CMD_SB_POOL_GET = 15
DEVLINK_CMD_SB_POOL_SET = 16
DEVLINK_CMD_SB_POOL_NEW = 17
DEVLINK_CMD_SB_POOL_DEL = 18
DEVLINK_CMD_SB_PORT_POOL_GET = 19
DEVLINK_CMD_SB_PORT_POOL_SET = 20
DEVLINK_CMD_SB_PORT_POOL_NEW = 21
DEVLINK_CMD_SB_PORT_POOL_DEL = 22
DEVLINK_CMD_SB_TC_POOL_BIND_GET = 23
DEVLINK_CMD_SB_TC_POOL_BIND_SET = 24
DEVLINK_CMD_SB_TC_POOL_BIND_NEW = 25
DEVLINK_CMD_SB_TC_POOL_BIND_DEL = 26
DEVLINK_CMD_SB_OCC_SNAPSHOT = 27
DEVLINK_CMD_SB_OCC_MAX_CLEAR = 28
DEVLINK_CMD_ESWITCH_GET = 29
DEVLINK_CMD_ESWITCH_SET = 30
DEVLINK_CMD_DPIPE_TABLE_GET = 31
DEVLINK_CMD_DPIPE_ENTRIES_GET = 32
DEVLINK_CMD_DPIPE_HEADERS_GET = 33
DEVLINK_CMD_DPIPE_TABLE_COUNTERS_SET = 34
DEVLINK_CMD_RESOURCE_SET = 35
DEVLINK_CMD_RESOURCE_DUMP = 36
DEVLINK_CMD_RELOAD = 37
DEVLINK_CMD_PARAM_GET = 38
DEVLINK_CMD_PARAM_SET = 39
DEVLINK_CMD_PARAM_NEW = 40
DEVLINK_CMD_PARAM_DEL = 41
DEVLINK_CMD_REGION_GET = 42
DEVLINK_CMD_REGION_SET = 43
DEVLINK_CMD_REGION_NEW = 44
DEVLINK_CMD_REGION_DEL = 45
DEVLINK_CMD_REGION_READ = 46
DEVLINK_CMD_PORT_PARAM_GET = 47
DEVLINK_CMD_PORT_PARAM_SET = 48
DEVLINK_CMD_PORT_PARAM_NEW = 49
DEVLINK_CMD_PORT_PARAM_DEL = 50
DEVLINK_CMD_INFO_GET = 51
DEVLINK_CMD_HEALTH_REPORTER_GET = 52
DEVLINK_CMD_HEALTH_REPORTER_SET = 53
DEVLINK_CMD_HEALTH_REPORTER_RECOVER = 54
DEVLINK_CMD_HEALTH_REPORTER_DIAGNOSE = 55
DEVLINK_CMD_HEALTH_REPORTER_DUMP_GET = 56
DEVLINK_CMD_HEALTH_REPORTER_DUMP_CLEAR = 57
DEVLINK_CMD_FLASH_UPDATE = 58
DEVLINK_CMD_FLASH_UPDATE_END = 59
DEVLINK_CMD_FLASH_UPDATE_STATUS = 60
DEVLINK_CMD_TRAP_GET = 61
DEVLINK_CMD_TRAP_SET = 62
DEVLINK_CMD_TRAP_NEW = 63
DEVLINK_CMD_TRAP_DEL = 64
DEVLINK_CMD_TRAP_GROUP_GET = 65
DEVLINK_CMD_TRAP_GROUP_SET = 66
DEVLINK_CMD_TRAP_GROUP_NEW = 67
DEVLINK_CMD_TRAP_GROUP_DEL = 68
DEVLINK_CMD_TRAP_POLICER_GET = 69
DEVLINK_CMD_TRAP_POLICER_SET = 70
DEVLINK_CMD_TRAP_POLICER_NEW = 71
DEVLINK_CMD_TRAP_POLICER_DEL = 72
DEVLINK_CMD_MAX = DEVLINK_CMD_TRAP_POLICER_DEL

(DEVLINK_NAMES, DEVLINK_VALUES) = map_namespace('DEVLINK_CMD_', globals())

# port type
DEVLINK_PORT_TYPE_NOTSET = 0
DEVLINK_PORT_TYPE_AUTO = 1
DEVLINK_PORT_TYPE_ETH = 2
DEVLINK_PORT_TYPE_IB = 3

# threshold type
DEVLINK_SB_POOL_TYPE_INGRESS = 0
DEVLINK_SB_POOL_TYPE_EGRESS = 1

DEVLINK_SB_THRESHOLD_TO_ALPHA_MAX = 20


class devlinkcmd(genlmsg):
    prefix = 'DEVLINK_ATTR_'
    nla_map = (
        ('DEVLINK_ATTR_UNSPEC', 'none'),
        ('DEVLINK_ATTR_BUS_NAME', 'asciiz'),
        ('DEVLINK_ATTR_DEV_NAME', 'asciiz'),
        ('DEVLINK_ATTR_PORT_INDEX', 'uint32'),
        ('DEVLINK_ATTR_PORT_TYPE', 'uint16'),
        ('DEVLINK_ATTR_PORT_DESIRED_TYPE', 'uint16'),
        ('DEVLINK_ATTR_PORT_NETDEV_IFINDEX', 'uint32'),
        ('DEVLINK_ATTR_PORT_NETDEV_NAME', 'asciiz'),
        ('DEVLINK_ATTR_PORT_IBDEV_NAME', 'asciiz'),
        ('DEVLINK_ATTR_PORT_SPLIT_COUNT', 'uint32'),
        ('DEVLINK_ATTR_PORT_SPLIT_GROUP', 'uint32'),
        ('DEVLINK_ATTR_SB_INDEX', 'uint32'),
        ('DEVLINK_ATTR_SB_SIZE', 'uint32'),
        ('DEVLINK_ATTR_SB_INGRESS_POOL_COUNT', 'uint16'),
        ('DEVLINK_ATTR_SB_EGRESS_POOL_COUNT', 'uint16'),
        ('DEVLINK_ATTR_SB_INGRESS_TC_COUNT', 'uint16'),
        ('DEVLINK_ATTR_SB_EGRESS_TC_COUNT', 'uint16'),
        ('DEVLINK_ATTR_SB_POOL_INDEX', 'uint16'),
        ('DEVLINK_ATTR_SB_POOL_TYPE', 'uint8'),
        ('DEVLINK_ATTR_SB_POOL_SIZE', 'uint32'),
        ('DEVLINK_ATTR_SB_POOL_THRESHOLD_TYPE', 'uint8'),
        ('DEVLINK_ATTR_SB_THRESHOLD', 'uint32'),
        ('DEVLINK_ATTR_SB_TC_INDEX', 'uint16'),
        ('DEVLINK_ATTR_SB_OCC_CUR', 'uint32'),
        ('DEVLINK_ATTR_SB_OCC_MAX', 'uint32'),
        ('DEVLINK_ATTR_ESWITCH_MODE', 'uint16'),
        ('DEVLINK_ATTR_ESWITCH_INLINE_MODE', 'uint8'),
        ('DEVLINK_ATTR_DPIPE_TABLES', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_TABLE', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_TABLE_NAME', 'asciiz'),
        ('DEVLINK_ATTR_DPIPE_TABLE_SIZE', 'uint64'),
        ('DEVLINK_ATTR_DPIPE_TABLE_MATCHES', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_TABLE_ACTIONS', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_TABLE_COUNTERS_ENABLED', 'uint8'),
        ('DEVLINK_ATTR_DPIPE_ENTRIES', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_ENTRY', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_ENTRY_INDEX', 'uint64'),
        ('DEVLINK_ATTR_DPIPE_ENTRY_MATCH_VALUES', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_ENTRY_ACTION_VALUES', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_ENTRY_COUNTER', 'uint64'),
        ('DEVLINK_ATTR_DPIPE_MATCH', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_MATCH_VALUE', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_MATCH_TYPE', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_ACTION', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_ACTION_VALUE', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_ACTION_TYPE', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_VALUE', 'none'),
        ('DEVLINK_ATTR_DPIPE_VALUE_MASK', 'none'),
        ('DEVLINK_ATTR_DPIPE_VALUE_MAPPING', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_HEADERS', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_HEADER', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_HEADER_NAME', 'asciiz'),
        ('DEVLINK_ATTR_DPIPE_HEADER_ID', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_HEADER_FIELDS', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_HEADER_GLOBAL', 'uint8'),
        ('DEVLINK_ATTR_DPIPE_HEADER_INDEX', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_FIELD', 'devlink'),
        ('DEVLINK_ATTR_DPIPE_FIELD_NAME', 'asciiz'),
        ('DEVLINK_ATTR_DPIPE_FIELD_ID', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_FIELD_BITWIDTH', 'uint32'),
        ('DEVLINK_ATTR_DPIPE_FIELD_MAPPING_TYPE', 'uint32'),
        ('DEVLINK_ATTR_PAD', 'none'),
        ('DEVLINK_ATTR_ESWITCH_ENCAP_MODE', 'uint8'),
        ('DEVLINK_ATTR_RESOURCE_LIST', 'devlink'),
        ('DEVLINK_ATTR_RESOURCE', 'devlink'),
        ('DEVLINK_ATTR_RESOURCE_NAME', 'asciiz'),
        ('DEVLINK_ATTR_RESOURCE_ID', 'uint64'),
        ('DEVLINK_ATTR_RESOURCE_SIZE', 'uint64'),
        ('DEVLINK_ATTR_RESOURCE_SIZE_NEW', 'uint64'),
        ('DEVLINK_ATTR_RESOURCE_SIZE_VALID', 'uint8'),
        ('DEVLINK_ATTR_RESOURCE_SIZE_MIN', 'uint64'),
        ('DEVLINK_ATTR_RESOURCE_SIZE_MAX', 'uint64'),
        ('DEVLINK_ATTR_RESOURCE_SIZE_GRAN', 'uint64'),
        ('DEVLINK_ATTR_RESOURCE_UNIT', 'uint8'),
        ('DEVLINK_ATTR_RESOURCE_OCC', 'uint64'),
        ('DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_ID', 'uint64'),
        ('DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_UNITS', 'uint64'),
        ('DEVLINK_ATTR_PORT_FLAVOUR', 'uint16'),
        ('DEVLINK_ATTR_PORT_NUMBER', 'uint32'),
        ('DEVLINK_ATTR_PORT_SPLIT_SUBPORT_NUMBER', 'uint32'),
        ('DEVLINK_ATTR_PARAM', 'devlink'),
        ('DEVLINK_ATTR_PARAM_NAME', 'asciiz'),
        ('DEVLINK_ATTR_PARAM_GENERIC', 'flag'),
        ('DEVLINK_ATTR_PARAM_TYPE', 'uint8'),
        ('DEVLINK_ATTR_PARAM_VALUES_LIST', 'devlink'),
        ('DEVLINK_ATTR_PARAM_VALUE', 'devlink'),
        ('DEVLINK_ATTR_PARAM_VALUE_DATA', 'none'),
        ('DEVLINK_ATTR_PARAM_VALUE_CMODE', 'uint8'),
        ('DEVLINK_ATTR_REGION_NAME', 'asciiz'),
        ('DEVLINK_ATTR_REGION_SIZE', 'uint64'),
        ('DEVLINK_ATTR_REGION_SNAPSHOTS', 'devlink'),
        ('DEVLINK_ATTR_REGION_SNAPSHOT', 'devlink'),
        ('DEVLINK_ATTR_REGION_SNAPSHOT_ID', 'uint32'),
        ('DEVLINK_ATTR_REGION_CHUNKS', 'devlink'),
        ('DEVLINK_ATTR_REGION_CHUNK', 'devlink'),
        ('DEVLINK_ATTR_REGION_CHUNK_DATA', 'binary'),
        ('DEVLINK_ATTR_REGION_CHUNK_ADDR', 'uint64'),
        ('DEVLINK_ATTR_REGION_CHUNK_LEN', 'uint64'),
        ('DEVLINK_ATTR_INFO_DRIVER_NAME', 'asciiz'),
        ('DEVLINK_ATTR_INFO_SERIAL_NUMBER', 'asciiz'),
        ('DEVLINK_ATTR_INFO_VERSION_FIXED', 'devlink'),
        ('DEVLINK_ATTR_INFO_VERSION_RUNNING', 'devlink'),
        ('DEVLINK_ATTR_INFO_VERSION_STORED', 'devlink'),
        ('DEVLINK_ATTR_INFO_VERSION_NAME', 'asciiz'),
        ('DEVLINK_ATTR_INFO_VERSION_VALUE', 'asciiz'),
        ('DEVLINK_ATTR_SB_POOL_CELL_SIZE', 'uint32'),
        ('DEVLINK_ATTR_FMSG', 'devlink'),
        ('DEVLINK_ATTR_FMSG_OBJ_NEST_START', 'flag'),
        ('DEVLINK_ATTR_FMSG_PAIR_NEST_START', 'flag'),
        ('DEVLINK_ATTR_FMSG_ARR_NEST_START', 'flag'),
        ('DEVLINK_ATTR_FMSG_NEST_END', 'flag'),
        ('DEVLINK_ATTR_FMSG_OBJ_NAME', 'asciiz'),
        ('DEVLINK_ATTR_FMSG_OBJ_VALUE_TYPE', 'uint8'),
        ('DEVLINK_ATTR_FMSG_OBJ_VALUE_DATA', 'none'),
        ('DEVLINK_ATTR_HEALTH_REPORTER', 'devlink'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_NAME', 'asciiz'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_STATE', 'uint8'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_ERR_COUNT', 'uint64'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_RECOVER_COUNT', 'uint64'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_DUMP_TS', 'uint64'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_GRACEFUL_PERIOD', 'uint64'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_AUTO_RECOVER', 'uint8'),
        ('DEVLINK_ATTR_FLASH_UPDATE_FILE_NAME', 'asciiz'),
        ('DEVLINK_ATTR_FLASH_UPDATE_COMPONENT', 'asciiz'),
        ('DEVLINK_ATTR_FLASH_UPDATE_STATUS_MSG', 'asciiz'),
        ('DEVLINK_ATTR_FLASH_UPDATE_STATUS_DONE', 'uint64'),
        ('DEVLINK_ATTR_FLASH_UPDATE_STATUS_TOTAL', 'uint64'),
        ('DEVLINK_ATTR_PORT_PCI_PF_NUMBER', 'uint16'),
        ('DEVLINK_ATTR_PORT_PCI_VF_NUMBER', 'uint16'),
        ('DEVLINK_ATTR_STATS', 'devlink'),
        ('DEVLINK_ATTR_TRAP_NAME', 'asciiz'),
        ('DEVLINK_ATTR_TRAP_ACTION', 'uint8'),
        ('DEVLINK_ATTR_TRAP_TYPE', 'uint8'),
        ('DEVLINK_ATTR_TRAP_GENERIC', 'flag'),
        ('DEVLINK_ATTR_TRAP_METADATA', 'devlink'),
        ('DEVLINK_ATTR_TRAP_GROUP_NAME', 'asciiz'),
        ('DEVLINK_ATTR_RELOAD_FAILED', 'uint8'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_DUMP_TS_NS', 'uint64'),
        ('DEVLINK_ATTR_NETNS_FD', 'uint32'),
        ('DEVLINK_ATTR_NETNS_PID', 'uint32'),
        ('DEVLINK_ATTR_NETNS_ID', 'uint32'),
        ('DEVLINK_ATTR_HEALTH_REPORTER_AUTO_DUMP', 'uint8'),
        ('DEVLINK_ATTR_TRAP_POLICER_ID', 'uint32'),
        ('DEVLINK_ATTR_TRAP_POLICER_RATE', 'uint64'),
        ('DEVLINK_ATTR_TRAP_POLICER_BURST', 'uint64'),
        ('DEVLINK_ATTR_PORT_FUNCTION', 'devlink'),
        ('DEVLINK_ATTR_INFO_BOARD_SERIAL_NUMBER', 'asciiz'),
        ('DEVLINK_ATTR_PORT_LANES', 'uint32'),
        ('DEVLINK_ATTR_PORT_SPLITTABLE', 'uint8'),
    )

    class devlink(nla):
        prefix = 'DEVLINK_ATTR_'
        nla_map = (
            ('DEVLINK_ATTR_UNSPEC', 'none'),
            ('DEVLINK_ATTR_BUS_NAME', 'asciiz'),
            ('DEVLINK_ATTR_DEV_NAME', 'asciiz'),
            ('DEVLINK_ATTR_PORT_INDEX', 'uint32'),
            ('DEVLINK_ATTR_PORT_TYPE', 'uint16'),
            ('DEVLINK_ATTR_PORT_DESIRED_TYPE', 'uint16'),
            ('DEVLINK_ATTR_PORT_NETDEV_IFINDEX', 'uint32'),
            ('DEVLINK_ATTR_PORT_NETDEV_NAME', 'asciiz'),
            ('DEVLINK_ATTR_PORT_IBDEV_NAME', 'asciiz'),
            ('DEVLINK_ATTR_PORT_SPLIT_COUNT', 'uint32'),
            ('DEVLINK_ATTR_PORT_SPLIT_GROUP', 'uint32'),
            ('DEVLINK_ATTR_SB_INDEX', 'uint32'),
            ('DEVLINK_ATTR_SB_SIZE', 'uint32'),
            ('DEVLINK_ATTR_SB_INGRESS_POOL_COUNT', 'uint16'),
            ('DEVLINK_ATTR_SB_EGRESS_POOL_COUNT', 'uint16'),
            ('DEVLINK_ATTR_SB_INGRESS_TC_COUNT', 'uint16'),
            ('DEVLINK_ATTR_SB_EGRESS_TC_COUNT', 'uint16'),
            ('DEVLINK_ATTR_SB_POOL_INDEX', 'uint16'),
            ('DEVLINK_ATTR_SB_POOL_TYPE', 'uint8'),
            ('DEVLINK_ATTR_SB_POOL_SIZE', 'uint32'),
            ('DEVLINK_ATTR_SB_POOL_THRESHOLD_TYPE', 'uint8'),
            ('DEVLINK_ATTR_SB_THRESHOLD', 'uint32'),
            ('DEVLINK_ATTR_SB_TC_INDEX', 'uint16'),
            ('DEVLINK_ATTR_SB_OCC_CUR', 'uint32'),
            ('DEVLINK_ATTR_SB_OCC_MAX', 'uint32'),
            ('DEVLINK_ATTR_ESWITCH_MODE', 'uint16'),
            ('DEVLINK_ATTR_ESWITCH_INLINE_MODE', 'uint8'),
            ('DEVLINK_ATTR_DPIPE_TABLES', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_TABLE', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_TABLE_NAME', 'asciiz'),
            ('DEVLINK_ATTR_DPIPE_TABLE_SIZE', 'uint64'),
            ('DEVLINK_ATTR_DPIPE_TABLE_MATCHES', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_TABLE_ACTIONS', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_TABLE_COUNTERS_ENABLED', 'uint8'),
            ('DEVLINK_ATTR_DPIPE_ENTRIES', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_ENTRY', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_ENTRY_INDEX', 'uint64'),
            ('DEVLINK_ATTR_DPIPE_ENTRY_MATCH_VALUES', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_ENTRY_ACTION_VALUES', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_ENTRY_COUNTER', 'uint64'),
            ('DEVLINK_ATTR_DPIPE_MATCH', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_MATCH_VALUE', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_MATCH_TYPE', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_ACTION', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_ACTION_VALUE', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_ACTION_TYPE', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_VALUE', 'none'),
            ('DEVLINK_ATTR_DPIPE_VALUE_MASK', 'none'),
            ('DEVLINK_ATTR_DPIPE_VALUE_MAPPING', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_HEADERS', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_HEADER', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_HEADER_NAME', 'asciiz'),
            ('DEVLINK_ATTR_DPIPE_HEADER_ID', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_HEADER_FIELDS', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_HEADER_GLOBAL', 'uint8'),
            ('DEVLINK_ATTR_DPIPE_HEADER_INDEX', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_FIELD', 'recursive'),
            ('DEVLINK_ATTR_DPIPE_FIELD_NAME', 'asciiz'),
            ('DEVLINK_ATTR_DPIPE_FIELD_ID', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_FIELD_BITWIDTH', 'uint32'),
            ('DEVLINK_ATTR_DPIPE_FIELD_MAPPING_TYPE', 'uint32'),
            ('DEVLINK_ATTR_PAD', 'none'),
            ('DEVLINK_ATTR_ESWITCH_ENCAP_MODE', 'uint8'),
            ('DEVLINK_ATTR_RESOURCE_LIST', 'recursive'),
            ('DEVLINK_ATTR_RESOURCE', 'recursive'),
            ('DEVLINK_ATTR_RESOURCE_NAME', 'asciiz'),
            ('DEVLINK_ATTR_RESOURCE_ID', 'uint64'),
            ('DEVLINK_ATTR_RESOURCE_SIZE', 'uint64'),
            ('DEVLINK_ATTR_RESOURCE_SIZE_NEW', 'uint64'),
            ('DEVLINK_ATTR_RESOURCE_SIZE_VALID', 'uint8'),
            ('DEVLINK_ATTR_RESOURCE_SIZE_MIN', 'uint64'),
            ('DEVLINK_ATTR_RESOURCE_SIZE_MAX', 'uint64'),
            ('DEVLINK_ATTR_RESOURCE_SIZE_GRAN', 'uint64'),
            ('DEVLINK_ATTR_RESOURCE_UNIT', 'uint8'),
            ('DEVLINK_ATTR_RESOURCE_OCC', 'uint64'),
            ('DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_ID', 'uint64'),
            ('DEVLINK_ATTR_DPIPE_TABLE_RESOURCE_UNITS', 'uint64'),
            ('DEVLINK_ATTR_PORT_FLAVOUR', 'uint16'),
            ('DEVLINK_ATTR_PORT_NUMBER', 'uint32'),
            ('DEVLINK_ATTR_PORT_SPLIT_SUBPORT_NUMBER', 'uint32'),
            ('DEVLINK_ATTR_PARAM', 'recursive'),
            ('DEVLINK_ATTR_PARAM_NAME', 'asciiz'),
            ('DEVLINK_ATTR_PARAM_GENERIC', 'flag'),
            ('DEVLINK_ATTR_PARAM_TYPE', 'uint8'),
            ('DEVLINK_ATTR_PARAM_VALUES_LIST', 'recursive'),
            ('DEVLINK_ATTR_PARAM_VALUE', 'recursive'),
            ('DEVLINK_ATTR_PARAM_VALUE_DATA', 'none'),
            ('DEVLINK_ATTR_PARAM_VALUE_CMODE', 'uint8'),
            ('DEVLINK_ATTR_REGION_NAME', 'asciiz'),
            ('DEVLINK_ATTR_REGION_SIZE', 'uint64'),
            ('DEVLINK_ATTR_REGION_SNAPSHOTS', 'recursive'),
            ('DEVLINK_ATTR_REGION_SNAPSHOT', 'recursive'),
            ('DEVLINK_ATTR_REGION_SNAPSHOT_ID', 'uint32'),
            ('DEVLINK_ATTR_REGION_CHUNKS', 'recursive'),
            ('DEVLINK_ATTR_REGION_CHUNK', 'recursive'),
            ('DEVLINK_ATTR_REGION_CHUNK_DATA', 'binary'),
            ('DEVLINK_ATTR_REGION_CHUNK_ADDR', 'uint64'),
            ('DEVLINK_ATTR_REGION_CHUNK_LEN', 'uint64'),
            ('DEVLINK_ATTR_INFO_DRIVER_NAME', 'asciiz'),
            ('DEVLINK_ATTR_INFO_SERIAL_NUMBER', 'asciiz'),
            ('DEVLINK_ATTR_INFO_VERSION_FIXED', 'recursive'),
            ('DEVLINK_ATTR_INFO_VERSION_RUNNING', 'recursive'),
            ('DEVLINK_ATTR_INFO_VERSION_STORED', 'recursive'),
            ('DEVLINK_ATTR_INFO_VERSION_NAME', 'asciiz'),
            ('DEVLINK_ATTR_INFO_VERSION_VALUE', 'asciiz'),
            ('DEVLINK_ATTR_SB_POOL_CELL_SIZE', 'uint32'),
            ('DEVLINK_ATTR_FMSG', 'recursive'),
            ('DEVLINK_ATTR_FMSG_OBJ_NEST_START', 'flag'),
            ('DEVLINK_ATTR_FMSG_PAIR_NEST_START', 'flag'),
            ('DEVLINK_ATTR_FMSG_ARR_NEST_START', 'flag'),
            ('DEVLINK_ATTR_FMSG_NEST_END', 'flag'),
            ('DEVLINK_ATTR_FMSG_OBJ_NAME', 'asciiz'),
            ('DEVLINK_ATTR_FMSG_OBJ_VALUE_TYPE', 'uint8'),
            ('DEVLINK_ATTR_FMSG_OBJ_VALUE_DATA', 'none'),
            ('DEVLINK_ATTR_HEALTH_REPORTER', 'recursive'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_NAME', 'asciiz'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_STATE', 'uint8'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_ERR_COUNT', 'uint64'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_RECOVER_COUNT', 'uint64'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_DUMP_TS', 'uint64'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_GRACEFUL_PERIOD', 'uint64'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_AUTO_RECOVER', 'uint8'),
            ('DEVLINK_ATTR_FLASH_UPDATE_FILE_NAME', 'asciiz'),
            ('DEVLINK_ATTR_FLASH_UPDATE_COMPONENT', 'asciiz'),
            ('DEVLINK_ATTR_FLASH_UPDATE_STATUS_MSG', 'asciiz'),
            ('DEVLINK_ATTR_FLASH_UPDATE_STATUS_DONE', 'uint64'),
            ('DEVLINK_ATTR_FLASH_UPDATE_STATUS_TOTAL', 'uint64'),
            ('DEVLINK_ATTR_PORT_PCI_PF_NUMBER', 'uint16'),
            ('DEVLINK_ATTR_PORT_PCI_VF_NUMBER', 'uint16'),
            ('DEVLINK_ATTR_STATS', 'recursive'),
            ('DEVLINK_ATTR_TRAP_NAME', 'asciiz'),
            ('DEVLINK_ATTR_TRAP_ACTION', 'uint8'),
            ('DEVLINK_ATTR_TRAP_TYPE', 'uint8'),
            ('DEVLINK_ATTR_TRAP_GENERIC', 'flag'),
            ('DEVLINK_ATTR_TRAP_METADATA', 'recursive'),
            ('DEVLINK_ATTR_TRAP_GROUP_NAME', 'asciiz'),
            ('DEVLINK_ATTR_RELOAD_FAILED', 'uint8'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_DUMP_TS_NS', 'uint64'),
            ('DEVLINK_ATTR_NETNS_FD', 'uint32'),
            ('DEVLINK_ATTR_NETNS_PID', 'uint32'),
            ('DEVLINK_ATTR_NETNS_ID', 'uint32'),
            ('DEVLINK_ATTR_HEALTH_REPORTER_AUTO_DUMP', 'uint8'),
            ('DEVLINK_ATTR_TRAP_POLICER_ID', 'uint32'),
            ('DEVLINK_ATTR_TRAP_POLICER_RATE', 'uint64'),
            ('DEVLINK_ATTR_TRAP_POLICER_BURST', 'uint64'),
            ('DEVLINK_ATTR_PORT_FUNCTION', 'recursive'),
            ('DEVLINK_ATTR_INFO_BOARD_SERIAL_NUMBER', 'asciiz'),
            ('DEVLINK_ATTR_PORT_LANES', 'uint32'),
            ('DEVLINK_ATTR_PORT_SPLITTABLE', 'uint8'),
        )


class MarshalDevlink(Marshal):
    msg_map = {
        DEVLINK_CMD_UNSPEC: devlinkcmd,
        DEVLINK_CMD_GET: devlinkcmd,
        DEVLINK_CMD_SET: devlinkcmd,
        DEVLINK_CMD_NEW: devlinkcmd,
        DEVLINK_CMD_DEL: devlinkcmd,
        DEVLINK_CMD_PORT_GET: devlinkcmd,
        DEVLINK_CMD_PORT_SET: devlinkcmd,
        DEVLINK_CMD_PORT_NEW: devlinkcmd,
        DEVLINK_CMD_PORT_DEL: devlinkcmd,
        DEVLINK_CMD_PORT_SPLIT: devlinkcmd,
        DEVLINK_CMD_PORT_UNSPLIT: devlinkcmd,
        DEVLINK_CMD_SB_GET: devlinkcmd,
        DEVLINK_CMD_SB_SET: devlinkcmd,
        DEVLINK_CMD_SB_NEW: devlinkcmd,
        DEVLINK_CMD_SB_DEL: devlinkcmd,
        DEVLINK_CMD_SB_POOL_GET: devlinkcmd,
        DEVLINK_CMD_SB_POOL_SET: devlinkcmd,
        DEVLINK_CMD_SB_POOL_NEW: devlinkcmd,
        DEVLINK_CMD_SB_POOL_DEL: devlinkcmd,
        DEVLINK_CMD_SB_PORT_POOL_GET: devlinkcmd,
        DEVLINK_CMD_SB_PORT_POOL_SET: devlinkcmd,
        DEVLINK_CMD_SB_PORT_POOL_NEW: devlinkcmd,
        DEVLINK_CMD_SB_PORT_POOL_DEL: devlinkcmd,
        DEVLINK_CMD_SB_TC_POOL_BIND_GET: devlinkcmd,
        DEVLINK_CMD_SB_TC_POOL_BIND_SET: devlinkcmd,
        DEVLINK_CMD_SB_TC_POOL_BIND_NEW: devlinkcmd,
        DEVLINK_CMD_SB_TC_POOL_BIND_DEL: devlinkcmd,
        DEVLINK_CMD_SB_OCC_SNAPSHOT: devlinkcmd,
        DEVLINK_CMD_SB_OCC_MAX_CLEAR: devlinkcmd,
        DEVLINK_CMD_ESWITCH_GET: devlinkcmd,
        DEVLINK_CMD_ESWITCH_SET: devlinkcmd,
        DEVLINK_CMD_DPIPE_TABLE_GET: devlinkcmd,
        DEVLINK_CMD_DPIPE_ENTRIES_GET: devlinkcmd,
        DEVLINK_CMD_DPIPE_HEADERS_GET: devlinkcmd,
        DEVLINK_CMD_DPIPE_TABLE_COUNTERS_SET: devlinkcmd,
        DEVLINK_CMD_RESOURCE_SET: devlinkcmd,
        DEVLINK_CMD_RESOURCE_DUMP: devlinkcmd,
        DEVLINK_CMD_RELOAD: devlinkcmd,
        DEVLINK_CMD_PARAM_GET: devlinkcmd,
        DEVLINK_CMD_PARAM_SET: devlinkcmd,
        DEVLINK_CMD_PARAM_NEW: devlinkcmd,
        DEVLINK_CMD_PARAM_DEL: devlinkcmd,
        DEVLINK_CMD_REGION_GET: devlinkcmd,
        DEVLINK_CMD_REGION_SET: devlinkcmd,
        DEVLINK_CMD_REGION_NEW: devlinkcmd,
        DEVLINK_CMD_REGION_DEL: devlinkcmd,
        DEVLINK_CMD_REGION_READ: devlinkcmd,
        DEVLINK_CMD_PORT_PARAM_GET: devlinkcmd,
        DEVLINK_CMD_PORT_PARAM_SET: devlinkcmd,
        DEVLINK_CMD_PORT_PARAM_NEW: devlinkcmd,
        DEVLINK_CMD_PORT_PARAM_DEL: devlinkcmd,
        DEVLINK_CMD_INFO_GET: devlinkcmd,
        DEVLINK_CMD_HEALTH_REPORTER_GET: devlinkcmd,
        DEVLINK_CMD_HEALTH_REPORTER_SET: devlinkcmd,
        DEVLINK_CMD_HEALTH_REPORTER_RECOVER: devlinkcmd,
        DEVLINK_CMD_HEALTH_REPORTER_DIAGNOSE: devlinkcmd,
        DEVLINK_CMD_HEALTH_REPORTER_DUMP_GET: devlinkcmd,
        DEVLINK_CMD_HEALTH_REPORTER_DUMP_CLEAR: devlinkcmd,
        DEVLINK_CMD_FLASH_UPDATE: devlinkcmd,
        DEVLINK_CMD_FLASH_UPDATE_END: devlinkcmd,
        DEVLINK_CMD_FLASH_UPDATE_STATUS: devlinkcmd,
        DEVLINK_CMD_TRAP_GET: devlinkcmd,
        DEVLINK_CMD_TRAP_SET: devlinkcmd,
        DEVLINK_CMD_TRAP_NEW: devlinkcmd,
        DEVLINK_CMD_TRAP_DEL: devlinkcmd,
        DEVLINK_CMD_TRAP_GROUP_GET: devlinkcmd,
        DEVLINK_CMD_TRAP_GROUP_SET: devlinkcmd,
        DEVLINK_CMD_TRAP_GROUP_NEW: devlinkcmd,
        DEVLINK_CMD_TRAP_GROUP_DEL: devlinkcmd,
        DEVLINK_CMD_TRAP_POLICER_GET: devlinkcmd,
        DEVLINK_CMD_TRAP_POLICER_SET: devlinkcmd,
        DEVLINK_CMD_TRAP_POLICER_NEW: devlinkcmd,
        DEVLINK_CMD_TRAP_POLICER_DEL: devlinkcmd,
    }

    def fix_message(self, msg):
        try:
            msg['event'] = DEVLINK_VALUES[msg['cmd']]
        except Exception:
            pass


class DevlinkSocket(GenericNetlinkSocket):
    def __init__(self, *args, **kwargs):
        GenericNetlinkSocket.__init__(self, *args, **kwargs)
        self.marshal = MarshalDevlink()

    def bind(self, groups=0, **kwarg):
        GenericNetlinkSocket.bind(
            self, 'devlink', devlinkcmd, groups, None, **kwarg
        )
