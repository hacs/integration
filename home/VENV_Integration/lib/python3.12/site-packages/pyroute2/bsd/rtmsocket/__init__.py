import struct
from socket import AF_INET, AF_INET6, AF_ROUTE, SOCK_RAW

from pyroute2 import config
from pyroute2.bsd.pf_route import (
    bsdmsg,
    if_announcemsg,
    if_msg,
    ifa_msg,
    ifma_msg,
    rt_msg,
)
from pyroute2.common import dqn2int
from pyroute2.netlink.rtnl import RTM_DELADDR as RTNL_DELADDR
from pyroute2.netlink.rtnl import RTM_DELLINK as RTNL_DELLINK
from pyroute2.netlink.rtnl import RTM_DELROUTE as RTNL_DELROUTE
from pyroute2.netlink.rtnl import RTM_NEWADDR as RTNL_NEWADDR
from pyroute2.netlink.rtnl import RTM_NEWLINK as RTNL_NEWLINK
from pyroute2.netlink.rtnl import RTM_NEWROUTE as RTNL_NEWROUTE
from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.netlink.rtnl.rtmsg import rtmsg

if config.uname[0] == 'OpenBSD':
    from pyroute2.bsd.rtmsocket.openbsd import (
        RTM_ADD,
        RTM_NEWADDR,
        RTMSocketBase,
    )
else:
    from pyroute2.bsd.rtmsocket.freebsd import (
        RTM_ADD,
        RTM_NEWADDR,
        RTMSocketBase,
    )


def convert_rt_msg(msg):
    ret = rtmsg()
    ret['header']['type'] = (
        RTNL_NEWROUTE if msg['header']['type'] == RTM_ADD else RTNL_DELROUTE
    )
    ret['family'] = msg['DST']['header']['family']
    ret['attrs'] = []
    if 'address' in msg['DST']:
        ret['attrs'].append(['RTA_DST', msg['DST']['address']])
    if (
        'NETMASK' in msg
        and msg['NETMASK']['header']['family'] == ret['family']
    ):
        ret['dst_len'] = dqn2int(msg['NETMASK']['address'], ret['family'])
    if 'GATEWAY' in msg:
        if msg['GATEWAY']['header']['family'] not in (AF_INET, AF_INET6):
            # interface routes, table 255
            # discard for now
            return None
        ret['attrs'].append(['RTA_GATEWAY', msg['GATEWAY']['address']])
    if 'IFA' in msg:
        ret['attrs'].append(['RTA_SRC', msg['IFA']['address']])
    if 'IFP' in msg:
        ret['attrs'].append(['RTA_OIF', msg['IFP']['index']])
    elif msg['rtm_index'] != 0:
        ret['attrs'].append(['RTA_OIF', msg['rtm_index']])
    del ret['value']
    return ret


def convert_if_msg(msg):
    # discard this type for now
    return None


def convert_ifa_msg(msg):
    ret = ifaddrmsg()
    ret['header']['type'] = (
        RTNL_NEWADDR if msg['header']['type'] == RTM_NEWADDR else RTNL_DELADDR
    )
    ret['index'] = msg['IFP']['index']
    ret['family'] = msg['IFA']['header']['family']
    ret['prefixlen'] = dqn2int(msg['NETMASK']['address'], ret['family'])
    ret['attrs'] = [
        ['IFA_ADDRESS', msg['IFA']['address']],
        ['IFA_BROADCAST', msg['BRD']['address']],
        ['IFA_LABEL', msg['IFP']['ifname']],
    ]
    del ret['value']
    return ret


def convert_ifma_msg(msg):
    # ignore for now
    return None


def convert_if_announcemsg(msg):
    ret = ifinfmsg()
    ret['header']['type'] = RTNL_DELLINK if msg['ifan_what'] else RTNL_NEWLINK
    ret['index'] = msg['ifan_index']
    ret['attrs'] = [['IFLA_IFNAME', msg['ifan_name']]]
    del ret['value']
    return ret


def convert_bsdmsg(msg):
    # ignore unknown messages
    return None


convert = {
    rt_msg: convert_rt_msg,
    ifa_msg: convert_ifa_msg,
    if_msg: convert_if_msg,
    ifma_msg: convert_ifma_msg,
    if_announcemsg: convert_if_announcemsg,
    bsdmsg: convert_bsdmsg,
}


class RTMSocket(RTMSocketBase):
    def __init__(self, output='pf_route', target='localhost'):
        self.target = target
        self._sock = config.SocketBase(AF_ROUTE, SOCK_RAW)
        self._output = output

    def fileno(self):
        return self._sock.fileno()

    def get(self):
        msg = self._sock.recv(2048)
        _, _, msg_type = struct.unpack('HBB', msg[:4])
        msg_class = self.msg_map.get(msg_type, None)
        if msg_class is not None:
            msg = msg_class(msg)
            msg.decode()
            if self._output == 'netlink':
                # convert messages to the Netlink format
                msg = convert[type(msg)](msg)
                msg['header']['target'] = self.target
        return msg

    def close(self):
        self._sock.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


__all__ = [RTMSocket]
