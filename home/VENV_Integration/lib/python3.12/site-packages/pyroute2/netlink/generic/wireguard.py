'''

Usage::

    # Imports
    from pyroute2 import NDB, WireGuard

    IFNAME = 'wg1'

    # Create a WireGuard interface
    with NDB() as ndb:
        with ndb.interfaces.create(kind='wireguard', ifname=IFNAME) as link:
            link.add_ip('10.0.0.1/24')
            link.set(state='up')

    # Create WireGuard object
    wg = WireGuard()

    # Add a WireGuard configuration + first peer
    peer = {'public_key': 'TGFHcm9zc2VCaWNoZV9DJ2VzdExhUGx1c0JlbGxlPDM=',
            'endpoint_addr': '8.8.8.8',
            'endpoint_port': 8888,
            'persistent_keepalive': 15,
            'allowed_ips': ['10.0.0.0/24', '8.8.8.8/32']}
    wg.set(IFNAME, private_key='RCdhcHJlc0JpY2hlLEplU2VyYWlzTGFQbHVzQm9ubmU=',
           fwmark=0x1337, listen_port=2525, peer=peer)

    # Add second peer with preshared key
    peer = {'public_key': 'RCdBcHJlc0JpY2hlLFZpdmVMZXNQcm9iaW90aXF1ZXM=',
            'preshared_key': 'Pz8/V2FudFRvVHJ5TXlBZXJvR3Jvc3NlQmljaGU/Pz8=',
            'endpoint_addr': '8.8.8.8',
            'endpoint_port': 9999,
            'persistent_keepalive': 25,
            'allowed_ips': ['::/0']}
    wg.set(IFNAME, peer=peer)

    # Delete second peer
    peer = {'public_key': 'RCdBcHJlc0JpY2hlLFZpdmVMZXNQcm9iaW90aXF1ZXM=',
            'remove': True}
    wg.set(IFNAME, peer=peer)

    # Get information of the interface
    wg.info(IFNAME)

    # Get specific value from the interface
    wg.info(IFNAME)[0].get('WGDEVICE_A_PRIVATE_KEY')


NOTES:

* The `get()` method always returns iterable
* Using `set()` method only requires an interface name
* The `peer` structure is described as follow::

    struct peer_s {
        public_key:            # Base64 public key - required
        remove:                # Boolean - optional
        preshared_key:         # Base64 preshared key - optional
        endpoint_addr:         # IPv4 or IPv6 endpoint - optional
        endpoint_port :        # endpoint Port - required only if endpoint_addr
        persistent_keepalive:  # time in seconds to send keep alive - optional
        allowed_ips:           # list of CIDRs allowed - optional
    }
'''

import errno
import logging
import struct
from base64 import b64decode, b64encode
from binascii import a2b_hex
from socket import AF_INET, AF_INET6, inet_ntop, inet_pton
from time import ctime

from pyroute2.netlink import (
    NLA_F_NESTED,
    NLM_F_ACK,
    NLM_F_DUMP,
    NLM_F_REQUEST,
    genlmsg,
    nla,
)
from pyroute2.netlink.generic import GenericNetlinkSocket

# Defines from uapi/wireguard.h
WG_GENL_NAME = "wireguard"
WG_GENL_VERSION = 1
WG_KEY_LEN = 32

# WireGuard Device commands
WG_CMD_GET_DEVICE = 0
WG_CMD_SET_DEVICE = 1

# Wireguard Device attributes
WGDEVICE_A_UNSPEC = 0
WGDEVICE_A_IFINDEX = 1
WGDEVICE_A_IFNAME = 2
WGDEVICE_A_PRIVATE_KEY = 3
WGDEVICE_A_PUBLIC_KEY = 4
WGDEVICE_A_FLAGS = 5
WGDEVICE_A_LISTEN_PORT = 6
WGDEVICE_A_FWMARK = 7
WGDEVICE_A_PEERS = 8

# WireGuard Device flags
WGDEVICE_F_REPLACE_PEERS = 1

# WireGuard Allowed IP attributes
WGALLOWEDIP_A_UNSPEC = 0
WGALLOWEDIP_A_FAMILY = 1
WGALLOWEDIP_A_IPADDR = 2
WGALLOWEDIP_A_CIDR_MASK = 3

# WireGuard Peer flags
WGPEER_F_REMOVE_ME = 0
WGPEER_F_REPLACE_ALLOWEDIPS = 1
WGPEER_F_UPDATE_ONLY = 2

# Specific defines
WG_MAX_PEERS = 1000
WG_MAX_ALLOWEDIPS = 1000


