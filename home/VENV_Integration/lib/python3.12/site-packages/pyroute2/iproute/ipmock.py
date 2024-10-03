import copy
import errno
import queue
import socket
import struct
from itertools import count

from pyroute2.lab import LAB_API
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.nlsocket import NetlinkSocketBase, Stats
from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.netlink.rtnl.marshal import MarshalRtnl
from pyroute2.netlink.rtnl.rtmsg import rtmsg
from pyroute2.requests.address import AddressFieldFilter, AddressIPRouteFilter
from pyroute2.requests.link import LinkFieldFilter
from pyroute2.requests.main import RequestProcessor
from pyroute2.requests.route import RouteFieldFilter

interface_counter = count(3)


class MockLink:
    def __init__(
        self,
        index,
        ifname='',
        address='00:00:00:00:00:00',
        broadcast='ff:ff:ff:ff:ff:ff',
        perm_address=None,
        flags=1,
        rx_bytes=0,
        tx_bytes=0,
        rx_packets=0,
        tx_packets=0,
        mtu=0,
        qdisc='noqueue',
        kind=None,
        link=None,
        vlan_id=None,
        master=0,
        br_max_age=0,
        br_forward_delay=0,
        alt_ifname_list=None,
    ):
        self.index = index
        self.ifname = ifname
        self.flags = flags
        self.address = address
        self.broadcast = broadcast
        self.perm_address = perm_address
        self.rx_bytes = rx_bytes
        self.tx_bytes = tx_bytes
        self.rx_packets = rx_packets
        self.tx_packets = tx_packets
        self.mtu = mtu
        self.qdisc = qdisc
        self.kind = kind
        self.link = link
        self.vlan_id = vlan_id
        self.master = master
        self.br_max_age = br_max_age
        self.br_forward_delay = br_forward_delay
        self.alt_ifname_list = alt_ifname_list or []

    def export(self):
        ret = {
            'attrs': [
                ['IFLA_IFNAME', self.ifname],
                ['IFLA_TXQLEN', 1000],
                ['IFLA_OPERSTATE', 'UNKNOWN'],
                ['IFLA_LINKMODE', 0],
                ['IFLA_MTU', self.mtu],
                ['IFLA_GROUP', 0],
                ['IFLA_PROMISCUITY', 0],
                ['IFLA_NUM_TX_QUEUES', 1],
                ['IFLA_GSO_MAX_SEGS', 65535],
                ['IFLA_GSO_MAX_SIZE', 65536],
                ['IFLA_GRO_MAX_SIZE', 65536],
                ['IFLA_NUM_RX_QUEUES', 1],
                ['IFLA_CARRIER', 1],
                ['IFLA_QDISC', self.qdisc],
                ['IFLA_CARRIER_CHANGES', 0],
                ['IFLA_CARRIER_UP_COUNT', 0],
                ['IFLA_CARRIER_DOWN_COUNT', 0],
                ['IFLA_PROTO_DOWN', 0],
                [
                    'IFLA_MAP',
                    {
                        'base_addr': 0,
                        'dma': 0,
                        'irq': 0,
                        'mem_end': 0,
                        'mem_start': 0,
                        'port': 0,
                    },
                ],
                ['IFLA_ADDRESS', self.address],
                ['IFLA_BROADCAST', self.broadcast],
                [
                    'IFLA_STATS64',
                    {
                        'collisions': 0,
                        'multicast': 0,
                        'rx_bytes': self.rx_bytes,
                        'rx_compressed': 0,
                        'rx_crc_errors': 0,
                        'rx_dropped': 0,
                        'rx_errors': 0,
                        'rx_fifo_errors': 0,
                        'rx_frame_errors': 0,
                        'rx_length_errors': 0,
                        'rx_missed_errors': 0,
                        'rx_over_errors': 0,
                        'rx_packets': self.rx_packets,
                        'tx_aborted_errors': 0,
                        'tx_bytes': self.tx_bytes,
                        'tx_carrier_errors': 0,
                        'tx_compressed': 0,
                        'tx_dropped': 0,
                        'tx_errors': 0,
                        'tx_fifo_errors': 0,
                        'tx_heartbeat_errors': 0,
                        'tx_packets': self.tx_packets,
                        'tx_window_errors': 0,
                    },
                ],
                [
                    'IFLA_STATS',
                    {
                        'collisions': 0,
                        'multicast': 0,
                        'rx_bytes': self.rx_bytes,
                        'rx_compressed': 0,
                        'rx_crc_errors': 0,
                        'rx_dropped': 0,
                        'rx_errors': 0,
                        'rx_fifo_errors': 0,
                        'rx_frame_errors': 0,
                        'rx_length_errors': 0,
                        'rx_missed_errors': 0,
                        'rx_over_errors': 0,
                        'rx_packets': self.rx_packets,
                        'tx_aborted_errors': 0,
                        'tx_bytes': self.tx_bytes,
                        'tx_carrier_errors': 0,
                        'tx_compressed': 0,
                        'tx_dropped': 0,
                        'tx_errors': 0,
                        'tx_fifo_errors': 0,
                        'tx_heartbeat_errors': 0,
                        'tx_packets': self.tx_packets,
                        'tx_window_errors': 0,
                    },
                ],
                ['IFLA_XDP', {'attrs': [['IFLA_XDP_ATTACHED', None]]}],
                (
                    'IFLA_PERM_ADDRESS',
                    self.perm_address if self.perm_address else self.address,
                ),
                [
                    'IFLA_AF_SPEC',
                    {
                        'attrs': [
                            [
                                'AF_INET',
                                {
                                    'accept_local': 0,
                                    'accept_redirects': 1,
                                    'accept_source_route': 0,
                                    'arp_accept': 0,
                                    'arp_announce': 0,
                                    'arp_ignore': 0,
                                    'arp_notify': 0,
                                    'arpfilter': 0,
                                    'bootp_relay': 0,
                                    'dummy': 65672,
                                    'force_igmp_version': 0,
                                    'forwarding': 1,
                                    'log_martians': 0,
                                    'mc_forwarding': 0,
                                    'medium_id': 0,
                                    'nopolicy': 1,
                                    'noxfrm': 1,
                                    'promote_secondaries': 1,
                                    'proxy_arp': 0,
                                    'proxy_arp_pvlan': 0,
                                    'route_localnet': 0,
                                    'rp_filter': 2,
                                    'secure_redirects': 1,
                                    'send_redirects': 1,
                                    'shared_media': 1,
                                    'src_vmark': 0,
                                    'tag': 0,
                                },
                            ]
                        ]
                    },
                ],
            ],
            'change': 0,
            'event': 'RTM_NEWLINK',
            'family': 0,
            'flags': self.flags,
            'header': {
                'error': None,
                'flags': 2,
                'length': 1364,
                'pid': 303471,
                'sequence_number': 260,
                'stats': Stats(qsize=0, delta=0, delay=0),
                'target': 'localhost',
                'type': 16,
            },
            'ifi_type': 772,
            'index': self.index,
            'state': 'up' if self.flags & 1 else 'down',
        }
        linkinfo = None
        infodata = {'attrs': []}
        if self.kind is not None:
            linkinfo = {'attrs': [('IFLA_INFO_KIND', self.kind)]}
        if self.kind not in (None, 'dummy'):
            linkinfo['attrs'].append(('IFLA_INFO_DATA', infodata))
        if self.kind == 'vlan':
            infodata['attrs'].append(('IFLA_VLAN_ID', self.vlan_id))
            ret['attrs'].append(('IFLA_LINK', self.link))
        if self.kind == 'bridge':
            infodata['attrs'].extend(
                (
                    ('IFLA_BR_MAX_AGE', self.br_max_age),
                    ('IFLA_BR_FORWARD_DELAY', self.br_forward_delay),
                )
            )
        if linkinfo is not None:
            ret['attrs'].append(('IFLA_LINKINFO', linkinfo))
        if self.master != 0:
            ret['attrs'].append(('IFLA_MASTER', self.master))
        return ret


