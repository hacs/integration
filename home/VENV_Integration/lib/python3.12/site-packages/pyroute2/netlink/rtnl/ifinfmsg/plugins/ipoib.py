from pyroute2.netlink import nla, nlmsg_atoms


class ipoib(nla):
    prefix = 'IFLA_IPOIB_'

    nla_map = (
        ('IFLA_IPOIB_UNSPEC', 'none'),
        ('IFLA_IPOIB_PKEY', 'uint16'),
        ('IFLA_IPOIB_MODE', 'mode'),
        ('IFLA_IPOIB_UMCAST', 'uint16'),
    )

    class mode(nlmsg_atoms.uint16):
        value_map = {0: 'datagram', 1: 'connected'}
