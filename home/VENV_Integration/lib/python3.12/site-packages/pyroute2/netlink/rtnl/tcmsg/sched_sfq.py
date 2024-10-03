from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import (
    get_size,
    red_eval_ewma,
    red_eval_P,
)

parent = TC_H_ROOT

TC_RED_ECN = 1
TC_RED_HARDDROP = 2
TC_RED_ADAPTATIVE = 4


def get_parameters(kwarg):
    kwarg['quantum'] = get_size(kwarg.get('quantum', 0))
    kwarg['perturb_period'] = kwarg.get('perturb', 0) or kwarg.get(
        'perturb_period', 0
    )
    limit = kwarg['limit'] = kwarg.get('limit', 0) or kwarg.get(
        'redflowlimit', 0
    )
    qth_min = kwarg.get('min', 0)
    qth_max = kwarg.get('max', 0)
    avpkt = kwarg.get('avpkt', 1000)
    probability = kwarg.get('probability', 0.02)
    ecn = kwarg.get('ecn', False)
    harddrop = kwarg.get('harddrop', False)
    kwarg['flags'] = kwarg.get('flags', 0)
    if ecn:
        kwarg['flags'] |= TC_RED_ECN
    if harddrop:
        kwarg['flags'] |= TC_RED_HARDDROP
    if kwarg.get('redflowlimit'):
        qth_max = qth_max or limit / 4
        qth_min = qth_min or qth_max / 3
        kwarg['burst'] = kwarg['burst'] or (2 * qth_min + qth_max) / (
            3 * avpkt
        )
        if limit <= qth_max:
            raise ValueError('limit must be > qth_max')
        if qth_max <= qth_min:
            raise ValueError('qth_max must be > qth_min')
        kwarg['qth_min'] = qth_min
        kwarg['qth_max'] = qth_max
        kwarg['Wlog'] = red_eval_ewma(qth_min, kwarg['burst'], avpkt)
        kwarg['Plog'] = red_eval_P(qth_min, qth_max, probability)
        if kwarg['Wlog'] < 0:
            raise ValueError('Wlog must be > 0')
        if kwarg['Plog'] < 0:
            raise ValueError('Plog must be > 0')
        kwarg['max_P'] = int(probability * pow(2, 23))

    return kwarg


class options_sfq_v0(nla):
    fields = (
        ('quantum', 'I'),
        ('perturb_period', 'i'),
        ('limit', 'I'),
        ('divisor', 'I'),
        ('flows', 'I'),
    )


class options_sfq_v1(nla):
    fields = (
        ('quantum', 'I'),
        ('perturb_period', 'i'),
        ('limit_v0', 'I'),
        ('divisor', 'I'),
        ('flows', 'I'),
        ('depth', 'I'),
        ('headdrop', 'I'),
        ('limit_v1', 'I'),
        ('qth_min', 'I'),
        ('qth_max', 'I'),
        ('Wlog', 'B'),
        ('Plog', 'B'),
        ('Scell_log', 'B'),
        ('flags', 'B'),
        ('max_P', 'I'),
        ('prob_drop', 'I'),
        ('forced_drop', 'I'),
        ('prob_mark', 'I'),
        ('forced_mark', 'I'),
        ('prob_mark_head', 'I'),
        ('forced_mark_head', 'I'),
    )


def options(*argv, **kwarg):
    if kwarg.get('length', 0) >= options_sfq_v1.get_size():
        return options_sfq_v1
    else:
        return options_sfq_v0
