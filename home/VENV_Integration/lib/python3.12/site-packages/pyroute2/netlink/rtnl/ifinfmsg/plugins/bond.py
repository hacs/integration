from pyroute2.netlink import nla


class bond(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_BOND_UNSPEC', 'none'),
        ('IFLA_BOND_MODE', 'uint8'),
        ('IFLA_BOND_ACTIVE_SLAVE', 'uint32'),
        ('IFLA_BOND_MIIMON', 'uint32'),
        ('IFLA_BOND_UPDELAY', 'uint32'),
        ('IFLA_BOND_DOWNDELAY', 'uint32'),
        ('IFLA_BOND_USE_CARRIER', 'uint8'),
        ('IFLA_BOND_ARP_INTERVAL', 'uint32'),
        ('IFLA_BOND_ARP_IP_TARGET', '*ipaddr'),
        ('IFLA_BOND_ARP_VALIDATE', 'uint32'),
        ('IFLA_BOND_ARP_ALL_TARGETS', 'uint32'),
        ('IFLA_BOND_PRIMARY', 'uint32'),
        ('IFLA_BOND_PRIMARY_RESELECT', 'uint8'),
        ('IFLA_BOND_FAIL_OVER_MAC', 'uint8'),
        ('IFLA_BOND_XMIT_HASH_POLICY', 'uint8'),
        ('IFLA_BOND_RESEND_IGMP', 'uint32'),
        ('IFLA_BOND_NUM_PEER_NOTIF', 'uint8'),
        ('IFLA_BOND_ALL_SLAVES_ACTIVE', 'uint8'),
        ('IFLA_BOND_MIN_LINKS', 'uint32'),
        ('IFLA_BOND_LP_INTERVAL', 'uint32'),
        ('IFLA_BOND_PACKETS_PER_SLAVE', 'uint32'),
        ('IFLA_BOND_AD_LACP_RATE', 'uint8'),
        ('IFLA_BOND_AD_SELECT', 'uint8'),
        ('IFLA_BOND_AD_INFO', 'ad_info'),
        ('IFLA_BOND_AD_ACTOR_SYS_PRIO', 'uint16'),
        ('IFLA_BOND_AD_USER_PORT_KEY', 'uint16'),
        ('IFLA_BOND_AD_ACTOR_SYSTEM', 'hex'),
        ('IFLA_BOND_TLB_DYNAMIC_LB', 'uint8'),
    )

    class ad_info(nla):
        nla_map = (
            ('IFLA_BOND_AD_INFO_UNSPEC', 'none'),
            ('IFLA_BOND_AD_INFO_AGGREGATOR', 'uint16'),
            ('IFLA_BOND_AD_INFO_NUM_PORTS', 'uint16'),
            ('IFLA_BOND_AD_INFO_ACTOR_KEY', 'uint16'),
            ('IFLA_BOND_AD_INFO_PARTNER_KEY', 'uint16'),
            ('IFLA_BOND_AD_INFO_PARTNER_MAC', 'l2addr'),
        )
