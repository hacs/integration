from pyroute2.netlink import nla


class tun(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_TUN_UNSPEC', 'none'),
        ('IFLA_TUN_OWNER', 'uint32'),
        ('IFLA_TUN_GROUP', 'uint32'),
        ('IFLA_TUN_TYPE', 'uint8'),
        ('IFLA_TUN_PI', 'uint8'),
        ('IFLA_TUN_VNET_HDR', 'uint8'),
        ('IFLA_TUN_PERSIST', 'uint8'),
        ('IFLA_TUN_MULTI_QUEUE', 'uint8'),
        ('IFLA_TUN_NUM_QUEUES', 'uint32'),
        ('IFLA_TUN_NUM_DISABLED_QUEUES', 'uint32'),
    )