class wgmsg(genlmsg):
    prefix = 'WGDEVICE_A_'

    nla_map = (
        ('WGDEVICE_A_UNSPEC', 'none'),
        ('WGDEVICE_A_IFINDEX', 'uint32'),
        ('WGDEVICE_A_IFNAME', 'asciiz'),
        ('WGDEVICE_A_PRIVATE_KEY', 'parse_wg_key'),
        ('WGDEVICE_A_PUBLIC_KEY', 'parse_wg_key'),
        ('WGDEVICE_A_FLAGS', 'uint32'),
        ('WGDEVICE_A_LISTEN_PORT', 'uint16'),
        ('WGDEVICE_A_FWMARK', 'uint32'),
        ('WGDEVICE_A_PEERS', '*wgdevice_peer'),
    )

    class wgdevice_peer(nla):
        prefix = 'WGPEER_A_'

        nla_flags = NLA_F_NESTED
        nla_map = (
            ('WGPEER_A_UNSPEC', 'none'),
            ('WGPEER_A_PUBLIC_KEY', 'parse_peer_key'),
            ('WGPEER_A_PRESHARED_KEY', 'parse_peer_key'),
            ('WGPEER_A_FLAGS', 'uint32'),
            ('WGPEER_A_ENDPOINT', 'parse_endpoint'),
            ('WGPEER_A_PERSISTENT_KEEPALIVE_INTERVAL', 'uint16'),
            ('WGPEER_A_LAST_HANDSHAKE_TIME', 'parse_handshake_time'),
            ('WGPEER_A_RX_BYTES', 'uint64'),
            ('WGPEER_A_TX_BYTES', 'uint64'),
            ('WGPEER_A_ALLOWEDIPS', '*wgpeer_allowedip'),
            ('WGPEER_A_PROTOCOL_VERSION', 'uint32'),
        )

        class parse_peer_key(nla):
            fields = (('key', '32s'),)

            def decode(self):
                nla.decode(self)
                self['value'] = b64encode(self['key'])

            def encode(self):
                self['key'] = b64decode(self['value'])
                nla.encode(self)

        @staticmethod
        def parse_endpoint(nla, *argv, **kwarg):
            family = AF_INET
            if 'data' in kwarg:
                # decoding, fetch the famliy from the NLA data
                data = kwarg['data']
                offset = kwarg['offset']
                family = struct.unpack('H', data[offset + 4 : offset + 6])[0]
            elif kwarg['value']['addr'].find(':') > -1:
                # encoding, setup family from the addr format
                family = AF_INET6

            if family == AF_INET:
                return nla.endpoint_ipv4
            else:
                return nla.endpoint_ipv6

        class endpoint_ipv4(nla):
            fields = (
                ('family', 'H'),
                ('port', '>H'),
                ('addr', '4s'),
                ('__pad', '8x'),
            )

            def decode(self):
                nla.decode(self)
                self['addr'] = inet_ntop(AF_INET, self['addr'])

            def encode(self):
                self['family'] = AF_INET
                self['addr'] = inet_pton(AF_INET, self['addr'])
                nla.encode(self)

        class endpoint_ipv6(nla):
            fields = (
                ('family', 'H'),
                ('port', '>H'),
                ('flowinfo', '>I'),
                ('addr', '16s'),
                ('scope_id', '>I'),
            )

            def decode(self):
                nla.decode(self)
                self['addr'] = inet_ntop(AF_INET6, self['addr'])

            def encode(self):
                self['family'] = AF_INET6
                self['addr'] = inet_pton(AF_INET6, self['addr'])
                nla.encode(self)

        class parse_handshake_time(nla):
            fields = (('tv_sec', 'Q'), ('tv_nsec', 'Q'))

            def decode(self):
                nla.decode(self)
                self['latest handshake'] = ctime(self['tv_sec'])

        class wgpeer_allowedip(nla):
            prefix = 'WGALLOWEDIP_A_'

            nla_flags = NLA_F_NESTED
            nla_map = (
                ('WGALLOWEDIP_A_UNSPEC', 'none'),
                ('WGALLOWEDIP_A_FAMILY', 'uint16'),
                ('WGALLOWEDIP_A_IPADDR', 'hex'),
                ('WGALLOWEDIP_A_CIDR_MASK', 'uint8'),
            )

            def decode(self):
                nla.decode(self)
                family = self.get_attr('WGALLOWEDIP_A_FAMILY')
                if family is None:
                    # Prevent when decode() is called without attrs because all
                    # datas transfered to 'value' entry.
                    #  {'attrs': [], 'value': [{'attrs' ...
                    return
                ipaddr = self.get_attr('WGALLOWEDIP_A_IPADDR')
                cidr = self.get_attr('WGALLOWEDIP_A_CIDR_MASK')
                self['addr'] = '{ipaddr}/{cidr}'.format(
                    ipaddr=inet_ntop(family, a2b_hex(ipaddr.replace(':', ''))),
                    cidr=cidr,
                )

    class parse_wg_key(nla):
        fields = (('key', '32s'),)

        def decode(self):
            nla.decode(self)
            self['value'] = b64encode(self['key'])

        def encode(self):
            self['key'] = b64decode(self['value'])
            nla.encode(self)


