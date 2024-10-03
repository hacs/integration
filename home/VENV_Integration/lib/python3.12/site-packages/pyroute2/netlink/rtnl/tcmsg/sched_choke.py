'''
choke
+++++

Parameters:

    * `limit` (required) -- int
    * `bandwith` (required) -- str/int
    * `min` -- int
    * `max` -- int
    * `avpkt` -- str/int, packet size
    * `burst` -- int
    * `probability` -- float
    * `ecn` -- bool

Example::

    ip.tc('add', 'choke', interface,
          limit=5500,
          bandwith="10mbit",
          ecn=True)

'''

import logging
import struct

from pyroute2.netlink import nla, nla_string
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import (
    get_rate,
    get_size,
    red_eval_ewma,
    red_eval_idle_damping,
    red_eval_P,
)
from pyroute2.netlink.rtnl.tcmsg.common import stats2 as c_stats2

log = logging.getLogger(__name__)
parent = TC_H_ROOT


def get_parameters(kwarg):
    # The code is ported from iproute2
    avpkt = 1000
    probability = 0.02
    opt = {
        'limit': kwarg['limit'],  # required
        'qth_min': kwarg.get('min', 0),
        'qth_max': kwarg.get('max', 0),
        'Wlog': 0,
        'Plog': 0,
        'Scell_log': 0,
        'flags': 1 if kwarg.get('ecn') else 0,
    }

    rate = get_rate(kwarg['bandwith'])  # required
    burst = kwarg.get('burst', 0)
    avpkt = get_size(kwarg.get('avpkt', 1000))
    probability = kwarg.get('probability', 0.02)

    if not opt['qth_max']:
        opt['qth_max'] = opt['limit'] // 4
    if not opt['qth_min']:
        opt['qth_min'] = opt['qth_max'] // 3
    if not burst:
        burst = (2 * opt['qth_min'] + opt['qth_max']) // 3

    if opt['qth_max'] > opt['limit']:
        raise Exception('max is larger than limit')
    if opt['qth_min'] >= opt['qth_max']:
        raise Exception('min is not smaller than max')

    # Wlog
    opt['Wlog'] = red_eval_ewma(opt['qth_min'] * avpkt, burst, avpkt)
    if opt['Wlog'] < 0:
        raise Exception('failed to calculate EWMA')
    elif opt['Wlog'] > 10:
        log.warning('choke: burst %s seems to be too large' % burst)
    # Plog
    opt['Plog'] = red_eval_P(
        opt['qth_min'] * avpkt, opt['qth_max'] * avpkt, probability
    )
    if opt['Plog'] < 0:
        raise Exception('choke: failed to calculate probability')
    # Scell_log, stab
    opt['Scell_log'], stab = red_eval_idle_damping(opt['Wlog'], avpkt, rate)
    if opt['Scell_log'] < 0:
        raise Exception('choke: failed to calculate idle damping table')

    return {
        'attrs': [
            ['TCA_CHOKE_PARMS', opt],
            ['TCA_CHOKE_STAB', stab],
            ['TCA_CHOKE_MAX_P', int(probability * pow(2, 32))],
        ]
    }


class options(nla):
    nla_map = (
        ('TCA_CHOKE_UNSPEC', 'none'),
        ('TCA_CHOKE_PARMS', 'qopt'),
        ('TCA_CHOKE_STAB', 'stab'),
        ('TCA_CHOKE_MAX_P', 'uint32'),
    )

    class qopt(nla):
        fields = (
            ('limit', 'I'),
            ('qth_min', 'I'),
            ('qth_max', 'I'),
            ('Wlog', 'B'),
            ('Plog', 'B'),
            ('Scell_log', 'B'),
            ('flags', 'B'),
        )

    class stab(nla_string):
        def encode(self):
            self['value'] = struct.pack(
                'B' * 256, *(int(x) for x in self.value)
            )
            nla_string.encode(self)


class stats(nla):
    fields = (
        ('early', 'I'),
        ('pdrop', 'I'),
        ('other', 'I'),
        ('marked', 'I'),
        ('matched', 'I'),
    )


class stats2(c_stats2):
    class stats_app(stats):
        pass
