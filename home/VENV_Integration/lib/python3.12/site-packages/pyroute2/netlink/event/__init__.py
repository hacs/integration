from pyroute2.config import kernel
from pyroute2.netlink.generic import GenericNetlinkSocket


class EventSocket(GenericNetlinkSocket):
    marshal_class = None
    genl_family = None

    def __init__(self, *args, **kwargs):
        GenericNetlinkSocket.__init__(self, *args, **kwargs)
        self.marshal = self.marshal_class()
        if kernel[0] <= 2:
            self.bind(groups=0xFFFFFF)
        else:
            self.bind()
        for group in self.mcast_groups:
            self.add_membership(group)

    def bind(self, groups=0, **kwarg):
        GenericNetlinkSocket.bind(
            self,
            self.genl_family,
            self.marshal_class.msg_map[0],
            groups,
            None,
            **kwarg
        )
