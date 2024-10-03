import json
import os
import subprocess

from pyroute2.common import map_enoent
from pyroute2.netlink.rtnl.ifinfmsg import RTM_NEWLINK
from pyroute2.netlink.rtnl.ifinfmsg.sync import sync
from pyroute2.netlink.rtnl.ifinfmsg.tuntap import manage_tun, manage_tuntap

_BONDING_MASTERS = '/sys/class/net/bonding_masters'
_BONDING_SLAVES = '/sys/class/net/%s/bonding/slaves'
_BRIDGE_MASTER = '/sys/class/net/%s/brport/bridge/ifindex'
_BONDING_MASTER = '/sys/class/net/%s/master/ifindex'
IFNAMSIZ = 16


def proxy_setlink(msg, nl):
    def get_interface(index):
        msg = nl.get_links(index)[0]
        try:
            kind = msg.get_attr('IFLA_LINKINFO').get_attr('IFLA_INFO_KIND')
        except AttributeError:
            kind = 'unknown'
        return {
            'ifname': msg.get_attr('IFLA_IFNAME'),
            'master': msg.get_attr('IFLA_MASTER'),
            'kind': kind,
        }

    forward = True

    # is it a port setup?
    master = msg.get_attr('IFLA_MASTER')
    if master is not None:
        if master == 0:
            # port delete
            # 1. get the current master
            iface = get_interface(msg['index'])
            master = get_interface(iface['master'])
            cmd = 'del'
        else:
            # port add
            # 1. get the master
            master = get_interface(master)
            cmd = 'add'

        ifname = (
            msg.get_attr('IFLA_IFNAME')
            or get_interface(msg['index'])['ifname']
        )

        # 2. manage the port
        forward_map = {'team': manage_team_port}
        if master['kind'] in forward_map:
            func = forward_map[master['kind']]
            forward = func(cmd, master['ifname'], ifname, nl)

    if forward is not None:
        return {'verdict': 'forward', 'data': msg.data}


def proxy_newlink(msg, nl):
    kind = None

    # get the interface kind
    linkinfo = msg.get_attr('IFLA_LINKINFO')
    if linkinfo is not None:
        kind = [x[1] for x in linkinfo['attrs'] if x[0] == 'IFLA_INFO_KIND']
        if kind:
            kind = kind[0]

    if kind == 'tuntap':
        return manage_tuntap(msg)
    elif kind == 'tun':
        return manage_tun(msg)
    elif kind == 'team':
        return manage_team(msg)

    return {'verdict': 'forward', 'data': msg.data}


@map_enoent
@sync
def manage_team(msg):
    if msg['header']['type'] != RTM_NEWLINK:
        raise ValueError('wrong command type')

    try:
        linkinfo = msg.get_attr('IFLA_LINKINFO')
        infodata = linkinfo.get_attr('IFLA_INFO_DATA')
        config = infodata.get_attr('IFLA_TEAM_CONFIG')
        config = json.loads(config)
    except AttributeError:
        config = {
            'runner': {'name': 'activebackup'},
            'link_watch': {'name': 'ethtool'},
        }

    # fix device
    config['device'] = msg.get_attr('IFLA_IFNAME')

    with open(os.devnull, 'w') as fnull:
        subprocess.check_call(
            ['teamd', '-d', '-n', '-c', json.dumps(config)],
            stdout=fnull,
            stderr=fnull,
        )


@map_enoent
def manage_team_port(cmd, master, ifname, nl):
    with open(os.devnull, 'w') as fnull:
        subprocess.check_call(
            [
                'teamdctl',
                master,
                'port',
                'remove' if cmd == 'del' else 'add',
                ifname,
            ],
            stdout=fnull,
            stderr=fnull,
        )
