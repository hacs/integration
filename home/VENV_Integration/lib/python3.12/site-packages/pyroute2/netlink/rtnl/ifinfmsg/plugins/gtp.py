from pyroute2.netlink import nla


class gtp(nla):
    nla_map = (
        ('IFLA_GTP_UNSPEC', 'none'),
        ('IFLA_GTP_FD0', 'uint32'),
        ('IFLA_GTP_FD1', 'uint32'),
        ('IFLA_GTP_PDP_HASHSIZE', 'uint32'),
    )
