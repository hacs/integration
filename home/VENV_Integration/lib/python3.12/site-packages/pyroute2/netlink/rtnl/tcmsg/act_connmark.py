from pyroute2.netlink import NLA_F_NESTED, nla
from pyroute2.netlink.rtnl.tcmsg.common import tc_actions

"""
connmark - netfilter connmark retriever action
see tc-connmark(8)

This filter restores the connection mark into the packet mark.
Connection marks are typically handled by the CONNMARK iptables module.
See iptables-extensions(8).

There is no mandatory parameter, but you can specify the action, which defaults
to 'pipe', and the conntrack zone (see the manual).
"""


class options(nla):
    nla_flags = NLA_F_NESTED
    nla_map = (
        ('TCA_CONNMARK_UNSPEC', 'none'),
        ('TCA_CONNMARK_PARMS', 'tca_connmark_parms'),
        ('TCA_CONNMARK_TM', 'none'),
    )

    class tca_connmark_parms(nla):
        fields = (
            ('index', 'I'),
            ('capab', 'I'),
            ('action', 'i'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
            ('zone', 'H'),
            ('__padding', 'H'),  # XXX is there a better way to do this ?
        )


def get_parameters(kwarg):
    ret = {'attrs': []}

    parms = {
        'action': tc_actions[kwarg.get('action', 'pipe')],
        'zone': kwarg.get('zone', 0),
    }

    ret['attrs'].append(['TCA_CONNMARK_PARMS', parms])
    return ret
