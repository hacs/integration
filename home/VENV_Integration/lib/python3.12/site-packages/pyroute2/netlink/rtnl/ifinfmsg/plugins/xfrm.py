from pyroute2.netlink import nla


class xfrm(nla):
    nla_map = (
        ('IFLA_XFRM_UNSPEC', 'none'),
        ('IFLA_XFRM_LINK', 'uint32'),
        ('IFLA_XFRM_IF_ID', 'uint32'),
    )
