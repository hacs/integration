from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_INGRESS

parent = TC_H_INGRESS


def fix_msg(msg, kwarg):
    msg['handle'] = 0xFFFF0000


class options(nla):
    fields = (('value', 'I'),)
