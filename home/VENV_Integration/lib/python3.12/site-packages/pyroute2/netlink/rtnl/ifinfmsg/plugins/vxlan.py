from pyroute2.netlink import nla


class vxlan(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_VXLAN_UNSPEC', 'none'),
        ('IFLA_VXLAN_ID', 'uint32'),
        ('IFLA_VXLAN_GROUP', 'ip4addr'),
        ('IFLA_VXLAN_LINK', 'uint32'),
        ('IFLA_VXLAN_LOCAL', 'ip4addr'),
        ('IFLA_VXLAN_TTL', 'uint8'),
        ('IFLA_VXLAN_TOS', 'uint8'),
        ('IFLA_VXLAN_LEARNING', 'uint8'),
        ('IFLA_VXLAN_AGEING', 'uint32'),
        ('IFLA_VXLAN_LIMIT', 'uint32'),
        ('IFLA_VXLAN_PORT_RANGE', 'port_range'),
        ('IFLA_VXLAN_PROXY', 'uint8'),
        ('IFLA_VXLAN_RSC', 'uint8'),
        ('IFLA_VXLAN_L2MISS', 'uint8'),
        ('IFLA_VXLAN_L3MISS', 'uint8'),
        ('IFLA_VXLAN_PORT', 'be16'),
        ('IFLA_VXLAN_GROUP6', 'ip6addr'),
        ('IFLA_VXLAN_LOCAL6', 'ip6addr'),
        ('IFLA_VXLAN_UDP_CSUM', 'uint8'),
        ('IFLA_VXLAN_UDP_ZERO_CSUM6_TX', 'uint8'),
        ('IFLA_VXLAN_UDP_ZERO_CSUM6_RX', 'uint8'),
        ('IFLA_VXLAN_REMCSUM_TX', 'uint8'),
        ('IFLA_VXLAN_REMCSUM_RX', 'uint8'),
        ('IFLA_VXLAN_GBP', 'flag'),
        ('IFLA_VXLAN_REMCSUM_NOPARTIAL', 'flag'),
        ('IFLA_VXLAN_COLLECT_METADATA', 'uint8'),
        ('IFLA_VXLAN_LABEL', 'uint32'),
        ('IFLA_VXLAN_GPE', 'flag'),
        ('IFLA_VXLAN_TTL_INHERIT', 'flag'),
        ('IFLA_VXLAN_DF', 'uint8'),
    )

    class port_range(nla):
        fields = (('low', '>H'), ('high', '>H'))
