from pyroute2.netlink import nlmsg


class p2pmsg(nlmsg):
    '''
    Fake message type to represent peer to peer connections,
    be it GRE or PPP
    '''

    __slots__ = ()
    prefix = 'P2P_'

    fields = (('index', 'I'), ('family', 'I'))

    nla_map = (
        ('P2P_UNSPEC', 'none'),
        ('P2P_LOCAL', 'target'),
        ('P2P_REMOTE', 'target'),
    )