class WireGuard(GenericNetlinkSocket):
    def __init__(self, *args, **kwargs):
        GenericNetlinkSocket.__init__(self, *args, **kwargs)
        self.bind(WG_GENL_NAME, wgmsg)

    def info(self, interface):
        msg = wgmsg()
        msg['cmd'] = WG_CMD_GET_DEVICE
        msg['attrs'].append(['WGDEVICE_A_IFNAME', interface])
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def set(
        self,
        interface,
        listen_port=None,
        fwmark=None,
        private_key=None,
        peer=None,
    ):
        msg = wgmsg()
        msg['attrs'].append(['WGDEVICE_A_IFNAME', interface])

        if private_key is not None:
            self._wg_test_key(private_key)
            msg['attrs'].append(['WGDEVICE_A_PRIVATE_KEY', private_key])

        if listen_port is not None:
            msg['attrs'].append(['WGDEVICE_A_LISTEN_PORT', listen_port])

        if fwmark is not None:
            msg['attrs'].append(['WGDEVICE_A_FWMARK', fwmark])

        if peer is not None:
            self._wg_set_peer(msg, peer)

        # Message attributes
        msg['cmd'] = WG_CMD_SET_DEVICE
        msg['version'] = WG_GENL_VERSION
        msg['header']['type'] = self.prid
        msg['header']['flags'] = NLM_F_REQUEST | NLM_F_ACK
        msg['header']['pid'] = self.pid
        msg.encode()
        self.sendto(msg.data, (0, 0))
        msg = self.get()[0]
        err = msg['header'].get('error', None)
        if err is not None:
            if hasattr(err, 'code') and err.code == errno.ENOENT:
                logging.error(
                    'Generic netlink protocol %s not found' % self.prid
                )
                logging.error('Please check if the protocol module is loaded')
            raise err
        return msg

    def _wg_test_key(self, key):
        try:
            if len(b64decode(key)) != WG_KEY_LEN:
                raise ValueError('Invalid WireGuard key length')
        except TypeError:
            raise ValueError('Failed to decode Base64 key')

    def _wg_set_peer(self, msg, peer):
        attrs = []
        wg_peer = [{'attrs': attrs}]
        if 'public_key' not in peer:
            raise ValueError('Peer Public key required')

        # Check public key validity
        public_key = peer['public_key']
        self._wg_test_key(public_key)
        attrs.append(['WGPEER_A_PUBLIC_KEY', public_key])

        # If peer removal is set to True
        if 'remove' in peer and peer['remove']:
            attrs.append(['WGPEER_A_FLAGS', WGDEVICE_F_REPLACE_PEERS])
            msg['attrs'].append(['WGDEVICE_A_PEERS', wg_peer])
            return

        # Set Endpoint
        if 'endpoint_addr' in peer and 'endpoint_port' in peer:
            attrs.append(
                [
                    'WGPEER_A_ENDPOINT',
                    {
                        'addr': peer['endpoint_addr'],
                        'port': peer['endpoint_port'],
                    },
                ]
            )

        # Set Preshared key
        if 'preshared_key' in peer:
            pkey = peer['preshared_key']
            self._wg_test_key(pkey)
            attrs.append(['WGPEER_A_PRESHARED_KEY', pkey])

        # Set Persistent Keepalive time
        if 'persistent_keepalive' in peer:
            keepalive = peer['persistent_keepalive']
            attrs.append(['WGPEER_A_PERSISTENT_KEEPALIVE_INTERVAL', keepalive])

        # Set Peer flags
        attrs.append(['WGPEER_A_FLAGS', WGPEER_F_UPDATE_ONLY])

        # Set allowed IPs
        if 'allowed_ips' in peer:
            allowed_ips = self._wg_build_allowedips(peer['allowed_ips'])
            attrs.append(['WGPEER_A_ALLOWEDIPS', allowed_ips])

        msg['attrs'].append(['WGDEVICE_A_PEERS', wg_peer])

    def _wg_build_allowedips(self, allowed_ips):
        ret = []

        for index, ip in enumerate(allowed_ips):
            allowed_ip = []
            ret.append({'attrs': allowed_ip})

            if ip.find("/") == -1:
                raise ValueError('No CIDR set in allowed ip #{}'.format(index))

            addr, mask = ip.split('/')

            family = AF_INET if addr.find(":") == -1 else AF_INET6
            allowed_ip.append(['WGALLOWEDIP_A_FAMILY', family])
            allowed_ip.append(
                ['WGALLOWEDIP_A_IPADDR', inet_pton(family, addr)]
            )
            allowed_ip.append(['WGALLOWEDIP_A_CIDR_MASK', int(mask)])

        return ret