class MockAddress:
    def __init__(
        self,
        index,
        address,
        prefixlen,
        broadcast=None,
        label=None,
        family=2,
        local=None,
        **kwarg,
    ):
        self.address = address
        self.local = local
        self.broadcast = broadcast
        self.prefixlen = prefixlen
        self.index = index
        self.label = label
        self.family = family

    def export(self):
        ret = {
            'family': self.family,
            'prefixlen': self.prefixlen,
            'flags': 0,
            'scope': 0,
            'index': self.index,
            'attrs': [
                ('IFA_ADDRESS', self.address),
                ('IFA_LOCAL', self.local if self.local else self.address),
                ('IFA_FLAGS', 512),
                (
                    'IFA_CACHEINFO',
                    {
                        'ifa_preferred': 3476,
                        'ifa_valid': 3476,
                        'cstamp': 138655779,
                        'tstamp': 141288674,
                    },
                ),
            ],
            'header': {
                'length': 88,
                'type': 20,
                'flags': 2,
                'sequence_number': 256,
                'pid': 320994,
                'error': None,
                'target': 'localhost',
                'stats': Stats(qsize=0, delta=0, delay=0),
            },
            'event': 'RTM_NEWADDR',
        }
        if self.label is not None:
            ret['attrs'].append(('IFA_LABEL', self.label))
        if self.broadcast is not None:
            ret['attrs'].append(('IFA_BROADCAST', self.broadcast))
        return ret


