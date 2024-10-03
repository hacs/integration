import logging
import os
import re
import struct
from math import log as logfm
from socket import inet_aton

from pyroute2 import config
from pyroute2.common import (
    basestring,
    rate_suffixes,
    size_suffixes,
    time_suffixes,
)
from pyroute2.netlink import nla, nla_string

log = logging.getLogger(__name__)

LINKLAYER_UNSPEC = 0
LINKLAYER_ETHERNET = 1
LINKLAYER_ATM = 2

ATM_CELL_SIZE = 53
ATM_CELL_PAYLOAD = 48

TCA_ACT_MAX_PRIO = 32
TIME_UNITS_PER_SEC = 1000000

try:
    with open('/proc/net/psched', 'r') as psched:
        [t2us, us2t, clock_res, wee] = [
            int(i, 16) for i in psched.read().split()
        ]
    clock_factor = float(clock_res) / TIME_UNITS_PER_SEC
    tick_in_usec = float(t2us) / us2t * clock_factor
except IOError as e:
    if config.uname[0] == 'Linux':
        log.warning("tcmsg: %s", e)
        log.warning("the tc subsystem functionality is limited")
    clock_res = 0
    clock_factor = 1
    tick_in_usec = 1
    wee = 1000

_first_letter = re.compile('[^0-9]+')


def get_hz():
    if clock_res == 1000000:
        return wee
    else:
        return os.environ.get('HZ', 1000)


def get_by_suffix(value, default, func):
    if not isinstance(value, basestring):
        return value
    pos = _first_letter.search(value)
    if pos is None:
        suffix = default
    else:
        pos = pos.start()
        value, suffix = value[:pos], value[pos:]
    value = int(value)
    return func(value, suffix)


def get_size(size):
    return get_by_suffix(size, 'b', lambda x, y: x * size_suffixes[y])


def get_time(lat):
    return get_by_suffix(
        lat, 'ms', lambda x, y: (x * TIME_UNITS_PER_SEC) / time_suffixes[y]
    )


def get_rate(rate):
    return get_by_suffix(rate, 'bit', lambda x, y: (x * rate_suffixes[y]) / 8)


def time2tick(time):
    # The code is ported from tc utility
    return int(time) * tick_in_usec


def calc_xmittime(rate, size):
    # The code is ported from tc utility
    return int(time2tick(TIME_UNITS_PER_SEC * (float(size) / rate)))


def percent2u32(pct):
    '''xlate a percentage to an uint32 value
    0% -> 0
    100% -> 2**32 - 1'''
    return int((2**32 - 1) * pct / 100)


def red_eval_ewma(qmin, burst, avpkt):
    # The code is ported from tc utility
    wlog = 1
    W = 0.5
    a = float(burst) + 1 - float(qmin) / avpkt
    if a < 1:
        raise ValueError(f'wrong a = {a}')

    while wlog < 32:
        wlog += 1
        W /= 2
        if a <= (1 - pow(1 - W, burst)) / W:
            return wlog
    return -1


def red_eval_P(qmin, qmax, probability):
    # The code is ported from tc utility
    i = qmax - qmin
    if i <= 0:
        raise ValueError(f'qmax - qmin must be > 0 (got {i})')

    probability /= i

    for i in range(32):
        if probability > 1:
            break
        probability *= 2

    return i


def red_eval_idle_damping(Wlog, avpkt, bps):
    # The code is ported from tc utility
    xmit_time = calc_xmittime(bps, avpkt)
    lW = -logfm(1.0 - 1.0 / (1 << Wlog)) / xmit_time
    maxtime = 31.0 / lW
    sbuf = []
    for clog in range(32):
        if maxtime / (1 << clog) < 512:
            break
    if clog >= 32:
        return -1, sbuf
    for i in range(255):
        sbuf.append((i << clog) * lW)
        if sbuf[i] > 31:
            sbuf[i] = 31
    sbuf.append(31)
    return clog, sbuf


def get_rate_parameters(kwarg):
    # rate and burst are required
    rate = get_rate(kwarg['rate'])
    burst = kwarg['burst']

    # if peak, mtu is required
    peak = get_rate(kwarg.get('peak', 0))
    mtu = kwarg.get('mtu', 0)
    if peak:
        assert mtu

    # limit OR latency is required
    limit = kwarg.get('limit', None)
    latency = get_time(kwarg.get('latency', None))
    assert limit is not None or latency is not None

    # calculate limit from latency
    if limit is None:
        rate_limit = rate * float(latency) / TIME_UNITS_PER_SEC + burst
        if peak:
            peak_limit = peak * float(latency) / TIME_UNITS_PER_SEC + mtu
            if rate_limit > peak_limit:
                rate_limit = peak_limit
        limit = rate_limit

    return {
        'rate': int(rate),
        'mtu': mtu,
        'buffer': calc_xmittime(rate, burst),
        'limit': int(limit),
    }


tc_flow_keys = {
    'src': 0x01,
    'dst': 0x02,
    'proto': 0x04,
    'proto-src': 0x08,
    'proto-dst': 0x10,
    'iif': 0x20,
    'priority': 0x40,
    'mark': 0x80,
    'nfct': 0x0100,
    'nfct-src': 0x0200,
    'nfct-dst': 0x0400,
    'nfct-proto-src': 0x0800,
    'nfct-proto-dst': 0x1000,
    'rt-classid': 0x2000,
    'sk-uid': 0x4000,
    'sk-gid': 0x8000,
    'vlan-tag': 0x010000,
    'rxhash': 0x020000,
}


