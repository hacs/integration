from pyroute2.netlink import NLA_F_NESTED, NLA_F_NET_BYTEORDER, nla
from pyroute2.netlink.nfnetlink import NFNL_SUBSYS_IPSET, nfgen_msg

IPSET_MAXNAMELEN = 32
IPSET_DEFAULT_MAXELEM = 65536

IPSET_CMD_NONE = 0
IPSET_CMD_PROTOCOL = 1  # Return protocol version
IPSET_CMD_CREATE = 2  # Create a new (empty) set
IPSET_CMD_DESTROY = 3  # Destroy a (empty) set
IPSET_CMD_FLUSH = 4  # Remove all elements from a set
IPSET_CMD_RENAME = 5  # Rename a set
IPSET_CMD_SWAP = 6  # Swap two sets
IPSET_CMD_LIST = 7  # List sets
IPSET_CMD_SAVE = 8  # Save sets
IPSET_CMD_ADD = 9  # Add an element to a set
IPSET_CMD_DEL = 10  # Delete an element from a set
IPSET_CMD_TEST = 11  # Test an element in a set
IPSET_CMD_HEADER = 12  # Get set header data only
IPSET_CMD_TYPE = 13  # 13: Get set type
IPSET_CMD_GET_BYNAME = 14  # 14: Get set index by name
IPSET_CMD_GET_BYINDEX = 15  # 15: Get set index by index

# flags at command level (IPSET_ATTR_FLAGS)
IPSET_FLAG_LIST_SETNAME = 1 << 1
IPSET_FLAG_LIST_HEADER = 1 << 2
IPSET_FLAG_SKIP_COUNTER_UPDATE = 1 << 3
IPSET_FLAG_SKIP_SUBCOUNTER_UPDATE = 1 << 4
IPSET_FLAG_MATCH_COUNTERS = 1 << 5
IPSET_FLAG_RETURN_NOMATCH = 1 << 7

# flags at cadt attribute (IPSET_ATTR_CADT_FLAGS)
IPSET_FLAG_PHYSDEV = 1 << 1
IPSET_FLAG_NOMATCH = 1 << 2
IPSET_FLAG_WITH_COUNTERS = 1 << 3
IPSET_FLAG_WITH_COMMENT = 1 << 4
IPSET_FLAG_WITH_FORCEADD = 1 << 5
IPSET_FLAG_WITH_SKBINFO = 1 << 6
IPSET_FLAG_IFACE_WILDCARD = 1 << 7

IPSET_ERR_PROTOCOL = 4097
IPSET_ERR_FIND_TYPE = 4098
IPSET_ERR_MAX_SETS = 4099
IPSET_ERR_BUSY = 4100
IPSET_ERR_EXIST_SETNAME2 = 4101
IPSET_ERR_TYPE_MISMATCH = 4102
IPSET_ERR_EXIST = 4103
IPSET_ERR_INVALID_CIDR = 4104
IPSET_ERR_INVALID_NETMASK = 4105
IPSET_ERR_INVALID_FAMILY = 4106
IPSET_ERR_TIMEOUT = 4107
IPSET_ERR_REFERENCED = 4108
IPSET_ERR_IPADDR_IPV4 = 4109
IPSET_ERR_IPADDR_IPV6 = 4110
IPSET_ERR_COUNTER = 4111
IPSET_ERR_COMMENT = 4112
IPSET_ERR_INVALID_MARKMASK = 4113
IPSET_ERR_SKBINFO = 4114
IPSET_ERR_TYPE_SPECIFIC = 4352


class ipset_base(nla):
    class ipset_ip(nla):
        nla_flags = NLA_F_NESTED
        nla_map = (
            ('IPSET_ATTR_UNSPEC', 'none'),
            ('IPSET_ATTR_IPADDR_IPV4', 'ip4addr', NLA_F_NET_BYTEORDER),
            ('IPSET_ATTR_IPADDR_IPV6', 'ip6addr', NLA_F_NET_BYTEORDER),
        )


