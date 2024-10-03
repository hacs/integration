'''
Utility to parse ifconfig, netstat etc.

PF_ROUTE may be effectively used only to get notifications. To fetch
info from the system we have to use ioctl or external utilities.

Maybe some day it will be ioctl. For now it's ifconfig and netstat.
'''

import re
import socket
import subprocess


class CMD(object):
    cmd = ['uname', '-s']

    def __init__(self, cmd=None):
        if cmd is not None:
            self.cmd = cmd

    def run(self):
        '''
        Run the command and get stdout
        '''
        stdout = stderr = ''
        try:
            process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except Exception:
            process.kill()
        finally:
            process.wait()
        return stdout


class Route(CMD):
    cmd = ['netstat', '-rn']

    def parse(self, data):
        ret = []
        family = 0
        if isinstance(data, bytes):
            data = data.decode('utf-8')

        for line in data.split('\n'):
            if line == 'Internet:':
                family = socket.AF_INET
            elif line == 'Internet6:':
                # do NOT support IPv6 routes yet
                break

            sl = line.split()
            if len(sl) < 4:
                continue
            if sl[0] == 'Destination':
                # create the field map
                fmap = dict([(x[1], x[0]) for x in enumerate(sl)])
                if 'Netif' not in fmap:
                    fmap['Netif'] = fmap['Iface']
                continue

            route = {'family': family, 'attrs': []}

            #
            # RTA_DST
            dst = sl[fmap['Destination']]
            if dst != 'default':
                dst = dst.split('/')
                if len(dst) == 2:
                    dst, dst_len = dst
                else:
                    dst = dst[0]
                    if family == socket.AF_INET:
                        dst_len = 32
                    else:
                        dst_len = 128
                dst = dst.split('%')
                if len(dst) == 2:
                    dst, _ = dst
                else:
                    dst = dst[0]

                dst = '%s%s' % (dst, '.0' * (3 - dst.count('.')))
                route['dst_len'] = int(dst_len)
                route['attrs'].append(['RTA_DST', dst])
            #
            # RTA_GATEWAY
            gw = sl[fmap['Gateway']]
            if not gw.startswith('link') and not gw.find(':') >= 0:
                route['attrs'].append(['RTA_GATEWAY', sl[fmap['Gateway']]])
            #
            # RTA_OIF -- do not resolve it here! just save
            route['ifname'] = sl[fmap['Netif']]

            ret.append(route)
        return ret


class ARP(CMD):
    cmd = ['arp', '-an']

    def parse(self, data):
        ret = []
        f_dst = 1
        f_addr = 3
        f_ifname = 5
        if isinstance(data, bytes):
            data = data.decode('utf-8')

        for line in data.split('\n'):
            sl = line.split()
            if not sl:
                continue

            if sl[0] == 'Host':
                f_dst = 0
                f_addr = 1
                f_ifname = 2
                continue

            dst = sl[f_dst].strip('(').strip(')')
            addr = sl[f_addr].strip('(').strip(')')
            if addr == 'incomplete':
                continue

            ifname = sl[f_ifname]
            neighbour = {
                'ifindex': 0,
                'ifname': ifname,
                'family': 2,
                'attrs': [['NDA_DST', dst], ['NDA_LLADDR', addr]],
            }
            ret.append(neighbour)
        return ret


class Ifconfig(CMD):
    match = {'NR': re.compile(r'^\b').match}
    cmd = ['ifconfig', '-a']

    def parse_line(self, line):
        '''
        Dumb line parser:

        "key1 value1 key2 value2 something"
          -> {"key1": "value1", "key2": "value2"}
        '''
        ret = {}
        cursor = 0
        while cursor < (len(line) - 1):
            ret[line[cursor]] = line[cursor + 1]
            cursor += 2
        return ret

    def parse(self, data):
        '''
        Parse ifconfig output into netlink-compatible dicts::

            from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
            from pyroute2.bsd.util import Ifconfig

            def links()
                ifc = Ifconfig()
                data = ifc.run()
                for name, spec in ifc.parse(data)["links"].items():
                    yield ifinfmsg().load(spec)
        '''
        ifname = None
        kind = None
        ret = {'links': {}, 'addrs': {}}
        idx = 0
        info_data = {'attrs': None}

        if isinstance(data, bytes):
            data = data.decode('utf-8')

        for line in data.split('\n'):
            sl = line.split()
            pl = self.parse_line(sl)

            # type-specific
            if kind == 'gre' and 'inet' in sl and not info_data['attrs']:
                # first "inet" -- low-level addresses
                arrow = None
                try:
                    arrow = sl.index('->')
                except ValueError:
                    try:
                        arrow = sl.index('-->')
                    except ValueError:
                        continue
                if arrow is not None:
                    info_data['attrs'] = [
                        ('IFLA_GRE_LOCAL', sl[arrow - 1]),
                        ('IFLA_GRE_REMOTE', sl[arrow + 1]),
                    ]
                continue

            # first line -- ifname, flags, mtu
            if self.match['NR'](line):
                ifname = sl[0][:-1]
                kind = None
                idx += 1
                ret['links'][ifname] = link = {'index': idx, 'attrs': []}
                ret['addrs'][ifname] = addrs = []
                link['attrs'].append(['IFLA_IFNAME', ifname])
                #
                if ifname[:3] == 'gre':
                    kind = 'gre'
                    info_data = {'attrs': []}
                    linkinfo = {
                        'attrs': [
                            ('IFLA_INFO_KIND', kind),
                            ('IFLA_INFO_DATA', info_data),
                        ]
                    }
                    link['attrs'].append(['IFLA_LINKINFO', linkinfo])

                # extract flags
                try:
                    link['flags'] = int(sl[1].split('=')[1].split('<')[0])
                except Exception:
                    pass

                # extract MTU
                if 'mtu' in pl:
                    link['attrs'].append(['IFLA_MTU', int(pl['mtu'])])

            elif 'ether' in pl:
                link['attrs'].append(['IFLA_ADDRESS', pl['ether']])

            elif 'lladdr' in pl:
                link['attrs'].append(['IFLA_ADDRESS', pl['lladdr']])

            elif 'index' in pl:
                idx = int(pl['index'])
                link['index'] = int(pl['index'])

            elif 'inet' in pl:
                if ('netmask' not in pl) or ('inet' not in pl):
                    print(pl)
                    continue
                addr = {
                    'index': idx,
                    'family': socket.AF_INET,
                    'prefixlen': bin(int(pl['netmask'], 16)).count('1'),
                    'attrs': [['IFA_ADDRESS', pl['inet']]],
                }
                if 'broadcast' in pl:
                    addr['attrs'].append(['IFA_BROADCAST', pl['broadcast']])
                addrs.append(addr)
            elif 'inet6' in pl:
                if ('prefixlen' not in pl) or ('inet6' not in pl):
                    print(pl)
                    continue
                addr = {
                    'index': idx,
                    'family': socket.AF_INET6,
                    'prefixlen': int(pl['prefixlen']),
                    'attrs': [['IFA_ADDRESS', pl['inet6'].split('%')[0]]],
                }
                if 'scopeid' in pl:
                    addr['scope'] = int(pl['scopeid'], 16)
                addrs.append(addr)

        return ret
