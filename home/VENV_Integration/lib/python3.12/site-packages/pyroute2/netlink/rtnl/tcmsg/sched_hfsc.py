'''
hfsc
++++

Simple HFSC example::

    eth0 = ip.get_links(ifname="eth0")[0]
    ip.tc("add", "hfsc", eth0,
          handle="1:",
          default="1:1")
    ip.tc("add-class", "hfsc", eth0,
          handle="1:1",
          parent="1:0"
          rsc={"m2": "5mbit"})

HFSC curve nla types:

* `rsc`: real-time curve
* `fsc`: link-share curve
* `usc`: upper-limit curve
'''

from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import RTM_DELQDISC, RTM_NEWQDISC, TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import get_rate, get_time
from pyroute2.netlink.rtnl.tcmsg.common import stats2 as c_stats2

parent = TC_H_ROOT


def get_parameters(kwarg):
    defcls = kwarg.get('default', kwarg.get('defcls', 0x10))
    defcls &= 0xFFFF
    return {'defcls': defcls}


def get_class_parameters(kwarg):
    ret = {'attrs': []}
    for key in ('rsc', 'fsc', 'usc'):
        if key in kwarg:
            ret['attrs'].append(
                [
                    'TCA_HFSC_%s' % key.upper(),
                    {
                        'm1': get_rate(kwarg[key].get('m1', 0)),
                        'd': get_time(kwarg[key].get('d', 0)),
                        'm2': get_rate(kwarg[key].get('m2', 0)),
                    },
                ]
            )
    return ret


class options_hfsc(nla):
    fields = (('defcls', 'H'),)  # default class


class options_hfsc_class(nla):
    nla_map = (
        ('TCA_HFSC_UNSPEC', 'none'),
        ('TCA_HFSC_RSC', 'hfsc_curve'),  # real-time curve
        ('TCA_HFSC_FSC', 'hfsc_curve'),  # link-share curve
        ('TCA_HFSC_USC', 'hfsc_curve'),
    )  # upper-limit curve

    class hfsc_curve(nla):
        fields = (
            ('m1', 'I'),  # slope of the first segment in bps
            ('d', 'I'),  # x-projection of the first segment in us
            ('m2', 'I'),
        )  # slope of the second segment in bps


def options(msg, *argv, **kwarg):
    if msg['header']['type'] in (RTM_NEWQDISC, RTM_DELQDISC):
        return options_hfsc
    else:
        return options_hfsc_class


class stats2(c_stats2):
    class stats_app(nla):
        fields = (
            ('work', 'Q'),  # total work done
            ('rtwork', 'Q'),  # total work done by real-time criteria
            ('period', 'I'),  # current period
            ('level', 'I'),
        )  # class level in hierarchy
