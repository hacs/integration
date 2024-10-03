from pyroute2.netlink import nla

flags = {'reorder_hdr': 0x1, 'gvrp': 0x2, 'loose_binding': 0x4, 'mvrp': 0x8}


class vlan(nla):
    prefix = 'IFLA_'

    nla_map = (
        ('IFLA_VLAN_UNSPEC', 'none'),
        ('IFLA_VLAN_ID', 'uint16'),
        ('IFLA_VLAN_FLAGS', 'vlan_flags'),
        ('IFLA_VLAN_EGRESS_QOS', 'qos'),
        ('IFLA_VLAN_INGRESS_QOS', 'qos'),
        ('IFLA_VLAN_PROTOCOL', 'be16'),
    )

    class vlan_flags(nla):
        fields = (('flags', 'I'), ('mask', 'I'))

    class qos(nla):
        prefix = 'IFLA_'

        nla_map = (
            ('IFLA_VLAN_QOS_UNSPEC', 'none'),
            ('IFLA_VLAN_QOS_MAPPING', 'qos_mapping'),
        )

        class qos_mapping(nla):
            fields = (('from', 'I'), ('to', 'I'))