class MockRoute:
    def __init__(
        self,
        dst,
        oif,
        gateway=None,
        prefsrc=None,
        family=2,
        dst_len=24,
        table=254,
        scope=253,
        proto=2,
        route_type=1,
        **kwarg,
    ):
        self.dst = dst
        self.gateway = gateway
        self.prefsrc = prefsrc
        self.oif = oif
        self.family = family
        self.dst_len = dst_len
        self.table = table
        self.scope = scope
        self.proto = proto
        self.route_type = route_type
        self.priority = kwarg.get('priority', 0)
        self.tos = kwarg.get('tos', 0)
        self._type = kwarg.get('type', 2)

    def export(self):
        ret = {
            'family': self.family,
            'dst_len': self.dst_len,
            'src_len': 0,
            'tos': self.tos,
            'table': self.table if self.table <= 255 else 252,
            'proto': self.proto,
            'scope': self.scope,
            'type': self._type,
            'flags': 0,
            'attrs': [('RTA_TABLE', self.table), ('RTA_OIF', self.oif)],
            'header': {
                'length': 60,
                'type': 24,
                'flags': 2,
                'sequence_number': 255,
                'pid': 325359,
                'error': None,
                'target': 'localhost',
                'stats': Stats(qsize=0, delta=0, delay=0),
            },
            'event': 'RTM_NEWROUTE',
        }
        if self.dst is not None:
            ret['attrs'].append(('RTA_DST', self.dst))
        if self.prefsrc is not None:
            ret['attrs'].append(('RTA_PREFSRC', self.prefsrc))
        if self.gateway is not None:
            ret['attrs'].append(('RTA_GATEWAY', self.gateway))
        if self.priority > 0:
            ret['attrs'].append(('RTA_PRIORITY', self.priority))
        return ret


