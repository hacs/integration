'''
IPv4 DHCP socket
================

'''

from pyroute2.common import AddrPool
from pyroute2.dhcp.dhcp4msg import dhcp4msg
from pyroute2.ext.rawsocket import RawSocket
from pyroute2.protocols import ethmsg, ip4msg, udp4_pseudo_header, udpmsg


def listen_udp_port(port=68):
    # pre-scripted BPF code that matches UDP port
    bpf_code = [
        [40, 0, 0, 12],
        [21, 0, 8, 2048],
        [48, 0, 0, 23],
        [21, 0, 6, 17],
        [40, 0, 0, 20],
        [69, 4, 0, 8191],
        [177, 0, 0, 14],
        [72, 0, 0, 16],
        [21, 0, 1, port],
        [6, 0, 0, 65535],
        [6, 0, 0, 0],
    ]
    return bpf_code


class DHCP4Socket(RawSocket):
    '''
    Parameters:

    * ifname -- interface name to work on

    This raw socket binds to an interface and installs BPF filter
    to get only its UDP port. It can be used in poll/select and
    provides also the context manager protocol, so can be used in
    `with` statements.

    It does not provide any DHCP state machine, and does not inspect
    DHCP packets, it is totally up to you. No default values are
    provided here, except `xid` -- DHCP transaction ID. If `xid` is
    not provided, DHCP4Socket generates it for outgoing messages.
    '''

    def __init__(self, ifname, port=68):
        RawSocket.__init__(self, ifname, listen_udp_port(port))
        self.port = port
        # Create xid pool
        #
        # Every allocated xid will be released automatically after 1024
        # alloc() calls, there is no need to call free(). Minimal xid == 16
        self.xid_pool = AddrPool(minaddr=16, release=1024)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def put(self, msg=None, dport=67):
        '''
        Put DHCP message. Parameters:

        * msg -- dhcp4msg instance
        * dport -- DHCP server port

        If `msg` is not provided, it is constructed as default
        BOOTREQUEST + DHCPDISCOVER.

        Examples::

            sock.put(dhcp4msg({'op': BOOTREQUEST,
                               'chaddr': 'ff:11:22:33:44:55',
                               'options': {'message_type': DHCPREQUEST,
                                           'parameter_list': [1, 3, 6, 12, 15],
                                           'requested_ip': '172.16.101.2',
                                           'server_id': '172.16.101.1'}}))

        The method returns dhcp4msg that was sent, so one can get from
        there `xid` (transaction id) and other details.
        '''
        # DHCP layer
        dhcp = msg or dhcp4msg({'chaddr': self.l2addr})

        # dhcp transaction id
        if dhcp['xid'] is None:
            dhcp['xid'] = self.xid_pool.alloc()

        data = dhcp.encode().buf

        # UDP layer
        udp = udpmsg(
            {'sport': self.port, 'dport': dport, 'len': 8 + len(data)}
        )
        udph = udp4_pseudo_header(
            {'dst': '255.255.255.255', 'len': 8 + len(data)}
        )
        udp['csum'] = self.csum(udph.encode().buf + udp.encode().buf + data)
        udp.reset()

        # IPv4 layer
        ip4 = ip4msg(
            {'len': 20 + 8 + len(data), 'proto': 17, 'dst': '255.255.255.255'}
        )
        ip4['csum'] = self.csum(ip4.encode().buf)
        ip4.reset()

        # MAC layer
        eth = ethmsg(
            {'dst': 'ff:ff:ff:ff:ff:ff', 'src': self.l2addr, 'type': 0x800}
        )

        data = eth.encode().buf + ip4.encode().buf + udp.encode().buf + data
        self.send(data)
        dhcp.reset()
        return dhcp

    def get(self):
        '''
        Get the next incoming packet from the socket and try
        to decode it as IPv4 DHCP. No analysis is done here,
        only MAC/IPv4/UDP headers are stripped out, and the
        rest is interpreted as DHCP.
        '''
        (data, addr) = self.recvfrom(4096)
        eth = ethmsg(buf=data).decode()
        ip4 = ip4msg(buf=data, offset=eth.offset).decode()
        udp = udpmsg(buf=data, offset=ip4.offset).decode()
        return dhcp4msg(buf=data, offset=udp.offset).decode()
