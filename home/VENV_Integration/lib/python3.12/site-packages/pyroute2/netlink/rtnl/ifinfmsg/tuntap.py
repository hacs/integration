import errno
import os
import struct
from fcntl import ioctl

from pyroute2 import config
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.rtnl.ifinfmsg import (
    IFT_MULTI_QUEUE,
    IFT_NO_PI,
    IFT_ONE_QUEUE,
    IFT_TAP,
    IFT_TUN,
    IFT_VNET_HDR,
    RTM_NEWLINK,
)
from pyroute2.netlink.rtnl.ifinfmsg.sync import sync

IFNAMSIZ = 16

TUNDEV = '/dev/net/tun'
PLATFORMS = (
    'i386',
    'i686',
    'x86_64',
    'armv6l',
    'armv7l',
    's390x',
    'aarch64',
    'loongarch64',
)
if config.machine in PLATFORMS:
    TUNSETIFF = 0x400454CA
    TUNSETPERSIST = 0x400454CB
    TUNSETOWNER = 0x400454CC
    TUNSETGROUP = 0x400454CE
elif config.machine in ('ppc64', 'mips'):
    TUNSETIFF = 0x800454CA
    TUNSETPERSIST = 0x800454CB
    TUNSETOWNER = 0x800454CC
    TUNSETGROUP = 0x800454CE
else:
    TUNSETIFF = None


@sync
def manage_tun(msg):
    if TUNSETIFF is None:
        raise NetlinkError(errno.EOPNOTSUPP, 'Arch not supported')

    if msg['header']['type'] != RTM_NEWLINK:
        raise NetlinkError(errno.EOPNOTSUPP, 'Unsupported event')

    ifru_flags = 0
    linkinfo = msg.get_attr('IFLA_LINKINFO')
    infodata = linkinfo.get_attr('IFLA_INFO_DATA')

    if infodata.get_attr('IFLA_TUN_TYPE') == 1:
        ifru_flags |= IFT_TUN
    elif infodata.get_attr('IFLA_TUN_TYPE') == 2:
        ifru_flags |= IFT_TAP
    else:
        raise ValueError('invalid mode')
    if not infodata.get_attr('IFLA_TUN_PI'):
        ifru_flags |= IFT_NO_PI
    if infodata.get_attr('IFLA_TUN_VNET_HDR'):
        ifru_flags |= IFT_VNET_HDR
    if infodata.get_attr('IFLA_TUN_MULTI_QUEUE'):
        ifru_flags |= IFT_MULTI_QUEUE

    ifr = msg.get_attr('IFLA_IFNAME')
    if len(ifr) > IFNAMSIZ:
        raise ValueError('ifname too long')
    ifr += (IFNAMSIZ - len(ifr)) * '\0'
    ifr = ifr.encode('ascii')
    ifr += struct.pack('H', ifru_flags)

    user = infodata.get_attr('IFLA_TUN_OWNER')
    group = infodata.get_attr('IFLA_TUN_GROUP')
    #
    fd = os.open(TUNDEV, os.O_RDWR)
    try:
        ioctl(fd, TUNSETIFF, ifr)
        if user is not None:
            ioctl(fd, TUNSETOWNER, user)
        if group is not None:
            ioctl(fd, TUNSETGROUP, group)
        ioctl(fd, TUNSETPERSIST, 1)
    except Exception:
        raise
    finally:
        os.close(fd)


@sync
def manage_tuntap(msg):
    if TUNSETIFF is None:
        raise NetlinkError(errno.EOPNOTSUPP, 'Arch not supported')

    if msg['header']['type'] != RTM_NEWLINK:
        raise NetlinkError(errno.EOPNOTSUPP, 'Unsupported event')

    ifru_flags = 0
    linkinfo = msg.get_attr('IFLA_LINKINFO')
    infodata = linkinfo.get_attr('IFLA_INFO_DATA')

    flags = infodata.get_attr('IFTUN_IFR', None)
    if infodata.get_attr('IFTUN_MODE') == 'tun':
        ifru_flags |= IFT_TUN
    elif infodata.get_attr('IFTUN_MODE') == 'tap':
        ifru_flags |= IFT_TAP
    else:
        raise ValueError('invalid mode')
    if flags is not None:
        if flags['no_pi']:
            ifru_flags |= IFT_NO_PI
        if flags['one_queue']:
            ifru_flags |= IFT_ONE_QUEUE
        if flags['vnet_hdr']:
            ifru_flags |= IFT_VNET_HDR
        if flags['multi_queue']:
            ifru_flags |= IFT_MULTI_QUEUE
    ifr = msg.get_attr('IFLA_IFNAME')
    if len(ifr) > IFNAMSIZ:
        raise ValueError('ifname too long')
    ifr += (IFNAMSIZ - len(ifr)) * '\0'
    ifr = ifr.encode('ascii')
    ifr += struct.pack('H', ifru_flags)

    user = infodata.get_attr('IFTUN_UID')
    group = infodata.get_attr('IFTUN_GID')
    #
    fd = os.open(TUNDEV, os.O_RDWR)
    try:
        ioctl(fd, TUNSETIFF, ifr)
        if user is not None:
            ioctl(fd, TUNSETOWNER, user)
        if group is not None:
            ioctl(fd, TUNSETGROUP, group)
        ioctl(fd, TUNSETPERSIST, 1)
    except Exception:
        raise
    finally:
        os.close(fd)
