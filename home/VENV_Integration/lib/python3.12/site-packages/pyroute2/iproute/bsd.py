'''
The library provides very basic RTNL API for BSD systems
via protocol emulation. Only getters are supported yet, no
setters.

BSD employs PF_ROUTE sockets to send notifications about
network object changes, but the protocol doesn not allow
changing links/addresses/etc like Netlink.

To change network setting one have to rely on system calls
or external tools. Thus IPRoute on BSD systems is not as
effective as on Linux, where all the changes are done via
Netlink.

The monitoring started with `bind()` is implemented as an
implicit thread, started by the `bind()` call. This is done
to have only one notification FD, used both for normal calls
and notifications. This allows to use IPRoute objects in
poll/select calls.

On Linux systems RTNL API is provided by the netlink protocol,
so no implicit threads are started by default to monitor the
system updates. `IPRoute.bind(...)` may start the async cache
thread, but only when asked explicitly::

    #
    # Normal monitoring. Always starts monitoring thread on
    # FreeBSD / OpenBSD, no threads on Linux.
    #
    with IPRoute() as ipr:
        ipr.bind()
        ...

    #
    # Monitoring with async cache. Always starts cache thread
    # on Linux, ignored on FreeBSD / OpenBSD.
    #
    with IPRoute() as ipr:
        ipr.bind(async_cache=True)
        ...

On all the supported platforms, be it Linux or BSD, the
`IPRoute.recv(...)` method returns valid netlink RTNL raw binary
payload and `IPRoute.get(...)` returns parsed RTNL messages.
'''

import errno
import os
import select
import struct
import threading

from pyroute2 import config
from pyroute2.bsd.pf_route import IFF_VALUES
from pyroute2.bsd.rtmsocket import RTMSocket
from pyroute2.bsd.util import ARP, Ifconfig, Route
from pyroute2.common import AddrPool, Namespace
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
from pyroute2.netlink.rtnl.ifinfmsg import IFF_NAMES, ifinfmsg
from pyroute2.netlink.rtnl.marshal import MarshalRtnl
from pyroute2.netlink.rtnl.ndmsg import ndmsg
from pyroute2.netlink.rtnl.rtmsg import rtmsg

try:
    import queue
except ImportError:
    import Queue as queue


