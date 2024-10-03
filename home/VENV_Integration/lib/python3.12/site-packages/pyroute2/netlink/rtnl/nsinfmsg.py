from pyroute2.netlink import nlmsg, nlmsg_atoms


class nsinfmsg(nlmsg):
    '''
    Fake message type to represent network namespace information.

    This is a prototype, the NLA layout is subject to change without
    notification.
    '''

    __slots__ = ()
    prefix = 'NSINFO_'

    fields = (('inode', 'I'), ('netnsid', 'I'))

    nla_map = (
        ('NSINFO_UNSPEC', 'none'),
        ('NSINFO_PATH', 'string'),
        ('NSINFO_PEER', 'peer'),
    )

    class peer(nlmsg_atoms.string):
        sql_type = None
