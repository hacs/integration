'''
Windows systems are not supported, but the library provides some
proof-of-concept how to build an RTNL-compatible core on top of
WinAPI calls.

Only two methods are provided so far. If you're interested in
extending the functionality, you're welcome to propose PRs.

.. warning::
    Using pyroute2 on Windows requires installing `win_inet_pton` module,
    you can use `pip install win_inet_pton`.
'''

import ctypes
import os
from socket import AF_INET

from pyroute2.common import AddrPool, Namespace, dqn2int
from pyroute2.netlink import NLM_F_DUMP, NLM_F_MULTI, NLM_F_REQUEST, NLMSG_DONE
from pyroute2.netlink.proxy import NetlinkProxy
from pyroute2.netlink.rtnl import (
    RTM_GETADDR,
    RTM_GETLINK,
    RTM_GETNEIGH,
    RTM_GETROUTE,
    RTM_NEWADDR,
    RTM_NEWLINK,
    RTM_NEWNEIGH,
    RTM_NEWROUTE,
)
from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.netlink.rtnl.marshal import MarshalRtnl

MAX_ADAPTER_NAME_LENGTH = 256
MAX_ADAPTER_DESCRIPTION_LENGTH = 128
MAX_ADAPTER_ADDRESS_LENGTH = 8


class IP_ADDRESS_STRING(ctypes.Structure):
    pass


PIP_ADDRESS_STRING = ctypes.POINTER(IP_ADDRESS_STRING)
IP_ADDRESS_STRING._fields_ = [
    ('Next', PIP_ADDRESS_STRING),
    ('IpAddress', ctypes.c_byte * 16),
    ('IpMask', ctypes.c_byte * 16),
    ('Context', ctypes.c_ulong),
]


class IP_ADAPTER_INFO(ctypes.Structure):
    pass


PIP_ADAPTER_INFO = ctypes.POINTER(IP_ADAPTER_INFO)
IP_ADAPTER_INFO._fields_ = [
    ('Next', PIP_ADAPTER_INFO),
    ('ComboIndex', ctypes.c_ulong),
    ('AdapterName', ctypes.c_byte * (256 + 4)),
    ('Description', ctypes.c_byte * (128 + 4)),
    ('AddressLength', ctypes.c_uint),
    ('Address', ctypes.c_ubyte * 8),
    ('Index', ctypes.c_ulong),
    ('Type', ctypes.c_uint),
    ('DhcpEnabled', ctypes.c_uint),
    ('CurrentIpAddress', PIP_ADDRESS_STRING),
    ('IpAddressList', IP_ADDRESS_STRING),
    ('GatewayList', IP_ADDRESS_STRING),
    ('DhcpServer', IP_ADDRESS_STRING),
    ('HaveWins', ctypes.c_byte),
    ('PrimaryWinsServer', IP_ADDRESS_STRING),
    ('SecondaryWinsServer', IP_ADDRESS_STRING),
    ('LeaseObtained', ctypes.c_ulong),
    ('LeaseExpires', ctypes.c_ulong),
]


