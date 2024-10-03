from pyroute2.netlink import nla
from pyroute2.netlink.rtnl.tcmsg.common import tc_actions


class options(nla):
    nla_map = (
        ('TCA_ACT_BPF_UNSPEC', 'none'),
        ('TCA_ACT_BPF_TM,', 'none'),
        ('TCA_ACT_BPF_PARMS', 'tca_act_bpf_parms'),
        ('TCA_ACT_BPF_OPS_LEN', 'uint16'),
        ('TCA_ACT_BPF_OPS', 'hex'),
        ('TCA_ACT_BPF_FD', 'uint32'),
        ('TCA_ACT_BPF_NAME', 'asciiz'),
    )

    class tca_act_bpf_parms(nla):
        fields = (
            ('index', 'I'),
            ('capab', 'I'),
            ('action', 'i'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
        )


def get_parameters(kwarg):
    ret = {'attrs': []}
    if 'fd' in kwarg:
        ret['attrs'].append(['TCA_ACT_BPF_FD', kwarg['fd']])
    if 'name' in kwarg:
        ret['attrs'].append(['TCA_ACT_BPF_NAME', kwarg['name']])
    a = tc_actions[kwarg.get('action', 'drop')]
    ret['attrs'].append(['TCA_ACT_BPF_PARMS', {'action': a}])
    return ret
