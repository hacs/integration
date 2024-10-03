import json
import os
import subprocess

from pyroute2.common import map_enoent
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.netlink.rtnl.ifinfmsg.sync import sync
from pyroute2.netlink.rtnl.ifinfmsg.tuntap import manage_tuntap
from pyroute2.netlink.rtnl.marshal import MarshalRtnl

# it's simpler to double constants here, than to change all the
# module layout; but it is a subject of the future refactoring
RTM_NEWLINK = 16
RTM_DELLINK = 17
#

_BONDING_MASTERS = '/sys/class/net/bonding_masters'
_BONDING_SLAVES = '/sys/class/net/%s/bonding/slaves'
_BRIDGE_MASTER = '/sys/class/net/%s/brport/bridge/ifindex'
_BONDING_MASTER = '/sys/class/net/%s/master/ifindex'
IFNAMSIZ = 16


def compat_fix_attrs(msg, nl):
    kind = None
    ifname = msg.get_attr('IFLA_IFNAME')

    # fix master
    if not nl.capabilities['provide_master']:
        master = compat_get_master(ifname)
        if master is not None:
            msg['attrs'].append(['IFLA_MASTER', master])

    # fix linkinfo & kind
    li = msg.get_attr('IFLA_LINKINFO')
    if li is not None:
        kind = li.get_attr('IFLA_INFO_KIND')
        if kind is None:
            kind = get_interface_type(ifname)
            li['attrs'].append(['IFLA_INFO_KIND', kind])
    elif 'attrs' in msg:
        kind = get_interface_type(ifname)
        msg['attrs'].append(
            ['IFLA_LINKINFO', {'attrs': [['IFLA_INFO_KIND', kind]]}]
        )
    else:
        return

    li = msg.get_attr('IFLA_LINKINFO')
    # fetch specific interface data

    if (kind in ('bridge', 'bond')) and [
        x for x in li['attrs'] if x[0] == 'IFLA_INFO_DATA'
    ]:
        if kind == 'bridge':
            t = '/sys/class/net/%s/bridge/%s'
            ifdata = ifinfmsg.ifinfo.bridge_data
        elif kind == 'bond':
            t = '/sys/class/net/%s/bonding/%s'
            ifdata = ifinfmsg.ifinfo.bond_data

        commands = []
        for cmd, _ in ifdata.nla_map:
            try:
                with open(t % (ifname, ifdata.nla2name(cmd)), 'r') as f:
                    value = f.read()
                if cmd == 'IFLA_BOND_MODE':
                    value = value.split()[1]
                commands.append([cmd, int(value)])
            except:
                pass
        if commands:
            li['attrs'].append(['IFLA_INFO_DATA', {'attrs': commands}])


def proxy_linkinfo(data, nl):
    marshal = MarshalRtnl()
    inbox = marshal.parse(data)
    data = b''
    for msg in inbox:
        if msg['event'] == 'NLMSG_ERROR':
            data += msg.data
            continue
        # Sysfs operations can require root permissions,
        # but the script can be run under a normal user
        # Bug-Url: https://github.com/svinota/pyroute2/issues/113
        try:
            compat_fix_attrs(msg, nl)
        except OSError:
            # We can safely ignore here any OSError.
            # In the worst case, we just return what we have got
            # from the kernel via netlink
            pass

        msg.reset()
        msg.encode()
        data += msg.data

    return {'verdict': 'forward', 'data': data}


def proxy_setlink(imsg, nl):
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

    msg = ifinfmsg(imsg.data)
    msg.decode()
    forward = True

    kind = None
    infodata = None

    ifname = (
        msg.get_attr('IFLA_IFNAME') or get_interface(msg['index'])['ifname']
    )
    linkinfo = msg.get_attr('IFLA_LINKINFO')
    if linkinfo:
        kind = linkinfo.get_attr('IFLA_INFO_KIND')
        infodata = linkinfo.get_attr('IFLA_INFO_DATA')

    if kind in ('bond', 'bridge') and infodata is not None:
        code = 0
        #
        if kind == 'bond':
            func = compat_set_bond
        elif kind == 'bridge':
            func = compat_set_bridge
        #
        for cmd, value in infodata.get('attrs', []):
            cmd = infodata.nla2name(cmd)
            code = func(ifname, cmd, value) or code
        #
        if code:
            err = OSError()
            err.errno = code
            raise err

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

        # 2. manage the port
        forward_map = {
            'team': manage_team_port,
            'bridge': compat_bridge_port,
            'bond': compat_bond_port,
        }
        if master['kind'] in forward_map:
            func = forward_map[master['kind']]
            forward = func(cmd, master['ifname'], ifname, nl)

    if forward is not None:
        return {'verdict': 'forward', 'data': imsg.data}


