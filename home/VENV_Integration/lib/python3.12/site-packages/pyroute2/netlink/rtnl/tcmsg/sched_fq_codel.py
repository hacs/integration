import logging

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import RTM_DELQDISC, RTM_NEWQDISC, TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import get_time, stats2

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
        'fqc_limit': lambda x: x,
        'fqc_flows': lambda x: x,
        'fqc_quantum': lambda x: x,
        'fqc_ecn': lambda x: x,
        'fqc_target': get_time,
        'fqc_ce_threshold': get_time,
        'fqc_interval': get_time,
    }
    for key in transform:
        if key in kwarg:
            log.warning(
                'fq_codel parameters naming will be changed '
                'in next releases (%s)' % key
            )
            ret['attrs'].append(
                [
                    'TCA_FQ_CODEL_%s' % key[4:].upper(),
                    transform[key](kwarg[key]),
                ]
            )
    return ret


class options(nla):
    nla_map = (
        ('TCA_FQ_CODEL_UNSPEC', 'none'),
        ('TCA_FQ_CODEL_TARGET', 'uint32'),
        ('TCA_FQ_CODEL_LIMIT', 'uint32'),
        ('TCA_FQ_CODEL_INTERVAL', 'uint32'),
        ('TCA_FQ_CODEL_ECN', 'uint32'),
        ('TCA_FQ_CODEL_FLOWS', 'uint32'),
        ('TCA_FQ_CODEL_QUANTUM', 'uint32'),
        ('TCA_FQ_CODEL_CE_THRESHOLD', 'uint32'),
        ('TCA_FQ_CODEL_DROP_BATCH_SIZE', 'uint32'),
        ('TCA_FQ_CODEL_MEMORY_LIMIT', 'uint32'),
    )


class qdisc_stats(nla):
    fields = (
        ('type', 'I'),
        ('maxpacket', 'I'),
        ('drop_overlimit', 'I'),
        ('ecn_mark', 'I'),
        ('new_flow_count', 'I'),
        ('new_flows_len', 'I'),
        ('old_flows_len', 'I'),
        ('ce_mark', 'I'),
        ('memory_usage', 'I'),
        ('drop_overmemory', 'I'),
    )


class class_stats(nla):
    fields = (
        ('type', 'I'),
        ('deficit', 'i'),
        ('ldelay', 'I'),
        ('count', 'I'),
        ('lastcount', 'I'),
        ('dropping', 'I'),
        ('drop_next', 'i'),
    )


class qdisc_stats2(stats2):
    class stats_app(qdisc_stats):
        pass


class class_stats2(stats2):
    class stats_app(class_stats):
        pass


def stats2(msg, *argv, **kwarg):
    if msg['header']['type'] in (RTM_NEWQDISC, RTM_DELQDISC):
        return qdisc_stats2
    else:
        return class_stats2


# To keep the compatibility with TCA_XSTATS
def stats(msg, *argv, **kwarg):
    if msg['header']['type'] in (RTM_NEWQDISC, RTM_DELQDISC):
        return qdisc_stats
    else:
        return class_stats
