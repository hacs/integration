from pyroute2.netlink import nla, nlmsg
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg


class ifstatsmsg(nlmsg):
    fields = (
        ('family', 'B'),
        ('pad1', 'B'),
        ('pad2', 'H'),
        ('ifindex', 'I'),
        ('filter_mask', 'I'),
    )

    nla_map = (
        ('IFLA_STATS_UNSPEC', 'none'),
        ('IFLA_STATS_LINK_64', 'ifstats64'),
        ('IFLA_STATS_LINK_XSTATS', 'ifxstats'),
        ('IFLA_STATS_LINK_XSTATS_SLAVE', 'ifxstats'),
        ('IFLA_STATS_LINK_OFFLOAD_XSTATS', 'hex'),
        ('IFLA_STATS_AF_SPEC', 'hex'),
    )

    class ifstats64(ifinfmsg.ifstats64):
        pass

    class ifxstats(nla):
        nla_map = (
            ('LINK_XSTATS_TYPE_UNSPEC', 'none'),
            ('LINK_XSTATS_TYPE_BRIDGE', 'bridge'),
            ('LINK_XSTATS_TYPE_BOND', 'hex'),
        )

        class bridge(nla):
            nla_map = (
                ('BRIDGE_XSTATS_UNSPEC', 'none'),
                ('BRIDGE_XSTATS_VLAN', 'vlan'),
                ('BRIDGE_XSTATS_MCAST', 'mcast'),
                ('BRIDGE_XSTATS_PAD', 'hex'),
                ('BRIDGE_XSTATS_STP', 'stp'),
            )

            class vlan(nla):
                fields = (
                    ('rx_bytes', 'Q'),
                    ('rx_packets', 'Q'),
                    ('tx_bytes', 'Q'),
                    ('tx_packets', 'Q'),
                    ('vid', 'H'),
                    ('flags', 'H'),
                    ('pad2', 'I'),
                )

            class mcast(nla):
                fields = (
                    ('igmp_v1queries', 'QQ'),
                    ('igmp_v2queries', 'QQ'),
                    ('igmp_v3queries', 'QQ'),
                    ('igmp_leaves', 'QQ'),
                    ('igmp_v1reports', 'QQ'),
                    ('igmp_v2reports', 'QQ'),
                    ('igmp_v3reports', 'QQ'),
                    ('igmp_parse_errors', 'Q'),
                    ('mld_v1queries', 'QQ'),
                    ('mld_v2queries', 'QQ'),
                    ('mld_leaves', 'QQ'),
                    ('mld_v1reports', 'QQ'),
                    ('mld_v2reports', 'QQ'),
                    ('mld_parse_errors', 'Q'),
                    ('mcast_bytes', 'QQ'),
                    ('mcast_packets', 'QQ'),
                )

            class stp(nla):
                fields = (
                    ('transition_blk', 'Q'),
                    ('transition_fwd', 'Q'),
                    ('rx_bpdu', 'Q'),
                    ('tx_bpdu', 'Q'),
                    ('rx_tcn', 'Q'),
                    ('tx_tcn', 'Q'),
                )
