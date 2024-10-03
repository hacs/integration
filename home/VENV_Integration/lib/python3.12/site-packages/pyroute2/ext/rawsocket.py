import struct
from ctypes import (
    Structure,
    addressof,
    c_ubyte,
    c_uint,
    c_ushort,
    c_void_p,
    sizeof,
    string_at,
)
from socket import AF_PACKET, SOCK_RAW, SOL_SOCKET, errno, error, htons, socket

from pyroute2.iproute.linux import IPRoute

ETH_P_ALL = 3
SO_ATTACH_FILTER = 26
SO_DETACH_FILTER = 27


total_filter = [[0x06, 0, 0, 0]]


class sock_filter(Structure):
    _fields_ = [
        ('code', c_ushort),  # u16
        ('jt', c_ubyte),  # u8
        ('jf', c_ubyte),  # u8
        ('k', c_uint),
    ]  # u32


class sock_fprog(Structure):
    _fields_ = [('len', c_ushort), ('filter', c_void_p)]


def compile_bpf(code):
    ProgramType = sock_filter * len(code)
    program = ProgramType(*[sock_filter(*line) for line in code])
    sfp = sock_fprog(len(code), addressof(program[0]))
    return string_at(addressof(sfp), sizeof(sfp)), program


class RawSocket(socket):
    '''
    This raw socket binds to an interface and optionally installs a BPF
    filter.
    When created, the socket's buffer is cleared to remove packets that
    arrived before bind() or the BPF filter is installed.  Doing so
    requires calling recvfrom() which may raise an exception if the
    interface is down.
    In order to allow creating the socket when the interface is
    down, the ENETDOWN exception is caught and discarded.
    '''

    fprog = None

    def __init__(self, ifname, bpf=None):
        self.ifname = ifname
        # lookup the interface details
        with IPRoute() as ip:
            for link in ip.get_links():
                if link.get_attr('IFLA_IFNAME') == ifname:
                    break
            else:
                raise IOError(2, 'Link not found')
        self.l2addr = link.get_attr('IFLA_ADDRESS')
        self.ifindex = link['index']
        # bring up the socket
        socket.__init__(self, AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))
        socket.bind(self, (self.ifname, ETH_P_ALL))
        if bpf:
            self.clear_buffer()
            fstring, self.fprog = compile_bpf(bpf)
            socket.setsockopt(self, SOL_SOCKET, SO_ATTACH_FILTER, fstring)
        else:
            self.clear_buffer(remove_total_filter=True)

    def clear_buffer(self, remove_total_filter=False):
        # there is a window of time after the socket has been created and
        # before bind/attaching a filter where packets can be queued onto the
        # socket buffer
        # see comments in function set_kernel_filter() in libpcap's
        # pcap-linux.c. libpcap sets a total filter which does not match any
        # packet.  It then clears what is already in the socket
        # before setting the desired filter
        total_fstring, prog = compile_bpf(total_filter)
        socket.setsockopt(self, SOL_SOCKET, SO_ATTACH_FILTER, total_fstring)
        self.setblocking(0)
        while True:
            try:
                self.recvfrom(0)
            except error as e:
                if e.args[0] == errno.ENETDOWN:
                    # we only get this exception once per down event
                    # there may be more packets left to clean
                    pass
                elif e.args[0] in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    break
                else:
                    raise
        self.setblocking(1)
        if remove_total_filter:
            # total_fstring ignored
            socket.setsockopt(
                self, SOL_SOCKET, SO_DETACH_FILTER, total_fstring
            )

    def csum(self, data):
        if len(data) % 2:
            data += b'\x00'
        csum = sum(
            [
                struct.unpack('>H', data[x * 2 : x * 2 + 2])[0]
                for x in range(len(data) // 2)
            ]
        )
        csum = (csum >> 16) + (csum & 0xFFFF)
        csum += csum >> 16
        return ~csum & 0xFFFF
