'''
basic
+++++

Basic filter has multiple types supports.
Examples with ipset matches::

    # Prepare a simple match on an ipset at index 0 src
    # (the first ipset name that appears when running `ipset list`)
    match = [{"kind": "ipset", "index": 0, "mode": "src"}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # The same match but inverted, simply add inverse flag
    match = [{"kind": "ipset", "index": 0, "mode": "src",
              "inverse": True}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Still one ipset but with multiple dimensions:
    # comma separated list of modes
    match = [{"kind": "ipset", "index": 0, "mode": "src,dst"}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Now let's add multiple expressions (ipset 0 src and ipset 1 src)
    match = [{"kind": "ipset", "index": 0, "mode": "src",
              "relation": "and"},
             {"kind": "ipset", "index": 1, "mode": "src"}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # The same works with OR (ipset 0 src or ipset 1 src)
    match = [{"kind": "ipset", "index": 0, "mode": "src",
              "relation": "OR"},
             {"kind": "ipset", "index": 1, "mode": "src"}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)


Examples with cmp matches::

    # Repeating the example given in the man page
    match = [{"kind": "cmp", "layer": 2, "opnd": "gt", "align": "u16",
              "offset": 3, "mask": 0xff00, "value": 20}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Now, the same example but with variations
    # - use layer name instead of enum
    # - use operand sign instead of name
    match = [{"kind": "cmp", "layer": "transport", "opnd": ">","align": "u16",
              "offset": 3, "mask": 0xff00, "value": 20}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Again, the same example with all possible keywords even if they are
    # ignored
    match = [{"kind": "cmp", "layer": "tcp", "opnd": ">", "align": "u16",
              "offset": 3, "mask": 0xff00, "value": 20, "trans": False}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Another example, we want to work at the link layer
    # and filter incoming packets matching hwaddr 00:DE:AD:C0:DE:00
    # OSI model tells us that the source hwaddr is at offset 0 of
    # the link layer.
    # Size of hwaddr is 6-bytes in length, so I use an u32 then an u16
    # to do the complete match
    match = [{"kind": "cmp", "layer": "link", "opnd": "eq", "align": "u32",
              "offset": 0, "mask": 0xffffffff, "value": 0x00DEADC0,
              "relation": "and"},
             {"kind": "cmp", "layer": "link", "opnd": "eq", "align": "u16",
              "offset": 4, "mask": 0xffff, "value": 0xDE00}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # As the man page says, here are the different key-value pairs you can use:
    # "layer": "link" or "eth" or 0
    # "layer": "network" or "ip" or 1
    # "layer": "transport" or "tcp" or 2
    # "opnd": "eq" or "=" or 0
    # "opnd": "gt" or ">" or 1
    # "opnd": "lt" or "<" or 2
    # "align": "u8" or "u16" or "u32"
    # "trans": True or False
    # "offset", "mask" and "value": any integer


Examples with meta matches::

    # Repeating the example given in the man page
    match = [{"kind": "meta", "object":{"kind": "nfmark", "opnd": "gt"},
              "value": 24, "relation": "and"},
             {"kind": "meta", "object":{"kind": "tcindex", "opnd": "eq"},
              "value": 0xf0, "mask": 0xf0}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Now, the same example but with variations
    # - use operand sign instead of name
    match = [{"kind": "meta", "object":{"kind": "nfmark", "opnd": ">"},
              "value": 24, "relation": "and"},
             {"kind": "meta", "object":{"kind": "tcindex", "opnd": "="},
              "value": 0xf0, "mask": 0xf0}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Another example given by the tc helper
    # meta(indev shift 1 eq "ppp")
    match = [{"kind": "meta", "object":{"kind": "dev", "opnd": "eq",
              "shift": 1}, "value": "ppp"}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match)

    # Another example, drop every packets arriving on ifb0
    match = [{"kind": "meta", "object":{"kind": "dev", "opnd": "eq"},
              "value": "ifb0"}]
    ip.tc("add-filter", "basic", ifb0,
          parent=0x10000, classid=0x10010, match=match, action="drop")

    # As the man page says, here are the different key-value pairs you can use:
    # "opnd": "eq" or "=" or 0
    # "opnd": "gt" or ">" or 1
    # "opnd": "lt" or "<" or 2
    # "shift": any integer between 0 and 255 included
    # "kind" object: see `tc filter add dev iface basic match 'meta(list)'`
                     result
    # "value": any string if kind matches 'dev' or 'sk_bound_if',
    #          any integer otherwise

NOTES:
    When not specified, `inverse` flag is set to False.
    Do not specify `relation` keyword on the last expression or
    if there is only one expression.
    `relation` can be written using multiple format:
      "and", "AND", "&&", "or", "OR", "||"

    You can combine multiple different types of ematch. Here is an example::
    match = [{"kind": "cmp", "layer": 2, "opnd": "eq", "align": "u32",
              "offset": 0, "value": 32, "relation": "&&"},
             {"kind": "meta",
              "object":{"kind": "vlan_tag", "opnd": "eq"}, "value": 100,
              "relation": "||"},
             {"kind": "ipset", "index": 0, "mode": "src", "inverse": True}
            ]
'''

import struct
from socket import htons

from pyroute2 import protocols
from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.common_act import get_tca_action, tca_act_prio
from pyroute2.netlink.rtnl.tcmsg.common_ematch import (
    get_tcf_ematches,
    nla_plus_tcf_ematch_opt,
)


def fix_msg(msg, kwarg):
    msg['info'] = htons(
        kwarg.get('protocol', protocols.ETH_P_ALL) & 0xFFFF
    ) | ((kwarg.get('prio', 0) << 16) & 0xFFFF0000)


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (('classid', 'TCA_BASIC_CLASSID'),)

    if kwarg.get('match'):
        ret['attrs'].append(['TCA_BASIC_EMATCHES', get_tcf_ematches(kwarg)])

    if kwarg.get('action'):
        ret['attrs'].append(['TCA_BASIC_ACT', get_tca_action(kwarg)])

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            ret['attrs'].append([v, r])

    return ret


class options(nla):
    nla_map = (
        ('TCA_BASIC_UNSPEC', 'none'),
        ('TCA_BASIC_CLASSID', 'uint32'),
        ('TCA_BASIC_EMATCHES', 'parse_basic_ematch_tree'),
        ('TCA_BASIC_ACT', 'tca_act_prio'),
        ('TCA_BASIC_POLICE', 'hex'),
    )

    class parse_basic_ematch_tree(nla):
        nla_map = (
            ('TCA_EMATCH_TREE_UNSPEC', 'none'),
            ('TCA_EMATCH_TREE_HDR', 'tcf_parse_header'),
            ('TCA_EMATCH_TREE_LIST', '*tcf_parse_list'),
        )

        class tcf_parse_header(nla):
            fields = (('nmatches', 'H'), ('progid', 'H'))

        class tcf_parse_list(nla, nla_plus_tcf_ematch_opt):
            fields = (
                ('matchid', 'H'),
                ('kind', 'H'),
                ('flags', 'H'),
                ('pad', 'H'),
                ('opt', 's'),
            )

            def decode(self):
                nla.decode(self)
                size = 0
                for field in self.fields + self.header:
                    if 'opt' in field:
                        # Ignore this field as it a hack used to brain encoder
                        continue
                    size += struct.calcsize(field[1])

                start = self.offset + size
                end = self.offset + self.length
                data = self.data[start:end]
                self['opt'] = self.parse_ematch_options(self, data)

    tca_act_prio = tca_act_prio
