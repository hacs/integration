from pyroute2.netlink import nla


class ipvlan(nla):
    prefix = 'IFLA_'
    nla_map = (('IFLA_IPVLAN_UNSPEC', 'none'), ('IFLA_IPVLAN_MODE', 'uint16'))

    modes = {
        0: 'IPVLAN_MODE_L2',
        1: 'IPVLAN_MODE_L3',
        'IPVLAN_MODE_L2': 0,
        'IPVLAN_MODE_L3': 1,
    }
