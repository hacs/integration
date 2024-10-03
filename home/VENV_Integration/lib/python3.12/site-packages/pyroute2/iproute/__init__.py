# -*- coding: utf-8 -*-
'''
Classes
-------

The RTNL API is provided by the class `RTNL_API`. It is a
mixin class that works on top of any RTNL-compatible socket,
so several classes with almost the same API are available:

* `IPRoute` -- simple RTNL API
* `NetNS` -- RTNL API in a network namespace
* `IPBatch` -- RTNL packet compiler
* `RemoteIPRoute` -- run RTNL remotely (no deployment required)

Responses as lists
------------------

The netlink socket implementation in the pyroute2 is
agnostic to particular netlink protocols, and always returns
a list of messages as the response to a request sent to the
kernel::

    with IPRoute() as ipr:

        # this request returns one match
        eth0 = ipr.link_lookup(ifname='eth0')
        len(eth0)  # -> 1, if exists, else 0

        # but that one returns a set of
        up = ipr.link_lookup(operstate='UP')
        len(up)  # -> k, where 0 <= k <= [interface count]

Thus, always expect a list in the response, running any
`IPRoute()` netlink request.

NLMSG_ERROR responses
~~~~~~~~~~~~~~~~~~~~~

Some kernel subsystems return `NLMSG_ERROR` in response to
any request. It is OK as long as `nlmsg["header"]["error"] is None`.
Otherwise an exception will be raised by the parser.

So if instead of an exception you get a `NLMSG_ERROR` message,
it means `error == 0`, the same as `$? == 0` in bash.

How to work with messages
~~~~~~~~~~~~~~~~~~~~~~~~~

Every netlink message contains header, fields and NLAs
(netlink attributes). Every NLA is a netlink message...
(see "recursion").

And the library provides parsed messages according to
this scheme. Every RTNL message contains:

* `nlmsg['header']` -- parsed header
* `nlmsg['attrs']` -- NLA chain (parsed on demand)
* 0 .. k data fields, e.g. `nlmsg['flags']` etc.
* `nlmsg.header` -- the header fields spec
* `nlmsg.fields` -- the data fields spec
* `nlmsg.nla_map` -- NLA spec

An important parser feature is that NLAs are parsed
on demand, when someone tries to access them. Otherwise
the parser doesn't waste CPU cycles.

The NLA chain is a list-like structure, not a dictionary.
The netlink standard doesn't require NLAs to be unique
within one message::

    {'attrs': [('IFLA_IFNAME', 'lo'),    # [1]
               ('IFLA_TXQLEN', 1),
               ('IFLA_OPERSTATE', 'UNKNOWN'),
               ('IFLA_LINKMODE', 0),
               ('IFLA_MTU', 65536),
               ('IFLA_GROUP', 0),
               ('IFLA_PROMISCUITY', 0),
               ('IFLA_NUM_TX_QUEUES', 1),
               ('IFLA_NUM_RX_QUEUES', 1),
               ('IFLA_CARRIER', 1),
               ...],
     'change': 0,
     'event': 'RTM_NEWLINK',             # [2]
     'family': 0,
     'flags': 65609,
     'header': {'error': None,           # [3]
                'flags': 2,
                'length': 1180,
                'pid': 28233,
                'sequence_number': 257,  # [4]
                'type': 16},             # [5]
     'ifi_type': 772,
     'index': 1}

     # [1] every NLA is parsed upon access
     # [2] this field is injected by the RTNL parser
     # [3] if not None, an exception will be raised
     # [4] more details in the netlink description
     # [5] 16 == RTM_NEWLINK

To access fields::

    msg['index'] == 1

To access one NLA::

    msg.get_attr('IFLA_CARRIER') == 1

When an NLA with the specified name is not present in the
chain, `get_attr()` returns `None`. To get the list of all
NLAs of that name, use `get_attrs()`. A real example with
NLA hierarchy, take notice of `get_attr()` and
`get_attrs()` usage::

    # for macvlan interfaces there may be several
    # IFLA_MACVLAN_MACADDR NLA provided, so use
    # get_attrs() to get all the list, not only
    # the first one

    (msg
     .get_attr('IFLA_LINKINFO')           # one NLA
     .get_attr('IFLA_INFO_DATA')          # one NLA
     .get_attrs('IFLA_MACVLAN_MACADDR'))  # a list of

The protocol itself has no limit for number of NLAs of the
same type in one message, that's why we can not make a dictionary
from them -- unlike PF_ROUTE messages.

'''
import sys

from pyroute2 import config
from pyroute2.iproute.linux import RTNL_API, IPBatch

# compatibility fix -- LNST:
from pyroute2.netlink.rtnl import (
    RTM_DELADDR,
    RTM_DELLINK,
    RTM_GETADDR,
    RTM_GETLINK,
    RTM_NEWADDR,
    RTM_NEWLINK,
)

if sys.platform.startswith('emscripten'):
    from pyroute2.iproute.ipmock import ChaoticIPRoute, IPRoute, RawIPRoute
elif sys.platform.startswith('win'):
    from pyroute2.iproute.windows import ChaoticIPRoute, IPRoute, RawIPRoute
elif config.uname[0][-3:] == 'BSD':
    from pyroute2.iproute.bsd import ChaoticIPRoute, IPRoute, RawIPRoute
else:
    from pyroute2.iproute.linux import ChaoticIPRoute, IPRoute, RawIPRoute

classes = [RTNL_API, IPBatch, IPRoute, RawIPRoute, ChaoticIPRoute]

constants = [
    RTM_GETLINK,
    RTM_NEWLINK,
    RTM_DELLINK,
    RTM_GETADDR,
    RTM_NEWADDR,
    RTM_DELADDR,
]