presets = {
    'default': {
        'links': [
            MockLink(
                index=1,
                ifname='lo',
                address='00:00:00:00:00:00',
                broadcast='00:00:00:00:00:00',
                rx_bytes=43309665,
                tx_bytes=43309665,
                rx_packets=173776,
                tx_packets=173776,
                mtu=65536,
                qdisc='noqueue',
            ),
            MockLink(
                index=2,
                ifname='eth0',
                address='52:54:00:72:58:b2',
                broadcast='ff:ff:ff:ff:ff:ff',
                rx_bytes=175340,
                tx_bytes=175340,
                rx_packets=10251,
                tx_packets=10251,
                mtu=1500,
                qdisc='fq_codel',
            ),
        ],
        'addr': [
            MockAddress(
                index=1,
                label='lo',
                address='127.0.0.1',
                broadcast='127.255.255.255',
                prefixlen=8,
            ),
            MockAddress(
                index=2,
                label='eth0',
                address='192.168.122.28',
                broadcast='192.168.122.255',
                prefixlen=24,
            ),
        ],
        'routes': [
            MockRoute(
                dst=None,
                gateway='192.168.122.1',
                oif=2,
                dst_len=0,
                table=254,
                scope=0,
            ),
            MockRoute(dst='192.168.122.0', oif=2, dst_len=24, table=254),
            MockRoute(
                dst='127.0.0.0', oif=1, dst_len=8, table=255, route_type=2
            ),
            MockRoute(
                dst='127.0.0.1', oif=1, dst_len=32, table=255, route_type=2
            ),
            MockRoute(
                dst='127.255.255.255',
                oif=1,
                dst_len=32,
                table=255,
                route_type=3,
            ),
            MockRoute(
                dst='192.168.122.28',
                oif=2,
                dst_len=32,
                table=255,
                route_type=2,
            ),
            MockRoute(
                dst='192.168.122.255',
                oif=2,
                dst_len=32,
                table=255,
                route_type=3,
            ),
        ],
    },
    'netns': {
        'links': [
            MockLink(
                index=1,
                ifname='lo',
                address='00:00:00:00:00:00',
                broadcast='00:00:00:00:00:00',
                rx_bytes=43309665,
                tx_bytes=43309665,
                rx_packets=173776,
                tx_packets=173776,
                mtu=65536,
                qdisc='noqueue',
            )
        ],
        'addr': [
            MockAddress(
                index=1,
                label='lo',
                address='127.0.0.1',
                broadcast='127.255.255.255',
                prefixlen=8,
            )
        ],
        'routes': [
            MockRoute(
                dst='127.0.0.0', oif=1, dst_len=8, table=255, route_type=2
            ),
            MockRoute(
                dst='127.0.0.1', oif=1, dst_len=32, table=255, route_type=2
            ),
            MockRoute(
                dst='127.255.255.255',
                oif=1,
                dst_len=32,
                table=255,
                route_type=3,
            ),
        ],
    },
}


