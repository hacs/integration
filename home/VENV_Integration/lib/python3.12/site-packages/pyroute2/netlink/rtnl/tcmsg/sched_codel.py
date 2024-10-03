import logging

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import get_time
from pyroute2.netlink.rtnl.tcmsg.common import stats2 as c_stats2

log = logging.getLogger(__name__)
parent = TC_H_ROOT


def get_parameters(kwarg):
    #
    # ACHTUNG: experimental code
    #
    # Parameters naming scheme WILL be changed in next releases
    #
    ret = {'attrs': []}
    transform = {
        'cdl_limit': lambda x: x,
        'cdl_ecn': lambda x: x,
        'cdl_target': get_time,
        'cdl_ce_threshold': get_time,
        'cdl_interval': get_time,
    }
    for key in transform:
        if key in kwarg:
            log.warning(
                'codel parameters naming will be changed '
                'in next releases (%s)' % key
            )
            ret['attrs'].append(
                ['TCA_CODEL_%s' % key[4:].upper(), transform[key](kwarg[key])]
            )
    return ret


class options(nla):
    nla_map = (
        ('TCA_CODEL_UNSPEC', 'none'),
        ('TCA_CODEL_TARGET', 'uint32'),
        ('TCA_CODEL_LIMIT', 'uint32'),
        ('TCA_CODEL_INTERVAL', 'uint32'),
        ('TCA_CODEL_ECN', 'uint32'),
        ('TCA_CODEL_CE_THRESHOLD', 'uint32'),
    )


class stats(nla):
    fields = (
        ('maxpacket', 'I'),
        ('count', 'I'),
        ('lastcount', 'I'),
        ('ldelay', 'I'),
        ('drop_next', 'I'),
        ('drop_overlimit', 'I'),
        ('ecn_mark', 'I'),
        ('dropping', 'I'),
        ('ce_mark', 'I'),
    )


class stats2(c_stats2):
    class stats_app(stats):
        pass
