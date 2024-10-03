'''
u32
+++

Filters can take an `action` argument, which affects the packet
behavior when the filter matches. Currently the gact, bpf, and police
action types are supported, and can be attached to the u32 and bpf
filter types::

    # An action can be a simple string, which translates to a gact type
    action = "drop"

    # Or it can be an explicit type (these are equivalent)
    action = dict(kind="gact", action="drop")

    # There can also be a chain of actions, which depend on the return
    # value of the previous action.
    action = [
        dict(kind="bpf", fd=fd, name=name, action="ok"),
        dict(kind="police", rate="10kbit", burst=10240, limit=0),
        dict(kind="gact", action="ok"),
    ]

    # Add the action to a u32 match-all filter
    ip.tc("add", "htb", eth0, 0x10000, default=0x200000)
    ip.tc("add-filter", "u32", eth0,
          parent=0x10000,
          prio=10,
          protocol=protocols.ETH_P_ALL,
          target=0x10020,
          keys=["0x0/0x0+0"],
          action=action)

    # Add two more filters: One to send packets with a src address of
    # 192.168.0.1/32 into 1:10 and the second to send packets  with a
    # dst address of 192.168.0.0/24 into 1:20
    ip.tc("add-filter", "u32", eth0,
        parent=0x10000,
        prio=10,
        protocol=protocols.ETH_P_IP,
        target=0x10010,
        keys=["0xc0a80001/0xffffffff+12"])
        # 0xc0a800010 = 192.168.0.1
        # 0xffffffff = 255.255.255.255 (/32)
        # 12 = Source network field bit offset

    ip.tc("add-filter", "u32", eth0,
        parent=0x10000,
        prio=10,
        protocol=protocols.ETH_P_IP,
        target=0x10020,
        keys=["0xc0a80000/0xffffff00+16"])
        # 0xc0a80000 = 192.168.0.0
        # 0xffffff00 = 255.255.255.0 (/24)
        # 16 = Destination network field bit offset
'''

import struct
from socket import htons

from pyroute2.netlink import nla, nlmsg
from pyroute2.netlink.rtnl.tcmsg.act_police import (
    get_parameters as ap_parameters,
)
from pyroute2.netlink.rtnl.tcmsg.act_police import nla_plus_police
from pyroute2.netlink.rtnl.tcmsg.common_act import get_tca_action, tca_act_prio


def fix_msg(msg, kwarg):
    msg['info'] = htons(kwarg.get('protocol', 0) & 0xFFFF) | (
        (kwarg.get('prio', 0) << 16) & 0xFFFF0000
    )


def get_parameters(kwarg):
    ret = {'attrs': []}

    if kwarg.get('rate'):
        ret['attrs'].append(['TCA_U32_POLICE', ap_parameters(kwarg)])
    elif kwarg.get('action'):
        ret['attrs'].append(['TCA_U32_ACT', get_tca_action(kwarg)])

    ret['attrs'].append(['TCA_U32_CLASSID', kwarg['target']])
    ret['attrs'].append(['TCA_U32_SEL', {'keys': kwarg['keys']}])

    return ret


