from pyroute2.netlink import NETLINK_ROUTE, rtnl
from pyroute2.netlink.nlsocket import NetlinkSocket
from pyroute2.netlink.rtnl.marshal import MarshalRtnl


class RawIPRSocketBase(object):
    def __init__(self, fileno=None):
        super(RawIPRSocketBase, self).__init__(NETLINK_ROUTE, fileno=fileno)
        self.marshal = MarshalRtnl()

    def bind(self, groups=rtnl.RTMGRP_DEFAULTS, **kwarg):
        super(RawIPRSocketBase, self).bind(groups, **kwarg)


class RawIPRSocket(RawIPRSocketBase, NetlinkSocket):
    pass
