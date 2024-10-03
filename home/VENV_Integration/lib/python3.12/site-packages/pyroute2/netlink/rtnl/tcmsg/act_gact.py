from pyroute2.netlink import NLA_F_NESTED, nla
from pyroute2.netlink.rtnl.tcmsg.common import tc_actions


class options(nla):
    nla_flags = NLA_F_NESTED
    nla_map = (
        ('TCA_GACT_UNSPEC', 'none'),
        ('TCA_GACT_TM', 'none'),
        ('TCA_GACT_PARMS', 'tca_gact_parms'),
        ('TCA_GACT_PROB', 'none'),
    )

    class tca_gact_parms(nla):
        fields = (
            ('index', 'I'),
            ('capab', 'I'),
            ('action', 'i'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
        )


def get_parameters(kwarg):
    ret = {'attrs': []}
    a = tc_actions[kwarg.get('action', 'drop')]
    ret['attrs'].append(['TCA_GACT_PARMS', {'action': a}])
    return ret
