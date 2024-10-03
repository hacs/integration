'''
cake
++++

Usage:

    # Imports
    from pyroute2 import IPRoute


    # Add cake with 2048kbit of bandwidth capacity
    with IPRoute() as ipr:
        # Get interface index
        index = ipr.link_lookup(ifname='lo')
        ipr.tc('add', kind='cake', index=index, bandwidth='2048kbit')

    # Same with 15mbit of bandwidth capacity
    with IPRoute() as ipr:
        # Get interface index
        index = ipr.link_lookup(ifname='lo')
        ipr.tc('add', kind='cake', index=index, bandwidth='15mbit')

    # If you don't know the bandwidth capacity, use autorate
    with IPRoute() as ipr:
        # Get interface index
        index = ipr.link_lookup(ifname='lo')
        ipr.tc('add', kind='cake', index=index, bandwidth='unlimited',
               autorate=True)

    # If you want to tune ATM properties use:
    # atm_mode=False # For no ATM tuning
    # atm_mode=True # For ADSL tuning
    # atm_mode='ptm' # For VDSL2 tuning
    with IPRoute() as ipr:
        # Get interface index
        index = ipr.link_lookup(ifname='lo')
        ipr.tc('add', kind='cake', index=index, bandwidth='unlimited',
               autorate=True, atm_mode=True)

    # Complex example which has no-sense
    with IPRoute() as ipr:
        # Get interface index
        index = ipr.link_lookup(ifname='lo')
        ipr.tc('add', kind='cake', index=index, bandwidth='unlimited',
               autorate=True, nat=True, rtt='interplanetary', target=10000,
               flow_mode='dsthost', diffserv_mode='precedence', fwmark=0x1337)

NOTES:
    Here is the list of all supported options with their values:
    - ack_filter: False, True or 'aggressive' (False by default)
    - atm_mode: False, True or 'ptm' (False by default)
    - autorate: False or True (False by default)
    - bandwidth: any integer, 'N[kbit|mbit|gbit]' or 'unlimited'
    - diffserv_mode: 'diffserv3', 'diffserv4', 'diffserv8',
        'besteffort', 'precedence' ('diffserv3' by default)
    - ingress: False or True (False by default)
    - overhead: any integer between -64 and 256 inclusive (0 by default)
    - flow_mode: 'flowblind', 'srchost', 'dsthost', 'hosts', 'flows',
        'dual-srchost', 'dual-dsthost', 'triple-isolate'
        ('triple-isolate' by default)
    - fwmark: any integer (0 by default)
    - memlimit: any integer (by default, calculated based on the bandwidth
        and RTT settings)
    - mpu: any integer between 0 and 256 inclusive (0 by default)
    - nat: False or True (False by default)
    - raw: False or True (True by default)
    - rtt: any integer or 'datacentre', 'lan', 'metro', 'regional',
        'internet', 'oceanic', 'satellite', 'interplanetary'
        ('internet' by default)
    - split_gso: False or True (True by default)
    - target: any integer (5000 by default)
    - wash: False or True (False by default)
'''

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT

# Defines from pkt_sched.h
CAKE_FLOW_NONE = 0
CAKE_FLOW_SRC_IP = 1
CAKE_FLOW_DST_IP = 2
CAKE_FLOW_HOSTS = 3
CAKE_FLOW_FLOWS = 4
CAKE_FLOW_DUAL_SRC = 5
CAKE_FLOW_DUAL_DST = 6
CAKE_FLOW_TRIPLE = 7

CAKE_DIFFSERV_DIFFSERV3 = 0
CAKE_DIFFSERV_DIFFSERV4 = 1
CAKE_DIFFSERV_DIFFSERV8 = 2
CAKE_DIFFSERV_BESTEFFORT = 3
CAKE_DIFFSERV_PRECEDENCE = 4

CAKE_ACK_NONE = 0
CAKE_ACK_FILTER = 1
CAKE_ACK_AGGRESSIVE = 2

CAKE_ATM_NONE = 0
CAKE_ATM_ATM = 1
CAKE_ATM_PTM = 2

TCA_CAKE_MAX_TINS = 8


def fix_msg(msg, kwarg):
    if 'parent' not in kwarg:
        msg['parent'] = TC_H_ROOT


def convert_bandwidth(value):
    types = [('kbit', 1000), ('mbit', 1000000), ('gbit', 1000000000)]

    if 'unlimited' == value:
        return 0

    try:
        # Value is passed as an int
        x = int(value)
        return x >> 3
    except ValueError:
        value = value.lower()
        for t, mul in types:
            if len(value.split(t)) == 2:
                x = int(value.split(t)[0]) * mul
                return x >> 3

    raise ValueError(
        'Invalid bandwidth value. Specify either an integer, '
        '"unlimited" or a value with "kbit", "mbit" or '
        '"gbit" appended'
    )


