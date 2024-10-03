from pyroute2.netlink.rtnl.rtgenmsg import rtgenmsg


class nsidmsg(rtgenmsg):
    nla_map = (
        ('NETNSA_NONE', 'none'),
        ('NETNSA_NSID', 'uint32'),
        ('NETNSA_PID', 'uint32'),
        ('NETNSA_FD', 'uint32'),
        ('NETNSA_TARGET_NSID', 'uint32'),
        ('NETNSA_CURRENT_NSID', 'uint32'),
    )