def proxy_dellink(imsg, nl):
    orig_msg = ifinfmsg(imsg.data)
    orig_msg.decode()

    # get full interface description
    msg = nl.get_links(orig_msg['index'])[0]
    msg['header']['type'] = orig_msg['header']['type']

    # get the interface kind
    kind = None
    li = msg.get_attr('IFLA_LINKINFO')
    if li is not None:
        kind = li.get_attr('IFLA_INFO_KIND')

    # team interfaces can be stopped by a normal RTM_DELLINK
    if kind == 'bond' and not nl.capabilities['create_bond']:
        return compat_del_bond(msg)
    elif kind == 'bridge' and not nl.capabilities['create_bridge']:
        return compat_del_bridge(msg)

    return {'verdict': 'forward', 'data': imsg.data}


def proxy_newlink(imsg, nl):
    msg = ifinfmsg(imsg.data)
    msg.decode()
    kind = None

    # get the interface kind
    linkinfo = msg.get_attr('IFLA_LINKINFO')
    if linkinfo is not None:
        kind = [x[1] for x in linkinfo['attrs'] if x[0] == 'IFLA_INFO_KIND']
        if kind:
            kind = kind[0]

    if kind == 'tuntap':
        return manage_tuntap(msg)
    elif kind == 'team':
        return manage_team(msg)
    elif kind == 'bond' and not nl.capabilities['create_bond']:
        return compat_create_bond(msg)
    elif kind == 'bridge' and not nl.capabilities['create_bridge']:
        return compat_create_bridge(msg)

    return {'verdict': 'forward', 'data': imsg.data}


@map_enoent
@sync
def manage_team(msg):
    if msg['header']['type'] != RTM_NEWLINK:
        raise ValueError('wrong command type')

    config = {
        'device': msg.get_attr('IFLA_IFNAME'),
        'runner': {'name': 'activebackup'},
        'link_watch': {'name': 'ethtool'},
    }

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


@sync
def compat_create_bridge(msg):
    name = msg.get_attr('IFLA_IFNAME')
    with open(os.devnull, 'w') as fnull:
        subprocess.check_call(
            ['brctl', 'addbr', name], stdout=fnull, stderr=fnull
        )


@sync
def compat_create_bond(msg):
    name = msg.get_attr('IFLA_IFNAME')
    with open(_BONDING_MASTERS, 'w') as f:
        f.write('+%s' % (name))


def compat_set_bond(name, cmd, value):
    # FIXME: join with bridge
    # FIXME: use internal IO, not bash
    t = 'echo %s >/sys/class/net/%s/bonding/%s'
    with open(os.devnull, 'w') as fnull:
        return subprocess.call(
            ['bash', '-c', t % (value, name, cmd)], stdout=fnull, stderr=fnull
        )


def compat_set_bridge(name, cmd, value):
    t = 'echo %s >/sys/class/net/%s/bridge/%s'
    with open(os.devnull, 'w') as fnull:
        return subprocess.call(
            ['bash', '-c', t % (value, name, cmd)], stdout=fnull, stderr=fnull
        )


@sync
def compat_del_bridge(msg):
    name = msg.get_attr('IFLA_IFNAME')
    with open(os.devnull, 'w') as fnull:
        subprocess.check_call(['ip', 'link', 'set', 'dev', name, 'down'])
        subprocess.check_call(
            ['brctl', 'delbr', name], stdout=fnull, stderr=fnull
        )


@sync
def compat_del_bond(msg):
    name = msg.get_attr('IFLA_IFNAME')
    subprocess.check_call(['ip', 'link', 'set', 'dev', name, 'down'])
    with open(_BONDING_MASTERS, 'w') as f:
        f.write('-%s' % (name))


def compat_bridge_port(cmd, master, port, nl):
    if nl.capabilities['create_bridge']:
        return True
    with open(os.devnull, 'w') as fnull:
        subprocess.check_call(
            ['brctl', '%sif' % (cmd), master, port], stdout=fnull, stderr=fnull
        )


def compat_bond_port(cmd, master, port, nl):
    if nl.capabilities['create_bond']:
        return True
    remap = {'add': '+', 'del': '-'}
    cmd = remap[cmd]
    with open(_BONDING_SLAVES % (master), 'w') as f:
        f.write('%s%s' % (cmd, port))


def compat_get_master(name):
    f = None

    for i in (_BRIDGE_MASTER, _BONDING_MASTER):
        try:
            try:
                f = open(i % (name))
            except UnicodeEncodeError:
                # a special case with python3 on Ubuntu 14
                f = open(i % (name.encode('utf-8')))
            break
        except IOError:
            pass

    if f is not None:
        master = int(f.read())
        f.close()
        return master


def get_interface_type(name):
    '''
    Utility function to get interface type.

    Unfortunately, we can not rely on RTNL or even ioctl().
    RHEL doesn't support interface type in RTNL and doesn't
    provide extended (private) interface flags via ioctl().

    Args:
    * name (str): interface name

    Returns:
    * False -- sysfs info unavailable
    * None -- type not known
    * str -- interface type:
        - 'bond'
        - 'bridge'
    '''
    # FIXME: support all interface types? Right now it is
    # not needed
    try:
        ifattrs = os.listdir('/sys/class/net/%s/' % (name))
    except OSError as e:
        if e.errno == 2:
            return 'unknown'
        else:
            raise

    if 'bonding' in ifattrs:
        return 'bond'
    elif 'bridge' in ifattrs:
        return 'bridge'
    else:
        return 'unknown'