def convert_rtt(value):
    types = {
        'datacentre': 100,
        'lan': 1000,
        'metro': 10000,
        'regional': 30000,
        'internet': 100000,
        'oceanic': 300000,
        'satellite': 1000000,
        'interplanetary': 3600000000,
    }

    try:
        # Value is passed as an int
        x = int(value)
        return x
    except ValueError:
        rtt = types.get(value.lower())
        if rtt is not None:
            return rtt
        raise ValueError(
            'Invalid rtt value. Specify either an integer (us), '
            'or datacentre, lan, metro, regional, internet, '
            'oceanic or interplanetary.'
        )


def convert_atm(value):
    if isinstance(value, bool):
        if not value:
            return CAKE_ATM_NONE
        else:
            return CAKE_ATM_ATM
    else:
        if value == 'ptm':
            return CAKE_ATM_PTM

    raise ValueError('Invalid ATM value!')


def convert_flowmode(value):
    modes = {
        'flowblind': CAKE_FLOW_NONE,
        'srchost': CAKE_FLOW_SRC_IP,
        'dsthost': CAKE_FLOW_DST_IP,
        'hosts': CAKE_FLOW_HOSTS,
        'flows': CAKE_FLOW_FLOWS,
        'dual-srchost': CAKE_FLOW_DUAL_SRC,
        'dual-dsthost': CAKE_FLOW_DUAL_DST,
        'triple-isolate': CAKE_FLOW_TRIPLE,
    }

    res = modes.get(value.lower())
    if res:
        return res
    raise ValueError(
        'Invalid flow mode specified! See tc-cake man '
        'page for valid values.'
    )


def convert_diffserv(value):
    modes = {
        'diffserv3': CAKE_DIFFSERV_DIFFSERV3,
        'diffserv4': CAKE_DIFFSERV_DIFFSERV4,
        'diffserv8': CAKE_DIFFSERV_DIFFSERV8,
        'besteffort': CAKE_DIFFSERV_BESTEFFORT,
        'precedence': CAKE_DIFFSERV_PRECEDENCE,
    }

    res = modes.get(value.lower())
    if res is not None:
        return res
    raise ValueError(
        'Invalid diffserv mode specified! See tc-cake man '
        'page for valid values.'
    )


def convert_ackfilter(value):
    if isinstance(value, bool):
        if not value:
            return CAKE_ACK_NONE
        else:
            return CAKE_ACK_FILTER
    else:
        if value == 'aggressive':
            return CAKE_ACK_AGGRESSIVE

    raise ValueError('Invalid ACK filter!')


def check_range(name, value, start, end):
    if not isinstance(value, int):
        raise ValueError('{} value must be an integer'.format(name))

    if not start <= value <= end:
        raise ValueError(
            '{0} value must be between {1} and {2} '
            'inclusive.'.format(name, start, end)
        )


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (
        ('ack_filter', 'TCA_CAKE_ACK_FILTER'),
        ('atm_mode', 'TCA_CAKE_ATM'),
        ('autorate', 'TCA_CAKE_AUTORATE'),
        ('bandwidth', 'TCA_CAKE_BASE_RATE64'),
        ('diffserv_mode', 'TCA_CAKE_DIFFSERV_MODE'),
        ('ingress', 'TCA_CAKE_INGRESS'),
        ('overhead', 'TCA_CAKE_OVERHEAD'),
        ('flow_mode', 'TCA_CAKE_FLOW_MODE'),
        ('fwmark', 'TCA_CAKE_FWMARK'),
        ('memlimit', 'TCA_CAKE_MEMORY'),
        ('mpu', 'TCA_CAKE_MPU'),
        ('nat', 'TCA_CAKE_NAT'),
        ('raw', 'TCA_CAKE_RAW'),
        ('rtt', 'TCA_CAKE_RTT'),
        ('split_gso', 'TCA_CAKE_SPLIT_GSO'),
        ('target', 'TCA_CAKE_TARGET'),
        ('wash', 'TCA_CAKE_WASH'),
    )

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            if k == 'bandwidth':
                r = convert_bandwidth(r)
            elif k == 'rtt':
                r = convert_rtt(r)
            elif k == 'atm_mode':
                r = convert_atm(r)
            elif k == 'flow_mode':
                r = convert_flowmode(r)
            elif k == 'diffserv_mode':
                r = convert_diffserv(r)
            elif k == 'ack_filter':
                r = convert_ackfilter(r)
            elif k == 'mpu':
                check_range(k, r, 0, 256)
            elif k == 'overhead':
                check_range(k, r, -64, 256)
            ret['attrs'].append([v, r])

    return ret