class options(nla, nla_plus_police):
    nla_map = (
        ('TCA_U32_UNSPEC', 'none'),
        ('TCA_U32_CLASSID', 'uint32'),
        ('TCA_U32_HASH', 'uint32'),
        ('TCA_U32_LINK', 'hex'),
        ('TCA_U32_DIVISOR', 'uint32'),
        ('TCA_U32_SEL', 'u32_sel'),
        ('TCA_U32_POLICE', 'police'),
        ('TCA_U32_ACT', 'tca_act_prio'),
        ('TCA_U32_INDEV', 'hex'),
        ('TCA_U32_PCNT', 'u32_pcnt'),
        ('TCA_U32_MARK', 'u32_mark'),
    )

    tca_act_prio = tca_act_prio

    class u32_sel(nla):
        fields = (
            ('flags', 'B'),
            ('offshift', 'B'),
            ('nkeys', 'B'),
            ('__align', 'x'),
            ('offmask', '>H'),
            ('off', 'H'),
            ('offoff', 'h'),
            ('hoff', 'h'),
            ('hmask', '>I'),
        )

        class u32_key(nlmsg):
            header = None
            fields = (
                ('key_mask', '>I'),
                ('key_val', '>I'),
                ('key_off', 'i'),
                ('key_offmask', 'i'),
            )

        def encode(self):
            '''
            Key sample::

                'keys': ['0x0006/0x00ff+8',
                         '0x0000/0xffc0+2',
                         '0x5/0xf+0',
                         '0x10/0xff+33']

                => 00060000/00ff0000 + 8
                   05000000/0f00ffc0 + 0
                   00100000/00ff0000 + 32
            '''

            def cut_field(key, separator):
                '''
                split a field from the end of the string
                '''
                field = '0'
                pos = key.find(separator)
                new_key = key
                if pos > 0:
                    field = key[pos + 1 :]
                    new_key = key[:pos]
                return (new_key, field)

            # 'header' array to pack keys to
            header = [(0, 0) for i in range(256)]

            keys = []
            # iterate keys and pack them to the 'header'
            for key in self['keys']:
                # TODO tags: filter
                (key, nh) = cut_field(key, '@')  # FIXME: do not ignore nh
                (key, offset) = cut_field(key, '+')
                offset = int(offset, 0)
                # a little trick: if you provide /00ff+8, that
                # really means /ff+9, so we should take it into
                # account
                (key, mask) = cut_field(key, '/')
                if mask[:2] == '0x':
                    mask = mask[2:]
                    while True:
                        if mask[:2] == '00':
                            offset += 1
                            mask = mask[2:]
                        else:
                            break
                    mask = '0x' + mask
                mask = int(mask, 0)
                value = int(key, 0)
                bits = 24
                if mask == 0 and value == 0:
                    key = self.u32_key(data=self.data)
                    key['key_off'] = offset
                    key['key_mask'] = mask
                    key['key_val'] = value
                    keys.append(key)
                for bmask in struct.unpack('4B', struct.pack('>I', mask)):
                    if bmask > 0:
                        bvalue = (value & (bmask << bits)) >> bits
                        header[offset] = (bvalue, bmask)
                        offset += 1
                    bits -= 8

            # recalculate keys from 'header'
            key = None
            value = 0
            mask = 0
            for offset in range(256):
                (bvalue, bmask) = header[offset]
                if bmask > 0 and key is None:
                    key = self.u32_key(data=self.data)
                    key['key_off'] = offset
                    key['key_mask'] = 0
                    key['key_val'] = 0
                    bits = 24
                if key is not None and bits >= 0:
                    key['key_mask'] |= bmask << bits
                    key['key_val'] |= bvalue << bits
                    bits -= 8
                    if bits < 0 or offset == 255:
                        keys.append(key)
                        key = None

            if not keys:
                raise ValueError('no keys specified')
            self['nkeys'] = len(keys)
            # FIXME: do not hardcode flags :)
            self['flags'] = 1

            nla.encode(self)
            offset = self.offset + 20  # 4 bytes header + 16 bytes fields
            for key in keys:
                key.offset = offset
                key.encode()
                offset += 16  # keys haven't header
            self.length = offset - self.offset
            struct.pack_into('H', self.data, self.offset, offset - self.offset)

        def decode(self):
            nla.decode(self)
            offset = self.offset + 16
            self['keys'] = []
            nkeys = self['nkeys']
            while nkeys:
                key = self.u32_key(data=self.data, offset=offset)
                key.decode()
                offset += 16
                self['keys'].append(key)
                nkeys -= 1

    class u32_mark(nla):
        fields = (('val', 'I'), ('mask', 'I'), ('success', 'I'))

    class u32_pcnt(nla):
        fields = (('rcnt', 'Q'), ('rhit', 'Q'), ('kcnts', 'Q'))