class IPRoute(object):
    def __init__(self, *argv, **kwarg):
        if 'ssh' in kwarg:
            self._ssh = ['ssh', kwarg.pop('ssh')]
        else:
            self._ssh = []
        async_qsize = kwarg.get('async_qsize')
        self._ifc = Ifconfig(cmd=self._ssh + ['ifconfig', '-a'])
        self._arp = ARP(cmd=self._ssh + ['arp', '-an'])
        self._route = Route(cmd=self._ssh + ['netstat', '-rn'])
        self.marshal = MarshalRtnl()
        self.target = kwarg.get('target') or 'localhost'
        send_ns = Namespace(
            self, {'addr_pool': AddrPool(0x10000, 0x1FFFF), 'monitor': False}
        )
        self._sproxy = NetlinkProxy(policy='return', nl=send_ns)
        self._mon_th = None
        self._rtm = None
        self._brd_socket = None
        self._pfdr, self._pfdw = os.pipe()  # notify external poll/select
        self._ctlr, self._ctlw = os.pipe()  # notify monitoring thread
        self._outq = queue.Queue(maxsize=async_qsize or config.async_qsize)
        self._system_lock = threading.Lock()
        self.closed = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def clone(self):
        return self

    def close(self, code=errno.ECONNRESET):
        with self._system_lock:
            if self.closed.is_set():
                return

            if self._mon_th is not None:
                os.write(self._ctlw, b'\0')
                self._mon_th.join()
                self._rtm.close()

            if code > 0:
                self._outq.put(struct.pack('IHHQIQQ', 28, 2, 0, 0, code, 0, 0))
            os.write(self._pfdw, b'\0')
            for ep in (self._pfdr, self._pfdw, self._ctlr, self._ctlw):
                try:
                    os.close(ep)
                except OSError:
                    pass
            self.closed.set()

    def bind(self, *argv, **kwarg):
        with self._system_lock:
            if self._mon_th is not None:
                return

            if self._ssh:
                return

            self._mon_th = threading.Thread(
                target=self._monitor_thread, name='PF_ROUTE monitoring'
            )
            self._mon_th.setDaemon(True)
            self._mon_th.start()

    def _monitor_thread(self):
        # Monitoring thread to convert arriving PF_ROUTE data into
        # the netlink format, enqueue it and notify poll/select.
        self._rtm = RTMSocket(output='netlink')
        inputs = [self._rtm.fileno(), self._ctlr]
        outputs = []
        while True:
            try:
                events, _, _ = select.select(inputs, outputs, inputs)
            except:
                continue
            for fd in events:
                if fd == self._ctlr:
                    # Main thread <-> monitor thread protocol is
                    # pretty simple: discard the data and terminate
                    # the monitor thread.
                    os.read(self._ctlr, 1)
                    return
                else:
                    # Read the data from the socket and queue it
                    msg = self._rtm.get()
                    if msg is not None:
                        msg.encode()
                        self._outq.put(msg.data)
                        # Notify external poll/select
                        os.write(self._pfdw, b'\0')

    def fileno(self):
        # Every time when some new data arrives, one should write
        # into self._pfdw one byte to kick possible poll/select.
        #
        # Resp. recv() discards one byte from self._pfdr each call.
        return self._pfdr

    def get(self):
        data = self.recv()
        return self.marshal.parse(data)

    def recv(self, bufsize=None):
        os.read(self._pfdr, 1)
        return self._outq.get()

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

    # 8<---------------------------------------------------------------
    #
    def dump(self, groups=None):
        '''
        Iterate all the objects -- links, routes, addresses etc.
        '''
        for method in (
            self.get_links,
            self.get_addr,
            self.get_neighbours,
            self.get_routes,
        ):
            for msg in method():
                yield msg

    # 8<---------------------------------------------------------------

    def get_links(self, *argv, **kwarg):
        ret = []
        data = self._ifc.run()
        parsed = self._ifc.parse(data)
        for name, spec in parsed['links'].items():
            msg = ifinfmsg().load(spec)
            msg['header']['type'] = RTM_NEWLINK
            msg['header']['target'] = self.target
            del msg['value']
            flags = msg['flags']
            new_flags = 0
            for value, name in IFF_VALUES.items():
                if value & flags and name in IFF_NAMES:
                    new_flags |= IFF_NAMES[name]
            msg['flags'] = new_flags
            ret.append(msg)
        return ret

    def get_addr(self, *argv, **kwarg):
        ret = []
        data = self._ifc.run()
        parsed = self._ifc.parse(data)
        for name, specs in parsed['addrs'].items():
            for spec in specs:
                msg = ifaddrmsg().load(spec)
                msg['header']['type'] = RTM_NEWADDR
                msg['header']['target'] = self.target
                del msg['value']
                ret.append(msg)
        return ret

    def get_neighbours(self, *argv, **kwarg):
        ifc = self._ifc.parse(self._ifc.run())
        arp = self._arp.parse(self._arp.run())
        ret = []
        for spec in arp:
            if spec['ifname'] not in ifc['links']:
                continue
            spec['ifindex'] = ifc['links'][spec['ifname']]['index']
            msg = ndmsg().load(spec)
            msg['header']['type'] = RTM_NEWNEIGH
            msg['header']['target'] = self.target
            del msg['value']
            ret.append(msg)
        return ret

    def get_routes(self, *argv, **kwarg):
        ifc = self._ifc.parse(self._ifc.run())
        rta = self._route.parse(self._route.run())
        ret = []
        for spec in rta:
            if spec['ifname'] not in ifc['links']:
                continue
            idx = ifc['links'][spec['ifname']]['index']
            spec['attrs'].append(['RTA_OIF', idx])
            msg = rtmsg().load(spec)
            msg['header']['type'] = RTM_NEWROUTE
            msg['header']['target'] = self.target
            del msg['value']
            ret.append(msg)
        return ret


class RawIPRoute(IPRoute):
    pass


class ChaoticIPRoute:
    def __init__(self, *argv, **kwarg):
        raise NotImplementedError()
