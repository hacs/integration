from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT

parent = TC_H_ROOT


class options(nla):
    fields = (('bands', 'i'), ('priomap', '16B'))


def get_parameters(kwarg):
    return kwarg
