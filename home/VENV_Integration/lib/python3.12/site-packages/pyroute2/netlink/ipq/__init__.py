'''
IPQ -- userspace firewall
=========================

Netlink family for dealing with `QUEUE` iptables
target. All the packets routed to the target
`QUEUE` should be handled by a userspace program
and the program should response with a verdict.
E.g., the verdict can be `NF_DROP` and in that
case the packet will be silently dropped, or
`NF_ACCEPT`, and the packet will be pass the
rule.
'''

from pyroute2.netlink import NLM_F_REQUEST, nlmsg
from pyroute2.netlink.nlsocket import Marshal, NetlinkSocket

# constants
IFNAMSIZ = 16
IPQ_MAX_PAYLOAD = 0x800

# IPQ messages
IPQM_BASE = 0x10
IPQM_MODE = IPQM_BASE + 1
IPQM_VERDICT = IPQM_BASE + 2
IPQM_PACKET = IPQM_BASE + 3

# IPQ modes
IPQ_COPY_NONE = 0
IPQ_COPY_META = 1
IPQ_COPY_PACKET = 2

# verdict types
NF_DROP = 0
NF_ACCEPT = 1
NF_STOLEN = 2
NF_QUEUE = 3
NF_REPEAT = 4
NF_STOP = 5


class ipq_base_msg(nlmsg):
    def decode(self):
        nlmsg.decode(self)
        self['payload'] = self.buf.read(self['data_len'])

    def encode(self):
        init = self.buf.tell()
        nlmsg.encode(self)
        if 'payload' in self:
            self.buf.write(self['payload'])
            self.update_length(init)


class ipq_packet_msg(ipq_base_msg):
    fields = (
        ('packet_id', 'L'),
        ('mark', 'L'),
        ('timestamp_sec', 'l'),
        ('timestamp_usec', 'l'),
        ('hook', 'I'),
        ('indev_name', '%is' % IFNAMSIZ),
        ('outdev_name', '%is' % IFNAMSIZ),
        ('hw_protocol', '>H'),
        ('hw_type', 'H'),
        ('hw_addrlen', 'B'),
        ('hw_addr', '6B'),
        ('__pad', '9x'),
        ('data_len', 'I'),
        ('__pad', '4x'),
    )


class ipq_mode_msg(nlmsg):
    pack = 'struct'
    fields = (
        ('value', 'B'),
        ('__pad', '7x'),
        ('range', 'I'),
        ('__pad', '12x'),
    )


class ipq_verdict_msg(ipq_base_msg):
    pack = 'struct'
    fields = (
        ('value', 'I'),
        ('__pad', '4x'),
        ('id', 'L'),
        ('data_len', 'I'),
        ('__pad', '4x'),
    )


class MarshalIPQ(Marshal):
    msg_map = {
        IPQM_MODE: ipq_mode_msg,
        IPQM_VERDICT: ipq_verdict_msg,
        IPQM_PACKET: ipq_packet_msg,
    }


class IPQSocket(NetlinkSocket):
    '''
    Low-level socket interface. Provides all the
    usual socket does, can be used in poll/select,
    doesn't create any implicit threads.
    '''

    def bind(self, mode=IPQ_COPY_PACKET):
        '''
        Bind the socket and performs IPQ mode configuration.
        The only parameter is mode, the default value is
        IPQ_COPY_PACKET (copy all the packet data).
        '''
        NetlinkSocket.bind(self, groups=0, pid=0)
        self.register_policy(MarshalIPQ.msg_map)
        msg = ipq_mode_msg()
        msg['value'] = mode
        msg['range'] = IPQ_MAX_PAYLOAD
        msg['header']['type'] = IPQM_MODE
        msg['header']['flags'] = NLM_F_REQUEST
        msg.encode()
        self.sendto(msg.data, (0, 0))

    def verdict(self, seq, v):
        '''
        Issue a verdict `v` for a packet `seq`.
        '''
        msg = ipq_verdict_msg()
        msg['value'] = v
        msg['id'] = seq
        msg['data_len'] = 0
        msg['header']['type'] = IPQM_VERDICT
        msg['header']['flags'] = NLM_F_REQUEST
        msg.encode()
        self.sendto(msg.buf.getvalue(), (0, 0))