class IPRoute(object):
    def __init__(self, *argv, **kwarg):
        self.marshal = MarshalRtnl()
        send_ns = Namespace(
            self, {'addr_pool': AddrPool(0x10000, 0x1FFFF), 'monitor': False}
        )
        self._sproxy = NetlinkProxy(policy='return', nl=send_ns)
        self.target = kwarg.get('target') or 'localhost'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def clone(self):
        return self

    def close(self, code=None):
        pass

    def bind(self, *argv, **kwarg):
        pass

    def getsockopt(self, *argv, **kwarg):
        return 1024 * 1024

    def sendto_gate(self, msg, addr):
        #
        # handle incoming netlink requests
        #
        # sendto_gate() receives single RTNL messages as objects
        #
        cmd = msg['header']['type']
        flags = msg['header']['flags']
        seq = msg['header']['sequence_number']

        # work only on dump requests for now
        if flags != NLM_F_REQUEST | NLM_F_DUMP:
            return

        #
        if cmd == RTM_GETLINK:
            rtype = RTM_NEWLINK
            ret = self.get_links()
        elif cmd == RTM_GETADDR:
            rtype = RTM_NEWADDR
            ret = self.get_addr()
        elif cmd == RTM_GETROUTE:
            rtype = RTM_NEWROUTE
            ret = self.get_routes()
        elif cmd == RTM_GETNEIGH:
            rtype = RTM_NEWNEIGH
            ret = self.get_neighbours()

        #
        # set response type and finalize the message
        for r in ret:
            r['header']['type'] = rtype
            r['header']['flags'] = NLM_F_MULTI
            r['header']['sequence_number'] = seq

        #
        r = type(msg)()
        r['header']['type'] = NLMSG_DONE
        r['header']['sequence_number'] = seq
        ret.append(r)

        data = b''
        for r in ret:
            r.encode()
            data += r.data
        self._outq.put(data)
        os.write(self._pfdw, b'\0')

    def _GetAdaptersInfo(self):
        ret = {'interfaces': [], 'addresses': []}

        # prepare buffer
        buf = ctypes.create_string_buffer(15000)
        buf_len = ctypes.c_ulong(15000)
        (
            ctypes.windll.iphlpapi.GetAdaptersInfo(
                ctypes.byref(buf), ctypes.byref(buf_len)
            )
        )
        adapter = IP_ADAPTER_INFO.from_address(ctypes.addressof(buf))
        while True:
            mac = ':'.join(['%02x' % x for x in adapter.Address][:6])
            ifname = ctypes.string_at(
                ctypes.addressof(adapter.AdapterName)
            ).decode('utf-8')
            spec = {
                'index': adapter.Index,
                'attrs': (['IFLA_ADDRESS', mac], ['IFLA_IFNAME', ifname]),
            }

            msg = ifinfmsg().load(spec)
            msg['header']['target'] = self.target
            msg['header']['type'] = RTM_NEWLINK
            del msg['value']
            ret['interfaces'].append(msg)

            ipaddr = adapter.IpAddressList
            while True:
                addr = ctypes.string_at(
                    ctypes.addressof(ipaddr.IpAddress)
                ).decode('utf-8')
                mask = ctypes.string_at(
                    ctypes.addressof(ipaddr.IpMask)
                ).decode('utf-8')
                spec = {
                    'index': adapter.Index,
                    'family': AF_INET,
                    'prefixlen': dqn2int(mask),
                    'attrs': (
                        ['IFA_ADDRESS', addr],
                        ['IFA_LOCAL', addr],
                        ['IFA_LABEL', ifname],
                    ),
                }
                msg = ifaddrmsg().load(spec)
                msg['header']['target'] = self.target
                msg['header']['type'] = RTM_NEWADDR
                del msg['value']
                ret['addresses'].append(msg)
                if ipaddr.Next:
                    ipaddr = ipaddr.Next.contents
                else:
                    break

            if adapter.Next:
                adapter = adapter.Next.contents
            else:
                break
        return ret

    def dump(self, groups=None):
        for method in (
            self.get_links,
            self.get_addr,
            self.get_neighbours,
            self.get_routes,
        ):
            for msg in method():
                yield msg

    def get_links(self, *argv, **kwarg):
        '''
        Get network interfaces list::

            >>> pprint(ipr.get_links())
            [{'attrs': (['IFLA_ADDRESS', '52:54:00:7a:8a:49'],
                        ['IFLA_IFNAME',
                         '{F444467B-3549-455D-81F2-AB617C7421AB}']),
              'change': 0,
              'family': 0,
              'flags': 0,
              'header': {},
              'ifi_type': 0,
              'index': 7}]
        '''
        return self._GetAdaptersInfo()['interfaces']

    def get_addr(self, *argv, **kwarg):
        '''
        Get IP addresses::

            >>> pprint(ipr.get_addr())
            [{'attrs': (['IFA_ADDRESS', '192.168.122.81'],
                        ['IFA_LOCAL', '192.168.122.81'],
                        ['IFA_LABEL',
                         '{F444467B-3549-455D-81F2-AB617C7421AB}']),
              'family': <AddressFamily.AF_INET: 2>,
              'flags': 0,
              'header': {},
              'index': 7,
              'prefixlen': 24,
              'scope': 0}]
        '''
        return self._GetAdaptersInfo()['addresses']

    def get_neighbours(self, *argv, **kwarg):
        ret = []
        return ret

    def get_routes(self, *argv, **kwarg):
        ret = []
        return ret


class RawIPRoute(IPRoute):
    pass


class ChaoticIPRoute:
    def __init__(self, *argv, **kwarg):
        raise NotImplementedError()
