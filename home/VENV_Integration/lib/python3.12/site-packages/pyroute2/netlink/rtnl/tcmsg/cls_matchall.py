from socket import htons

from pyroute2 import protocols
from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.common_act import get_tca_action, tca_act_prio


def fix_msg(msg, kwarg):
    msg['info'] = htons(
        kwarg.get('protocol', protocols.ETH_P_ALL) & 0xFFFF
    ) | ((kwarg.get('prio', 0) << 16) & 0xFFFF0000)


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (
        ('classid', 'TCA_MATCHALL_CLASSID'),
        ('flags', 'TCA_MATCHALL_FLAGS'),
    )

    if kwarg.get('action'):
        ret['attrs'].append(['TCA_MATCHALL_ACT', get_tca_action(kwarg)])

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            ret['attrs'].append([v, r])

    return ret


class options(nla):
    nla_map = (
        ('TCA_MATCHALL_UNSPEC', 'none'),
        ('TCA_MATCHALL_CLASSID', 'be32'),
        ('TCA_MATCHALL_ACT', 'tca_act_prio'),
        ('TCA_MATCHALL_FLAGS', 'be32'),
    )

    tca_act_prio = tca_act_prio