def get_tca_keys(kwarg, name):
    if name not in kwarg:
        raise ValueError('Missing attribute: {0}'.format(name))

    res = 0
    keys = kwarg[name]
    if name == 'hash':
        keys = keys.split(',')

    for key, value in tc_flow_keys.items():
        if key in keys:
            res |= value

    return res


tc_flow_modes = {'map': 0, 'hash': 1}


def get_tca_mode(kwarg):
    if 'mode' not in kwarg:
        raise ValueError('Missing attribute: mode')

    for key, value in tc_flow_modes.items():
        if key == kwarg['mode']:
            return value

    raise ValueError('Unknown flow mode {0}'.format(kwarg['mode']))


def get_tca_ops(kwarg, attrs):
    xor_value = 0
    mask_value = 0
    addend_value = 0
    rshift_value = 0

    for elem in kwarg['ops']:
        op = elem['op']
        num = elem['num']

        if op == 'and':
            mask_value = num
            attrs.append(['TCA_FLOW_XOR', xor_value])
            attrs.append(['TCA_FLOW_MASK', mask_value])
        elif op == 'or':
            if mask_value == 0:
                mask_value = (~num + 1) & 0xFFFFFFFF
            xor_value = num
            attrs.append(['TCA_FLOW_XOR', xor_value])
            attrs.append(['TCA_FLOW_MASK', mask_value])
        elif op == 'xor':
            if mask_value == 0:
                mask_value = 0xFFFFFFFF
            xor_value = num
            attrs.append(['TCA_FLOW_XOR', xor_value])
            attrs.append(['TCA_FLOW_MASK', mask_value])
        elif op == 'rshift':
            rshift_value = num
            attrs.append(['TCA_FLOW_RSHIFT', rshift_value])
        elif op == 'addend':
            # Check if an IP was specified
            if isinstance(num, str) and len(num.split('.')) == 4:
                if num.startswith('-'):
                    inverse = True
                else:
                    inverse = False
                ip = num.strip('-')

                # Convert IP to uint32
                ip = inet_aton(ip)
                ip = struct.unpack('>I', ip)[0]

                if inverse:
                    ip = (~ip + 1) & 0xFFFFFFFF
                addend_value = ip
            else:
                addend_value = num
            attrs.append(['TCA_FLOW_ADDEND', addend_value])


tc_actions = {
    'unspec': -1,  # TC_ACT_UNSPEC
    'ok': 0,  # TC_ACT_OK
    'reclassify': 1,  # TC_ACT_RECLASSIFY
    'shot': 2,  # TC_ACT_SHOT
    'drop': 2,  # TC_ACT_SHOT
    'pipe': 3,  # TC_ACT_PIPE
    'stolen': 4,  # TC_ACT_STOLEN
    'queued': 5,  # TC_ACT_QUEUED
    'repeat': 6,  # TC_ACT_REPEAT
    'redirect': 7,  # TC_ACT_REDIRECT
}


class nla_plus_rtab(nla):
    class parms(nla):
        def adjust_size(self, size, mpu, linklayer):
            # The current code is ported from tc utility
            if size < mpu:
                size = mpu

            if linklayer == LINKLAYER_ATM:
                cells = size / ATM_CELL_PAYLOAD
                if size % ATM_CELL_PAYLOAD > 0:
                    cells += 1
                size = cells * ATM_CELL_SIZE

            return size

        def calc_rtab(self, kind):
            # The current code is ported from tc utility
            rtab = []
            mtu = self.get('mtu', 0) or 1600
            cell_log = self['%s_cell_log' % (kind)]
            mpu = self['%s_mpu' % (kind)]
            rate = self.get(kind, 'rate')

            # calculate cell_log
            if cell_log == 0:
                while (mtu >> cell_log) > 255:
                    cell_log += 1

            # fill up the table
            for i in range(256):
                size = self.adjust_size(
                    (i + 1) << cell_log, mpu, LINKLAYER_ETHERNET
                )
                rtab.append(calc_xmittime(rate, size))

            self['%s_cell_align' % (kind)] = -1
            self['%s_cell_log' % (kind)] = cell_log
            return rtab

        def encode(self):
            self.rtab = None
            self.ptab = None
            if self.get('rate', False):
                self.rtab = self.calc_rtab('rate')
            if self.get('peak', False):
                self.ptab = self.calc_rtab('peak')
            if self.get('ceil', False):
                self.ctab = self.calc_rtab('ceil')
            nla.encode(self)

    class rtab(nla_string):
        own_parent = True

        def encode(self):
            parms = (
                self.parent.get_encoded('TCA_TBF_PARMS')
                or self.parent.get_encoded('TCA_HTB_PARMS')
                or self.parent.get_encoded('TCA_POLICE_TBF')
            )
            if parms is not None:
                self.value = getattr(parms, self.__class__.__name__)
                self['value'] = struct.pack(
                    'I' * 256, *(int(x) for x in self.value)
                )
            nla_string.encode(self)

        def decode(self):
            nla_string.decode(self)
            parms = (
                self.parent.get_attr('TCA_TBF_PARMS')
                or self.parent.get_attr('TCA_HTB_PARMS')
                or self.parent.get_attr('TCA_POLICE_TBF')
            )
            if parms is not None:
                rtab = struct.unpack(
                    'I' * (len(self['value']) / 4), self['value']
                )
                self.value = rtab
                setattr(parms, self.__class__.__name__, rtab)

    class ptab(rtab):
        pass

    class ctab(rtab):
        pass


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

    class stats_app(nla.hex):
        pass
