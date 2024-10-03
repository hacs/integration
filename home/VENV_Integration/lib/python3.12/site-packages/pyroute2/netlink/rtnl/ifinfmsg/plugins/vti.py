from pyroute2.netlink import nla


class vti(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_VTI_UNSPEC', 'none'),
        ('IFLA_VTI_LINK', 'uint32'),
        ('IFLA_VTI_IKEY', 'be32'),
        ('IFLA_VTI_OKEY', 'be32'),
        ('IFLA_VTI_LOCAL', 'ip4addr'),
        ('IFLA_VTI_REMOTE', 'ip4addr'),
    )
