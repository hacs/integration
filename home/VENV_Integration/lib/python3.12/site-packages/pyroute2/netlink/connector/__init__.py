from pyroute2.netlink import NETLINK_CONNECTOR, nlmsg
from pyroute2.netlink.nlsocket import NetlinkSocket


class cn_msg(nlmsg):
    fields = (
        ('idx', 'I'),
        ('val', 'I'),
        ('seq', 'I'),
        ('ack', 'I'),
        ('len', 'H'),
        ('flags', 'H'),
    )


class ConnectorSocket(NetlinkSocket):
    def __init__(self, fileno=None):
        super().__init__(NETLINK_CONNECTOR)
