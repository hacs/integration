'''
drr
+++

The qdisc doesn't accept any parameters, but the class
accepts `quantum` parameter::

    ip.tc('add', 'drr', interface, '1:')
    ip.tc('add-class', 'drr', interface, '1:10', quantum=1600)
    ip.tc('add-class', 'drr', interface, '1:20', quantum=1600)

'''

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import stats2 as c_stats2

parent = TC_H_ROOT


def get_class_parameters(kwarg):
    return {'attrs': [['TCA_DRR_QUANTUM', kwarg.get('quantum', 0)]]}


class options(nla):
    nla_map = (('TCA_DRR_UNSPEC', 'none'), ('TCA_DRR_QUANTUM', 'uint32'))


class stats(nla):
    fields = (('deficit', 'I'),)


class stats2(c_stats2):
    class stats_app(stats):
        pass
