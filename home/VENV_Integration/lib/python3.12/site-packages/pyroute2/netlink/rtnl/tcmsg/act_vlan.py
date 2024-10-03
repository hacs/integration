from socket import htons

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.common import tc_actions

v_actions = {'pop': 1, 'push': 2, 'modify': 3}


class options(nla):
    nla_map = (
        ('TCA_VLAN_UNSPEC', 'none'),
        ('TCA_VLAN_TM', 'none'),
        ('TCA_VLAN_PARMS', 'tca_vlan_parms'),
        ('TCA_VLAN_PUSH_VLAN_ID', 'uint16'),
        ('TCA_VLAN_PUSH_VLAN_PROTOCOL', 'uint16'),
        ('TCA_VLAN_PAD', 'none'),
        ('TCA_VLAN_PUSH_VLAN_PRIORITY', 'uint8'),
    )

    class tca_vlan_parms(nla):
        fields = (
            ('index', 'I'),
            ('capab', 'I'),
            ('action', 'i'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
            ('v_action', 'i'),
        )


def get_parameters(kwarg):
    ret = {'attrs': []}
    parms = {'v_action': v_actions[kwarg['v_action']]}
    parms['action'] = tc_actions[kwarg.get('action', 'pipe')]
    ret['attrs'].append(['TCA_VLAN_PARMS', parms])
    # Vlan id compulsory for "push" and "modify"
    if kwarg['v_action'] in ['push', 'modify']:
        ret['attrs'].append(['TCA_VLAN_PUSH_VLAN_ID', kwarg['id']])
    if 'priority' in kwarg:
        ret['attrs'].append(['TCA_VLAN_PUSH_VLAN_PRIORITY', kwarg['priority']])
    if kwarg.get('protocol', '802.1Q') == '802.1ad':
        ret['attrs'].append(['TCA_VLAN_PUSH_VLAN_PROTOCOL', htons(0x88A8)])
    else:
        ret['attrs'].append(['TCA_VLAN_PUSH_VLAN_PROTOCOL', htons(0x8100)])
    return ret
