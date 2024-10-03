from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import (
    get_rate_parameters,
    nla_plus_rtab,
)

parent = TC_H_ROOT


def get_parameters(kwarg):
    parms = get_rate_parameters(kwarg)
    # fill parameters
    return {'attrs': [['TCA_TBF_PARMS', parms], ['TCA_TBF_RTAB', True]]}


class options(nla_plus_rtab):
    nla_map = (
        ('TCA_TBF_UNSPEC', 'none'),
        ('TCA_TBF_PARMS', 'tbf_parms'),
        ('TCA_TBF_RTAB', 'rtab'),
        ('TCA_TBF_PTAB', 'ptab'),
    )

    class tbf_parms(nla_plus_rtab.parms):
        fields = (
            ('rate_cell_log', 'B'),
            ('rate___reserved', 'B'),
            ('rate_overhead', 'H'),
            ('rate_cell_align', 'h'),
            ('rate_mpu', 'H'),
            ('rate', 'I'),
            ('peak_cell_log', 'B'),
            ('peak___reserved', 'B'),
            ('peak_overhead', 'H'),
            ('peak_cell_align', 'h'),
            ('peak_mpu', 'H'),
            ('peak', 'I'),
            ('limit', 'I'),
            ('buffer', 'I'),
            ('mtu', 'I'),
        )
