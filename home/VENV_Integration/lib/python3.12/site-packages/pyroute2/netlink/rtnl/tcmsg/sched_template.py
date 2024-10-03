'''
Template sched file. All the tcmsg plugins should be
registered in `__init__.py`, see the `plugins` dict.

All the methods, variables and classes are optional,
but the naming scheme is fixed.
'''

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg import common

# if you define the `parent` variable, it will be used
# as the default parent value if no other value is
# provided in the call options
parent = TC_H_ROOT


def fix_msg(kwarg, msg):
    '''
    This method it called for all types -- classes,
    qdiscs and filters. Can be used to fix some `msg`
    fields.
    '''
    pass


def get_parameters(kwarg):
    '''
    Called for qdiscs and filters. Should return
    the structure to be embedded as the qdisc parameters
    (`TCA_OPTIONS`).
    '''
    return None


def get_class_parameters(kwarg):
    '''
    The same as above, but called only for classes.
    '''
    return None


class options(nla.hex):
    '''
    The `TCA_OPTIONS` struct, by default not decoded.
    '''

    pass


class stats(nla.hex):
    '''
    The struct to decode `TCA_XSTATS`.
    '''

    pass


class stats2(common.stats2):
    '''
    The struct to decode `TCA_STATS2`.
    '''

    pass
