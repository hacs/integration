from pyroute2.netlink import nla, nlmsg_atoms


class geneve(nla):
    nla_map = (
        ('IFLA_GENEVE_UNSPEC', 'none'),
        ('IFLA_GENEVE_ID', 'uint32'),
        ('IFLA_GENEVE_REMOTE', 'ip4addr'),
        ('IFLA_GENEVE_TTL', 'uint8'),
        ('IFLA_GENEVE_TOS', 'uint8'),
        ('IFLA_GENEVE_PORT', 'be16'),
        ('IFLA_GENEVE_COLLECT_METADATA', 'flag'),
        ('IFLA_GENEVE_REMOTE6', 'ip6addr'),
        ('IFLA_GENEVE_UDP_CSUM', 'uint8'),
        ('IFLA_GENEVE_UDP_ZERO_CSUM6_TX', 'uint8'),
        ('IFLA_GENEVE_UDP_ZERO_CSUM6_RX', 'uint8'),
        ('IFLA_GENEVE_LABEL', 'be32'),
        ('IFLA_GENEVE_TTL_INHERIT', 'uint8'),
        ('IFLA_GENEVE_DF', 'df'),
    )

    class df(nlmsg_atoms.uint16):
        value_map = {0: 'unset', 1: 'set', 2: 'inherit'}