class IPRoute(LAB_API, NetlinkSocketBase):
    def __init__(self, *argv, **kwarg):
        super().__init__()
        self.marshal = MarshalRtnl()
        self.target = kwarg.get('target')
        self.preset = copy.deepcopy(
            presets[kwarg['preset'] if 'preset' in kwarg else 'default']
        )
        self.buffer_queue = queue.Queue(maxsize=512)
        self.input_from_buffer_queue = True

    def bind(self, async_cache=True, clone_socket=True):
        pass

    def dump(self, groups=None):
        for method in (self.get_links, self.get_addr, self.get_routes):
            for msg in method():
                yield msg

    def _get_dump(self, dump, msg_class):
        for data in dump:
            loader = msg_class()
            loader.load(data.export())
            loader.encode()
            msg = msg_class()
            msg.data = loader.data
            msg.decode()
            if self.target is not None:
                msg['header']['target'] = self.target
            yield msg

    def _match(self, mode, obj, spec):
        keys = {
            'address': ['address', 'prefixlen', 'index', 'family'],
            'link': ['index', 'ifname'],
            'route': ['dst', 'dst_len', 'oif', 'priority'],
        }
        check = False
        for key in keys[mode]:
            if key in spec:
                check = True
                if spec[key] != getattr(obj, key):
                    return False
        if not check:
            return False
        return True

    def addr(self, command, **spec):
        if command == 'dump':
            return self.get_addr()
        request = RequestProcessor(context=spec, prime=spec)
        request.apply_filter(AddressFieldFilter())
        request.apply_filter(AddressIPRouteFilter(command))
        request.finalize()
        address = None

        for address in self.preset['addr']:
            if self._match('address', address, request):
                if command == 'add':
                    raise NetlinkError(errno.EEXIST, 'address exists')
                break
        else:
            if command == 'del':
                raise NetlinkError(errno.ENOENT, 'address does not exist')
            address = MockAddress(**request)

        if command == 'add':
            for link in self.preset['links']:
                if link.index == request['index']:
                    break
            else:
                raise NetlinkError(errno.ENOENT, 'link not found')
            address.label = link.ifname
            self.preset['addr'].append(address)
            for msg in self._get_dump([address], ifaddrmsg):
                msg.encode()
                self.buffer_queue.put(msg.data)
        elif command == 'del':
            self.preset['addr'].remove(address)
            for msg in self._get_dump([address], ifaddrmsg):
                msg['header']['type'] = 21
                msg['event'] = 'RTM_DELADDR'
                msg.encode()
                self.buffer_queue.put(msg.data)

        return self._get_dump([address], ifaddrmsg)

    def link(self, command, **spec):
        if command == 'dump':
            return self.get_links()
        if 'state' in spec:
            spec['flags'] = 1 if spec.pop('state') == 'up' else 0
        request = RequestProcessor(context=spec, prime=spec)
        request.apply_filter(LinkFieldFilter())
        request.finalize()

        for interface in self.preset['links']:
            if self._match('link', interface, request):
                if command == 'add':
                    raise NetlinkError(errno.EEXIST, 'interface exists')
                break
        else:
            index = next(interface_counter)
            if 'address' not in request:
                request['address'] = f'00:11:22:33:44:{index:02}'
            if 'index' not in request:
                request['index'] = index
            if 'tflags' in request:
                del request['tflags']
            if 'target' in request:
                del request['target']
            interface = MockLink(**request)

        if command == 'add':
            self.preset['links'].append(interface)
            for msg in self._get_dump([interface], ifinfmsg):
                msg.encode()
                self.buffer_queue.put(msg.data)
        elif command == 'set':
            for key, value in request.items():
                if hasattr(interface, key):
                    setattr(interface, key, value)
            for msg in self._get_dump([interface], ifinfmsg):
                msg.encode()
                self.buffer_queue.put(msg.data)

        return self._get_dump([interface], ifinfmsg)

    def route(self, command, **spec):
        if command == 'dump':
            return self.get_routes()
        request = RequestProcessor(context=spec, prime=spec)
        request.apply_filter(RouteFieldFilter())
        request.finalize()

        for route in self.preset['routes']:
            if self._match('route', route, request):
                if command == 'add':
                    raise NetlinkError(errno.EEXIST, 'route exists')
                break
        else:
            if command == 'del':
                raise NetlinkError(errno.ENOENT, 'route does not exist')
            if 'tflags' in request:
                del request['tflags']
            if 'target' in request:
                del request['target']
            if 'multipath' in request:
                del request['multipath']
            if 'metrics' in request:
                del request['metrics']
            if 'deps' in request:
                del request['deps']
            if 'oif' not in request:
                (gateway,) = struct.unpack(
                    '>I', socket.inet_aton(request['gateway'])
                )
                for route in self.preset['routes']:
                    if route.dst is None:
                        continue
                    (dst,) = struct.unpack('>I', socket.inet_aton(route.dst))
                    if (gateway & (0xFFFFFFFF << (32 - route.dst_len))) == dst:
                        request['oif'] = route.oif
                        break
                else:
                    raise NetlinkError(errno.ENOENT, 'no route to the gateway')
            route = MockRoute(**request)

        if command == 'add':
            self.preset['routes'].append(route)
            for msg in self._get_dump([route], rtmsg):
                msg.encode()
                self.buffer_queue.put(msg.data)
        elif command == 'set':
            for key, value in request.items():
                if hasattr(route, key):
                    setattr(route, key, value)
            for msg in self._get_dump([route], rtmsg):
                msg.encode()
                self.buffer_queue.put(msg.data)
        elif command == 'del':
            self.preset['routes'].remove(route)
            for msg in self._get_dump([route], rtmsg):
                msg['header']['type'] = 25
                msg['event'] = 'RTM_DELROUTE'
                msg.encode()
                self.buffer_queue.put(msg.data)

        return self._get_dump([route], rtmsg)

    def get_addr(self):
        return self._get_dump(self.preset['addr'], ifaddrmsg)

    def get_links(self):
        return self._get_dump(self.preset['links'], ifinfmsg)

    def get_routes(self):
        return self._get_dump(self.preset['routes'], rtmsg)


class ChaoticIPRoute:
    def __init__(self, *argv, **kwarg):
        raise NotImplementedError()


class RawIPRoute:
    def __init__(self, *argv, **kwarg):
        raise NotImplementedError()
