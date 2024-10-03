from socket import htons

from pyroute2 import protocols
from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.act_police import (
    get_parameters as ap_parameters,
)
from pyroute2.netlink.rtnl.tcmsg.act_police import nla_plus_police
from pyroute2.netlink.rtnl.tcmsg.common_act import get_tca_action, tca_act_prio


def fix_msg(msg, kwarg):
    msg['info'] = htons(
        kwarg.get('protocol', protocols.ETH_P_ALL) & 0xFFFF
    ) | ((kwarg.get('prio', 0) << 16) & 0xFFFF0000)


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (
        ('classid', 'TCA_FW_CLASSID'),
        # ('police', 'TCA_FW_POLICE'),
        # Handled in ap_parameters
        ('indev', 'TCA_FW_INDEV'),
        ('mask', 'TCA_FW_MASK'),
    )

    if kwarg.get('rate'):
        ret['attrs'].append(['TCA_FW_POLICE', ap_parameters(kwarg)])

    if kwarg.get('action'):
        ret['attrs'].append(['TCA_FW_ACT', get_tca_action(kwarg)])

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            ret['attrs'].append([v, r])

    return ret


class options(nla, nla_plus_police):
    nla_map = (
        ('TCA_FW_UNSPEC', 'none'),
        ('TCA_FW_CLASSID', 'uint32'),
        ('TCA_FW_POLICE', 'police'),  # TODO string?
        ('TCA_FW_INDEV', 'hex'),  # TODO string
        ('TCA_FW_ACT', 'tca_act_prio'),
        ('TCA_FW_MASK', 'uint32'),
    )

    tca_act_prio = tca_act_prio
