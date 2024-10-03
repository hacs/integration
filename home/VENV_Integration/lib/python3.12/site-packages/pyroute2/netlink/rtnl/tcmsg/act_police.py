from pyroute2.netlink.rtnl.tcmsg.common import (
    get_rate_parameters,
    nla_plus_rtab,
)

actions = {
    'unspec': -1,  # TC_POLICE_UNSPEC
    'ok': 0,  # TC_POLICE_OK
    'reclassify': 1,  # TC_POLICE_RECLASSIFY
    'shot': 2,  # TC_POLICE_SHOT
    'drop': 2,  # TC_POLICE_SHOT
    'pipe': 3,
}  # TC_POLICE_PIPE


class options(nla_plus_rtab):
    nla_map = (
        ('TCA_POLICE_UNSPEC', 'none'),
        ('TCA_POLICE_TBF', 'police_tbf'),
        ('TCA_POLICE_RATE', 'rtab'),
        ('TCA_POLICE_PEAKRATE', 'ptab'),
        ('TCA_POLICE_AVRATE', 'uint32'),
        ('TCA_POLICE_RESULT', 'uint32'),
    )

    class police_tbf(nla_plus_rtab.parms):
        fields = (
            ('index', 'I'),
            ('action', 'i'),
            ('limit', 'I'),
            ('burst', 'I'),
            ('mtu', 'I'),
            ('rate_cell_log', 'B'),
            ('rate___reserved', 'B'),
            ('rate_overhead', 'H'),
            ('rate_cell_align', 'h'),
            ('rate_mpu', 'H'),
            ('rate', 'I'),
            ('peak_cell_log', 'B'),
            ('peak___reserved', 'B'),
            ('peak_overhead', 'H'),
            ('peak_cell_align', 'h'),
            ('peak_mpu', 'H'),
            ('peak', 'I'),
            ('refcnt', 'i'),
            ('bindcnt', 'i'),
            ('capab', 'I'),
        )


class nla_plus_police(object):
    class police(options):
        pass


def get_parameters(kwarg):
    # if no limit specified, set it to zero to make
    # the next call happy
    kwarg['limit'] = kwarg.get('limit', 0)
    tbfp = get_rate_parameters(kwarg)
    # create an alias -- while TBF uses 'buffer', rate
    # policy uses 'burst'
    tbfp['burst'] = tbfp['buffer']
    # action resolver
    tbfp['action'] = actions[kwarg.get('action', 'reclassify')]
    return {'attrs': [['TCA_POLICE_TBF', tbfp], ['TCA_POLICE_RATE', True]]}