class ipset_msg(nfgen_msg):
    '''
    Since the support just begins to be developed,
    many attrs are still in `hex` format -- just to
    dump the content.
    '''

    nla_map = (
        ('IPSET_ATTR_UNSPEC', 'none'),
        ('IPSET_ATTR_PROTOCOL', 'uint8'),
        ('IPSET_ATTR_SETNAME', 'asciiz'),
        ('IPSET_ATTR_TYPENAME', 'asciiz'),
        ('IPSET_ATTR_REVISION', 'uint8'),
        ('IPSET_ATTR_FAMILY', 'uint8'),
        ('IPSET_ATTR_FLAGS', 'be32'),
        ('IPSET_ATTR_DATA', 'get_data_type'),
        ('IPSET_ATTR_ADT', 'attr_adt'),
        ('IPSET_ATTR_LINENO', 'hex'),
        ('IPSET_ATTR_PROTOCOL_MIN', 'uint8'),
        ('IPSET_ATTR_INDEX', 'be16'),
    )

    @staticmethod
    def get_data_type(self, *args, **kwargs):
        # create and list commands have specific attributes. See linux_ip_set.h
        # for more information (and/or lib/PROTOCOL of ipset sources)
        cmd = self['header']['type'] & ~(NFNL_SUBSYS_IPSET << 8)
        if cmd == IPSET_CMD_CREATE or cmd == IPSET_CMD_LIST:
            return self.cadt_data

        return self.ipset_generic.adt_data

    class ipset_generic(ipset_base):
        class adt_data(ipset_base):
            nla_flags = NLA_F_NESTED
            nla_map = (
                (0, 'IPSET_ATTR_UNSPEC', 'none'),
                (1, 'IPSET_ATTR_IP', 'ipset_ip'),
                (1, 'IPSET_ATTR_IP_FROM', 'ipset_ip'),
                (2, 'IPSET_ATTR_IP_TO', 'ipset_ip'),
                (3, 'IPSET_ATTR_CIDR', 'be8', NLA_F_NET_BYTEORDER),
                (4, 'IPSET_ATTR_PORT', 'be16', NLA_F_NET_BYTEORDER),
                (4, 'IPSET_ATTR_PORT_FROM', 'be16', NLA_F_NET_BYTEORDER),
                (5, 'IPSET_ATTR_PORT_TO', 'be16', NLA_F_NET_BYTEORDER),
                (6, 'IPSET_ATTR_TIMEOUT', 'be32', NLA_F_NET_BYTEORDER),
                (7, 'IPSET_ATTR_PROTO', 'be8', NLA_F_NET_BYTEORDER),
                (8, 'IPSET_ATTR_CADT_FLAGS', 'be32', NLA_F_NET_BYTEORDER),
                (9, 'IPSET_ATTR_CADT_LINENO', 'be32'),
                (10, 'IPSET_ATTR_MARK', 'be32', NLA_F_NET_BYTEORDER),
                (11, 'IPSET_ATTR_MARKMASK', 'be32', NLA_F_NET_BYTEORDER),
                (17, 'IPSET_ATTR_ETHER', 'l2addr'),
                (18, 'IPSET_ATTR_NAME', 'asciiz'),
                (19, 'IPSET_ATTR_NAMEREF', 'be32'),
                (20, 'IPSET_ATTR_IP2', 'ipset_ip'),
                (21, 'IPSET_ATTR_CIDR2', 'be8', NLA_F_NET_BYTEORDER),
                (22, 'IPSET_ATTR_IP2_TO', 'ipset_ip'),
                (23, 'IPSET_ATTR_IFACE', 'asciiz'),
                (24, 'IPSET_ATTR_BYTES', 'be64', NLA_F_NET_BYTEORDER),
                (25, 'IPSET_ATTR_PACKETS', 'be64', NLA_F_NET_BYTEORDER),
                (26, 'IPSET_ATTR_COMMENT', 'asciiz'),
                (27, 'IPSET_ATTR_SKBMARK', 'skbmark'),
                (28, 'IPSET_ATTR_SKBPRIO', 'skbprio'),
                (29, 'IPSET_ATTR_SKBQUEUE', 'be16', NLA_F_NET_BYTEORDER),
            )

            class skbmark(nla):
                nla_flags = NLA_F_NET_BYTEORDER
                fields = [('value', '>II')]

            class skbprio(nla):
                nla_flags = NLA_F_NET_BYTEORDER
                fields = [('value', '>HH')]

    class cadt_data(ipset_base):
        nla_flags = NLA_F_NESTED
        nla_map = (
            (0, 'IPSET_ATTR_UNSPEC', 'none'),
            (1, 'IPSET_ATTR_IP', 'ipset_ip'),
            (1, 'IPSET_ATTR_IP_FROM', 'ipset_ip'),
            (2, 'IPSET_ATTR_IP_TO', 'ipset_ip'),
            (3, 'IPSET_ATTR_CIDR', 'be8', NLA_F_NET_BYTEORDER),
            (4, 'IPSET_ATTR_PORT', 'be16', NLA_F_NET_BYTEORDER),
            (4, 'IPSET_ATTR_PORT_FROM', 'be16', NLA_F_NET_BYTEORDER),
            (5, 'IPSET_ATTR_PORT_TO', 'be16', NLA_F_NET_BYTEORDER),
            (6, 'IPSET_ATTR_TIMEOUT', 'be32', NLA_F_NET_BYTEORDER),
            (7, 'IPSET_ATTR_PROTO', 'be8', NLA_F_NET_BYTEORDER),
            (8, 'IPSET_ATTR_CADT_FLAGS', 'be32', NLA_F_NET_BYTEORDER),
            (9, 'IPSET_ATTR_CADT_LINENO', 'be32'),
            (10, 'IPSET_ATTR_MARK', 'be32', NLA_F_NET_BYTEORDER),
            (11, 'IPSET_ATTR_MARKMASK', 'be32', NLA_F_NET_BYTEORDER),
            (17, 'IPSET_ATTR_INITVAL', 'be32', NLA_F_NET_BYTEORDER),
            (18, 'IPSET_ATTR_HASHSIZE', 'be32', NLA_F_NET_BYTEORDER),
            (19, 'IPSET_ATTR_MAXELEM', 'be32', NLA_F_NET_BYTEORDER),
            (20, 'IPSET_ATTR_NETMASK', 'hex'),
            (21, 'IPSET_ATTR_BUCKETSIZE', 'uint8'),
            (22, 'IPSET_ATTR_RESIZE', 'hex'),
            (23, 'IPSET_ATTR_SIZE', 'be32', NLA_F_NET_BYTEORDER),
            (24, 'IPSET_ATTR_ELEMENTS', 'be32', NLA_F_NET_BYTEORDER),
            (25, 'IPSET_ATTR_REFERENCES', 'be32', NLA_F_NET_BYTEORDER),
            (26, 'IPSET_ATTR_MEMSIZE', 'be32', NLA_F_NET_BYTEORDER),
        )

    class attr_adt(ipset_generic):
        nla_flags = NLA_F_NESTED
        nla_map = ((7, 'IPSET_ATTR_DATA', 'adt_data'),)
