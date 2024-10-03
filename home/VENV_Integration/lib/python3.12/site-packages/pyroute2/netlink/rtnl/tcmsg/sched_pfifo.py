from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT

parent = TC_H_ROOT


class options(nla):
    fields = (('limit', 'i'),)


def get_parameters(kwarg):
    return kwarg
