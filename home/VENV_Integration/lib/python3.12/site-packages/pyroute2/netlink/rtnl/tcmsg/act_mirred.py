from pyroute2.netlink import NLA_F_NESTED, nla
from pyroute2.netlink.rtnl.tcmsg.common import tc_actions

"""
Mirred - mirror/redirect action
see tc-mirred(8)

Use like any other action, with the following parameters available:
- direction (mandatory): ingress or egress
- action (mandatory): mirror or redirect
- ifindex (mandatory): destination interface for mirrored or redirected packets
- index: explicit index for this action
"""

# see tc_mirred.h
MIRRED_EACTIONS = {
    ("egress", "redirect"): 1,  # redirect packet to egress
    ("egress", "mirror"): 2,  # mirror packet to egress
    ("ingress", "redirect"): 3,  # redirect packet to ingress
    ("ingress", "mirror"): 4,  # mirror packet to ingress
}


class options(nla):
    nla_flags = NLA_F_NESTED
    nla_map = (
        ('TCA_MIRRED_UNSPEC', 'none'),
        ('TCA_MIRRED_TM', 'none'),
        ('TCA_MIRRED_PARMS', 'tca_mirred_parms'),
    )

    class tca_mirred_parms(nla):
        fields = (
            ('index', 'I'),
            ('capab', 'I'),
            ('action', 'i'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
            ('eaction', 'i'),
            ('ifindex', 'I'),
        )


def get_parameters(kwarg):
    ret = {'attrs': []}
    # direction, action and ifindex are mandatory
    parms = {
        'eaction': MIRRED_EACTIONS[(kwarg['direction'], kwarg['action'])],
        'ifindex': kwarg['ifindex'],
    }

    if 'index' in kwarg:
        parms['index'] = int(kwarg['index'])

    # From m_mirred.c
    if kwarg['action'] == 'redirect':
        parms['action'] = tc_actions['stolen']
    else:  # mirror
        parms['action'] = tc_actions['pipe']

    ret['attrs'].append(['TCA_MIRRED_PARMS', parms])
    return ret