class options(nla):
    nla_map = (
        ('TCA_CAKE_UNSPEC', 'none'),
        ('TCA_CAKE_PAD', 'uint64'),
        ('TCA_CAKE_BASE_RATE64', 'uint64'),
        ('TCA_CAKE_DIFFSERV_MODE', 'uint32'),
        ('TCA_CAKE_ATM', 'uint32'),
        ('TCA_CAKE_FLOW_MODE', 'uint32'),
        ('TCA_CAKE_OVERHEAD', 'int32'),
        ('TCA_CAKE_RTT', 'uint32'),
        ('TCA_CAKE_TARGET', 'uint32'),
        ('TCA_CAKE_AUTORATE', 'uint32'),
        ('TCA_CAKE_MEMORY', 'uint32'),
        ('TCA_CAKE_NAT', 'uint32'),
        ('TCA_CAKE_RAW', 'uint32'),
        ('TCA_CAKE_WASH', 'uint32'),
        ('TCA_CAKE_MPU', 'uint32'),
        ('TCA_CAKE_INGRESS', 'uint32'),
        ('TCA_CAKE_ACK_FILTER', 'uint32'),
        ('TCA_CAKE_SPLIT_GSO', 'uint32'),
        ('TCA_CAKE_FWMARK', 'uint32'),
    )

    def encode(self):
        # Set default Auto-Rate value
        if not self.get_attr('TCA_CAKE_AUTORATE'):
            self['attrs'].append(['TCA_CAKE_AUTORATE', 0])
        nla.encode(self)


class stats2(nla):
    nla_map = (
        ('TCA_STATS_UNSPEC', 'none'),
        ('TCA_STATS_BASIC', 'basic'),
        ('TCA_STATS_RATE_EST', 'rate_est'),
        ('TCA_STATS_QUEUE', 'queue'),
        ('TCA_STATS_APP', 'stats_app'),
    )

    class basic(nla):
        fields = (('bytes', 'Q'), ('packets', 'I'))

    class rate_est(nla):
        fields = (('bps', 'I'), ('pps', 'I'))

    class queue(nla):
        fields = (
            ('qlen', 'I'),
            ('backlog', 'I'),
            ('drops', 'I'),
            ('requeues', 'I'),
            ('overlimits', 'I'),
        )

    class stats_app(nla):
        nla_map = (
            ('__TCA_CAKE_STATS_INVALID', 'none'),
            ('TCA_CAKE_STATS_PAD', 'hex'),
            ('TCA_CAKE_STATS_CAPACITY_ESTIMATE64', 'uint64'),
            ('TCA_CAKE_STATS_MEMORY_LIMIT', 'uint32'),
            ('TCA_CAKE_STATS_MEMORY_USED', 'uint32'),
            ('TCA_CAKE_STATS_AVG_NETOFF', 'uint32'),
            ('TCA_CAKE_STATS_MAX_NETLEN', 'uint32'),
            ('TCA_CAKE_STATS_MAX_ADJLEN', 'uint32'),
            ('TCA_CAKE_STATS_MIN_NETLEN', 'uint32'),
            ('TCA_CAKE_STATS_MIN_ADJLEN', 'uint32'),
            ('TCA_CAKE_STATS_TIN_STATS', 'tca_parse_tins'),
            ('TCA_CAKE_STATS_DEFICIT', 'uint32'),
            ('TCA_CAKE_STATS_COBALT_COUNT', 'uint32'),
            ('TCA_CAKE_STATS_DROPPING', 'uint32'),
            ('TCA_CAKE_STATS_DROP_NEXT_US', 'uint32'),
            ('TCA_CAKE_STATS_P_DROP', 'uint32'),
            ('TCA_CAKE_STATS_BLUE_TIMER_US', 'uint32'),
        )

        class tca_parse_tins(nla):
            nla_map = tuple(
                [
                    ('TCA_CAKE_TIN_STATS_%i' % x, 'tca_parse_tin_stats')
                    for x in range(TCA_CAKE_MAX_TINS)
                ]
            )

            class tca_parse_tin_stats(nla):
                nla_map = (
                    ('__TCA_CAKE_TIN_STATS_INVALID', 'none'),
                    ('TCA_CAKE_TIN_STATS_PAD', 'hex'),
                    ('TCA_CAKE_TIN_STATS_SENT_PACKETS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_SENT_BYTES64', 'uint64'),
                    ('TCA_CAKE_TIN_STATS_DROPPED_PACKETS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_DROPPED_BYTES64', 'uint64'),
                    ('TCA_CAKE_TIN_STATS_ACKS_DROPPED_PACKETS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_ACKS_DROPPED_BYTES64', 'uint64'),
                    ('TCA_CAKE_TIN_STATS_ECN_MARKED_PACKETS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_ECN_MARKED_BYTES64', 'uint64'),
                    ('TCA_CAKE_TIN_STATS_BACKLOG_PACKETS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_BACKLOG_BYTES', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_THRESHOLD_RATE64', 'uint64'),
                    ('TCA_CAKE_TIN_STATS_TARGET_US', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_INTERVAL_US', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_WAY_INDIRECT_HITS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_WAY_MISSES', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_WAY_COLLISIONS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_PEAK_DELAY_US', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_AVG_DELAY_US', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_BASE_DELAY_US', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_SPARSE_FLOWS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_BULK_FLOWS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_UNRESPONSIVE_FLOWS', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_MAX_SKBLEN', 'uint32'),
                    ('TCA_CAKE_TIN_STATS_FLOW_QUANTUM', 'uint32'),
                )
