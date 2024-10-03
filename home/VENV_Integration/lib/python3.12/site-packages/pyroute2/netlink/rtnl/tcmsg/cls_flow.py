'''
flow
++++

Flow filter supports two types of modes::
    - map
    - hash

    # Prepare a Qdisc with fq-codel
    ip.tc("add", "fq_codel", ifb0,
          parent=0x10001, handle=0x10010)

    # Create flow filter with hash mode
    # Single:
    keys = "src"
    # Multi (comma separated list of keys):
    keys = "src,nfct-src"
    ip.tc("add-filter", "flow", ifb0,
          mode="hash", keys=keys,
          divisor=1024, perturb=60,
          handle=0x10, baseclass=0x10010,
          parent=0x10001)


    # Create flow filter with map mode
    # Simple map dst with no OP:
    ip.tc("add-filter", "flow", ifb0,
    mode="map", key="dst",
    divisor=1024, handle=10
    baseclass=0x10010)

    # Same filter with xor OP:
    ops = [{"op": "xor", "num": 0xFF}]
    ip.tc("add-filter", "flow", ifb0,
    mode="map", key="dst",
    divisor=1024, handle=10
    baseclass=0x10010, ops=ops)

    # Complex one with addend OP (incl. minus support):
    ops = [{"op": "addend", "num": '-192.168.0.0'}]
    ip.tc("add-filter", "flow", ifb0,
    mode="map", key="dst",
    divisor=1024, handle=10
    baseclass=0x10010, ops=ops)

    # Example with multiple OPS:
    ops = [{"op": "and", "num": 0xFF},
           {"op": "rshift", "num": 4}]
    ip.tc("add-filter", "flow", ifb0,
    mode="map", key="dst",
    divisor=1024, handle=10
    baseclass=0x10010, ops=ops)


NOTES:
    When using `map` mode, use the keyword `key` to pass a key.
    When using `hash` mode, use the keyword `keys` to pass a key
    even if there is only one key.
    In `map` mode, the `num` parameter in `OPS` is always an
    integer unless if you use the OP `addend`, which can be
    a string IPv4 address. You can also add a minus sign at
    the beginning of the `num` value even if it is an IPv4
    address.
'''

from socket import htons

from pyroute2 import protocols
from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.common import (
    get_tca_keys,
    get_tca_mode,
    get_tca_ops,
    tc_flow_keys,
    tc_flow_modes,
)
from pyroute2.netlink.rtnl.tcmsg.common_act import get_tca_action, tca_act_prio


def fix_msg(msg, kwarg):
    msg['info'] = htons(
        kwarg.get('protocol', protocols.ETH_P_ALL) & 0xFFFF
    ) | ((kwarg.get('prio', 0) << 16) & 0xFFFF0000)


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (
        ('baseclass', 'TCA_FLOW_BASECLASS'),
        ('divisor', 'TCA_FLOW_DIVISOR'),
        ('perturb', 'TCA_FLOW_PERTURB'),
    )

    if kwarg.get('mode'):
        ret['attrs'].append(['TCA_FLOW_MODE', get_tca_mode(kwarg)])
        if kwarg.get('mode') == 'hash':
            ret['attrs'].append(['TCA_FLOW_KEYS', get_tca_keys(kwarg, 'keys')])

        if kwarg.get('mode') == 'map':
            ret['attrs'].append(['TCA_FLOW_KEYS', get_tca_keys(kwarg, 'key')])
            # Check for OPS presence
            if 'ops' in kwarg:
                get_tca_ops(kwarg, ret['attrs'])

    if kwarg.get('action'):
        ret['attrs'].append(['TCA_FLOW_ACT', get_tca_action(kwarg)])

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            ret['attrs'].append([v, r])

    return ret


class options(nla):
    nla_map = (
        ('TCA_FLOW_UNSPEC', 'none'),
        ('TCA_FLOW_KEYS', 'tca_parse_keys'),
        ('TCA_FLOW_MODE', 'tca_parse_mode'),
        ('TCA_FLOW_BASECLASS', 'uint32'),
        ('TCA_FLOW_RSHIFT', 'uint32'),
        ('TCA_FLOW_ADDEND', 'uint32'),
        ('TCA_FLOW_MASK', 'uint32'),
        ('TCA_FLOW_XOR', 'uint32'),
        ('TCA_FLOW_DIVISOR', 'uint32'),
        ('TCA_FLOW_ACT', 'tca_act_prio'),
        ('TCA_FLOW_POLICE', 'hex'),
        ('TCA_FLOW_EMATCHES', 'hex'),
        ('TCA_FLOW_PERTURB', 'uint32'),
    )

    class tca_parse_mode(nla):
        fields = (('flow_mode', 'I'),)

        def decode(self):
            nla.decode(self)
            for key, value in tc_flow_modes.items():
                if self['flow_mode'] == value:
                    self['flow_mode'] = key
                    break

        def encode(self):
            self['flow_mode'] = self['value']
            nla.encode(self)

    class tca_parse_keys(nla):
        fields = (('flow_keys', 'I'),)

        def decode(self):
            nla.decode(self)

            keys = ''
            for key, value in tc_flow_keys.items():
                if value & self['flow_keys']:
                    keys = '{0},{1}'.format(keys, key)

            self['flow_keys'] = keys.strip(',')

        def encode(self):
            self['flow_keys'] = self['value']
            nla.encode(self)

    tca_act_prio = tca_act_prio
