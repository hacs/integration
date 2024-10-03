'''
'''

from enum import Enum

from pyroute2.netlink import genlmsg
from pyroute2.netlink.event import EventSocket
from pyroute2.netlink.nlsocket import Marshal


class ThermalGenlCmd(Enum):
    THERMAL_GENL_CMD_UNSPEC = 0
    THERMAL_GENL_CMD_TZ_GET_ID = 1
    THERMAL_GENL_CMD_TZ_GET_TRIP = 2
    THERMAL_GENL_CMD_TZ_GET_TEMP = 3
    THERMAL_GENL_CMD_TZ_GET_GOV = 4
    THERMAL_GENL_CMD_TZ_GET_MODE = 5
    THERMAL_GENL_CMD_CDEV_GET = 6


class ThermalGenlEvent(Enum):
    THERMAL_GENL_EVENT_UNSPEC = 0
    THERMAL_GENL_EVENT_TZ_CREATE = 1
    THERMAL_GENL_EVENT_TZ_DELETE = 2
    THERMAL_GENL_EVENT_TZ_DISABLE = 3
    THERMAL_GENL_EVENT_TZ_ENABLE = 4
    THERMAL_GENL_EVENT_TZ_TRIP_UP = 5
    THERMAL_GENL_EVENT_TZ_TRIP_DOWN = 6
    THERMAL_GENL_EVENT_TZ_TRIP_CHANGE = 7
    THERMAL_GENL_EVENT_TZ_TRIP_ADD = 8
    THERMAL_GENL_EVENT_TZ_TRIP_DELETE = 9
    THERMAL_GENL_EVENT_CDEV_ADD = 10
    THERMAL_GENL_EVENT_CDEV_DELETE = 11
    THERMAL_GENL_EVENT_CDEV_STATE_UPDATE = 12
    THERMAL_GENL_EVENT_TZ_GOV_CHANGE = 13
    THERMAL_GENL_EVENT_CPU_CAPABILITY_CHANGE = 14


class thermal_msg(genlmsg):
    nla_map = (
        ('THERMAL_GENL_ATTR_UNSPEC', 'none'),
        ('THERMAL_GENL_ATTR_TZ', 'nested'),
        ('THERMAL_GENL_ATTR_TZ_ID', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_TEMP', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_TRIP', 'nested'),
        ('THERMAL_GENL_ATTR_TZ_TRIP_ID', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_TRIP_TYPE', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_TRIP_TEMP', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_TRIP_HYST', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_MODE', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_NAME', 'asciiz'),
        ('THERMAL_GENL_ATTR_TZ_CDEV_WEIGHT', 'uint32'),
        ('THERMAL_GENL_ATTR_TZ_GOV', 'nested'),
        ('THERMAL_GENL_ATTR_TZ_GOV_NAME', 'asciiz'),
        ('THERMAL_GENL_ATTR_CDEV', 'nested'),
        ('THERMAL_GENL_ATTR_CDEV_ID', 'uint32'),
        ('THERMAL_GENL_ATTR_CDEV_CUR_STATE', 'uint32'),
        ('THERMAL_GENL_ATTR_CDEV_MAX_STATE', 'uint32'),
        ('THERMAL_GENL_ATTR_CDEV_NAME', 'asciiz'),
        ('THERMAL_GENL_ATTR_GOV_NAME', 'asciiz'),
        ('THERMAL_GENL_ATTR_CPU_CAPABILITY', 'nested'),
        ('THERMAL_GENL_ATTR_CPU_CAPABILITY_ID', 'uint32'),
        ('THERMAL_GENL_ATTR_CPU_CAPABILITY_PERFORMANCE', 'uint32'),
        ('THERMAL_GENL_ATTR_CPU_CAPABILITY_EFFICIENCY', 'uint32'),
    )


class MarshalThermalEvent(Marshal):
    msg_map = {x.value: thermal_msg for x in ThermalGenlEvent}


class ThermalEventSocket(EventSocket):
    marshal_class = MarshalThermalEvent
    genl_family = 'thermal'
