'''
htb
+++

TODO: list parameters

An example with htb qdisc, lets assume eth0 == 2::

    #          u32 -->    +--> htb 1:10 --> sfq 10:0
    #          |          |
    #          |          |
    # eth0 -- htb 1:0 -- htb 1:1
    #          |          |
    #          |          |
    #          u32 -->    +--> htb 1:20 --> sfq 20:0

    eth0 = 2
    # add root queue 1:0
    ip.tc("add", "htb", eth0, 0x10000, default=0x200000)

    # root class 1:1
    ip.tc("add-class", "htb", eth0, 0x10001,
          parent=0x10000,
          rate="256kbit",
          burst=1024 * 6)

    # two branches: 1:10 and 1:20
    ip.tc("add-class", "htb", eth0, 0x10010,
          parent=0x10001,
          rate="192kbit",
          burst=1024 * 6,
          prio=1)
    ip.tc("add-class", "htb", eht0, 0x10020,
          parent=0x10001,
          rate="128kbit",
          burst=1024 * 6,
          prio=2)

    # two leaves: 10:0 and 20:0
    ip.tc("add", "sfq", eth0, 0x100000,
          parent=0x10010,
          perturb=10)
    ip.tc("add", "sfq", eth0, 0x200000,
          parent=0x10020,
          perturb=10)

    # two filters: one to load packets into 1:10 and the
    # second to 1:20
    ip.tc("add-filter", "u32", eth0,
          parent=0x10000,
          prio=10,
          protocol=socket.AF_INET,
          target=0x10010,
          keys=["0x0006/0x00ff+8", "0x0000/0xffc0+2"])
    ip.tc("add-filter", "u32", eth0,
          parent=0x10000,
          prio=10,
          protocol=socket.AF_INET,
          target=0x10020,
          keys=["0x5/0xf+0", "0x10/0xff+33"])
'''

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import RTM_DELQDISC, RTM_NEWQDISC, TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import (
    calc_xmittime,
    get_hz,
    get_rate,
    nla_plus_rtab,
    stats2,
)

parent = TC_H_ROOT


def get_class_parameters(kwarg):
    prio = kwarg.get('prio', 0)
    mtu = kwarg.get('mtu', 1600)
    mpu = kwarg.get('mpu', 0)
    overhead = kwarg.get('overhead', 0)
    quantum = kwarg.get('quantum', 0)
    rate = get_rate(kwarg.get('rate', None))
    ceil = get_rate(kwarg.get('ceil', 0)) or rate

    burst = (
        kwarg.get('burst', None)
        or kwarg.get('maxburst', None)
        or kwarg.get('buffer', None)
    )

    if rate is not None:
        if burst is None:
            burst = rate / get_hz() + mtu
        burst = calc_xmittime(rate, burst)

    cburst = (
        kwarg.get('cburst', None)
        or kwarg.get('cmaxburst', None)
        or kwarg.get('cbuffer', None)
    )

    if ceil is not None:
        if cburst is None:
            cburst = ceil / get_hz() + mtu
        cburst = calc_xmittime(ceil, cburst)

    return {
        'attrs': [
            [
                'TCA_HTB_PARMS',
                {
                    'buffer': burst,
                    'cbuffer': cburst,
                    'quantum': quantum,
                    'prio': prio,
                    'rate': rate,
                    'ceil': ceil,
                    'ceil_overhead': overhead,
                    'rate_overhead': overhead,
                    'rate_mpu': mpu,
                    'ceil_mpu': mpu,
                },
            ],
            ['TCA_HTB_RTAB', True],
            ['TCA_HTB_CTAB', True],
        ]
    }


def get_parameters(kwarg):
    rate2quantum = kwarg.get('r2q', 0xA)
    version = kwarg.get('version', 3)
    defcls = kwarg.get('default', 0x10)

    return {
        'attrs': [
            [
                'TCA_HTB_INIT',
                {
                    'debug': 0,
                    'defcls': defcls,
                    'direct_pkts': 0,
                    'rate2quantum': rate2quantum,
                    'version': version,
                },
            ]
        ]
    }


def fix_msg(msg, kwarg):
    if not kwarg:
        opts = get_parameters({})
        msg['attrs'].append(['TCA_OPTIONS', opts])


# The tokens and ctokens are badly defined in the kernel structure
# as unsigned int instead of signed int. (cf net/sched/sch_htb.c
# in linux source)
class stats(nla):
    fields = (
        ('lends', 'I'),
        ('borrows', 'I'),
        ('giants', 'I'),
        ('tokens', 'i'),
        ('ctokens', 'i'),
    )


class qdisc_stats2(stats2):
    nla_map = (
        ('TCA_STATS_UNSPEC', 'none'),
        ('TCA_STATS_BASIC', 'basic'),
        ('TCA_STATS_RATE_EST', 'rate_est'),
        ('TCA_STATS_QUEUE', 'queue'),
    )


class class_stats2(stats2):
    class stats_app(stats):
        pass


def stats2(msg, *argv, **kwarg):
    if msg['header']['type'] in (RTM_NEWQDISC, RTM_DELQDISC):
        return qdisc_stats2
    else:
        return class_stats2


class options(nla_plus_rtab):
    nla_map = (
        ('TCA_HTB_UNSPEC', 'none'),
        ('TCA_HTB_PARMS', 'htb_parms'),
        ('TCA_HTB_INIT', 'htb_glob'),
        ('TCA_HTB_CTAB', 'ctab'),
        ('TCA_HTB_RTAB', 'rtab'),
    )

    class htb_glob(nla):
        fields = (
            ('version', 'I'),
            ('rate2quantum', 'I'),
            ('defcls', 'I'),
            ('debug', 'I'),
            ('direct_pkts', 'I'),
        )

    class htb_parms(nla_plus_rtab.parms):
        fields = (
            ('rate_cell_log', 'B'),
            ('rate___reserved', 'B'),
            ('rate_overhead', 'H'),
            ('rate_cell_align', 'h'),
            ('rate_mpu', 'H'),
            ('rate', 'I'),
            ('ceil_cell_log', 'B'),
            ('ceil___reserved', 'B'),
            ('ceil_overhead', 'H'),
            ('ceil_cell_align', 'h'),
            ('ceil_mpu', 'H'),
            ('ceil', 'I'),
            ('buffer', 'I'),
            ('cbuffer', 'I'),
            ('quantum', 'I'),
            ('level', 'I'),
            ('prio', 'I'),
        )
