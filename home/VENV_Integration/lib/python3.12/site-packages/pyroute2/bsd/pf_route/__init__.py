import socket
import struct

from pyroute2 import config
from pyroute2.common import hexdump
from pyroute2.netlink import nlmsg_base

if config.uname[0] == 'OpenBSD':
    from pyroute2.bsd.pf_route.openbsd import (
        IFF_NAMES,
        IFF_VALUES,
        bsdmsg,
        if_announcemsg,
        if_msg,
        ifa_msg_base,
        ifma_msg_base,
        rt_msg_base,
    )
else:
    from pyroute2.bsd.pf_route.freebsd import (
        IFF_NAMES,
        IFF_VALUES,
        bsdmsg,
        if_announcemsg,
        if_msg,
        ifa_msg_base,
        ifma_msg_base,
        rt_msg_base,
    )


RTAX_MAX = 8


class rt_slot(nlmsg_base):
    __slots__ = ()
    header = (('length', 'B'), ('family', 'B'))


class rt_msg(rt_msg_base):
    __slots__ = ()
    force_mask = False

    class hex(rt_slot):
        def decode(self):
            rt_slot.decode(self)
            length = self['header']['length']
            self['value'] = hexdump(
                self.data[self.offset + 2 : self.offset + length]
            )

    class rt_slot_ifp(rt_slot):
        def decode(self):
            rt_slot.decode(self)
            #
            # Structure
            #     0       1       2       3       4       5       6       7
            # |-------+-------+-------+-------|-------+-------+-------+-------|
            # |  len  |  fam  |    ifindex    |   ?   |  nlen |    padding?   |
            # |-------+-------+-------+-------|-------+-------+-------+-------|
            # | ...
            # | ...
            #
            # len -- sockaddr len
            # fam -- sockaddr family
            # ifindex -- interface index
            # ? -- no idea, probably again some sockaddr related info?
            # nlen -- device name length
            # padding? -- probably structure alignment
            #
            (self['index'], _, name_length) = struct.unpack(
                'HBB', self.data[self.offset + 2 : self.offset + 6]
            )
            self['ifname'] = self.data[
                self.offset + 8 : self.offset + 8 + name_length
            ]

    class rt_slot_addr(rt_slot):
        def decode(self):
            alen = {socket.AF_INET: 4, socket.AF_INET6: 16}
            rt_slot.decode(self)
            #
            # Yksinkertainen: only the sockaddr family (one byte) and the
            # network address.
            #
            # But for netmask it's completely screwed up. E.g.:
            #
            #  ifconfig disc2 10.0.0.1 255.255.255.0 up
            # -->
            #  ... NETMASK: 38:12:00:00:ff:00:00:00:00:00:00:...
            #
            # Why?!
            #
            family = self['header']['family']
            length = self['header']['length']
            if family in (socket.AF_INET, socket.AF_INET6):
                addrlen = alen.get(family, 0)
                data = self.data[self.offset + 4 : self.offset + 4 + addrlen]
                self['address'] = socket.inet_ntop(family, data)
            else:
                # FreeBSD and OpenBSD use different approaches
                # FreeBSD: family == 0x12
                # OpenBSD: family == 0x0
                if self.parent.force_mask and family in (0x0, 0x12):
                    data = self.data[self.offset + 4 : self.offset + 8]
                    data = data + b'\0' * (4 - len(data))
                    self['address'] = socket.inet_ntop(socket.AF_INET, data)
                else:
                    self['raw'] = self.data[self.offset : self.offset + length]

    def decode(self):
        bsdmsg.decode(self)
        offset = self.sockaddr_offset
        for i in range(RTAX_MAX):
            if self['rtm_addrs'] & (1 << i):
                handler = getattr(self, self.ifa_slots[i][1])
                slot = handler(self.data[offset:], parent=self)
                slot.decode()
                offset += slot['header']['length']
                self[self.ifa_slots[i][0]] = slot


class ifa_msg(ifa_msg_base, rt_msg):
    force_mask = True


class ifma_msg(ifma_msg_base, rt_msg):
    pass


__all__ = (
    bsdmsg,
    if_msg,
    rt_msg,
    ifa_msg,
    ifma_msg,
    if_announcemsg,
    IFF_NAMES,
    IFF_VALUES,
)
