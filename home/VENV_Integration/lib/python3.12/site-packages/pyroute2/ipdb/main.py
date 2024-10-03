# -*- coding: utf-8 -*-
'''
IPDB guide
==========

.. warning::
    The IPDB module has design issues that may not be
    fixed. It is recommended to switch to NDB wherever
    it's possible.

Basically, IPDB is a transactional database, containing
records, that represent network stack objects. Any change
in the database is not reflected immediately in OS, but
waits until `commit()` is called. One failed operation
during `commit()` rolls back all the changes, has been made
so far. Moreover, IPDB has commit hooks API, that allows
you to roll back changes depending on your own function
calls, e.g. when a host or a network becomes unreachable.

Limitations
-----------

One of the major issues with IPDB is its memory footprint. It
proved not to be suitable for environments with thousands of
routes or neighbours. Being a design issue, it could not be
fixed, so a new module was started, NDB, that aims to replace
IPDB. IPDB is still more feature rich, but NDB is already more
fast and stable.

IPDB, NDB, IPRoute
------------------

These modules use different approaches.

* IPRoute just forwards requests to the kernel, and doesn't
  wait for the system state. So it's up to developer to check,
  whether the requested object is really set up or not.
* IPDB is an asynchronously updated database, that starts
  several additional threads by default. If your project's policy
  doesn't allow implicit threads, keep it in mind. But unlike IPRoute,
  the IPDB ensures the changes to be reflected in the system.
* NDB is like IPDB, and will obsolete it in the future. The difference
  is that IPDB creates Python object for every RTNL object, while
  NDB stores everything in an SQL DB, and creates objects on demand.

Being asynchronously updated, IPDB does sync on commit::

    with IPDB() as ipdb:
        with ipdb.interfaces['eth0'] as i:
            i.up()
            i.add_ip('192.168.0.2/24')
            i.add_ip('192.168.0.3/24')
        # ---> <--- here you can expect `eth0` is up
        #           and has these two addresses, so
        #           the following code can rely on that

NB: *In the example above `commit()` is implied with the
`__exit__()` of the `with` statement.*

IPDB and other software
-----------------------

IPDB is designed to be a non-exclusive network settings database.
There may be several IPDB instances on the same OS, as well as
other network management software, such as NetworkManager etc.

The IPDB transactions should not interfere with other software
settings, unless they touch the same objects. E.g., if IPDB
brings an interface up, while NM shuts it down, there will be
a race condition.

An example::

    # IPDB code                       #  NetworkManager at the same time:
    ipdb.interfaces['eth0'].up()      #
    ipdb.interfaces['eth0'].commit()  #  $ sudo nmcli con down eth0
    # ---> <---
    # The eth0 state here is undefined. Some of the commands
    # above will fail

But as long as the software doesn't touch the same objects, there
will be no conflicts. Another example::

    # IPDB code                         # At the same time, NetworkManager
    with ipdb.interfaces['eth0'] as i:  # adds addresses:
        i.add_ip('172.16.254.2/24')     #  * 10.0.0.2/24
        i.add_ip('172.16.254.3/24')     #  * 10.0.0.3/24
    # ---> <---
    # At this point the eth0 interface will have all four addresses.
    # If the IPDB transaction fails by some reason, only IPDB addresses
    # will be rolled back.

There may be a need to prevent other software from changing the network
settings. There is no locking at the kernel level, but IPDB can revert
all the changes as soon as they appear on the interface::

    # IPDB code
    ipdb.interfaces['eth0'].freeze()
                                       # Here some other software tries to
                                       # add an address, or to remove the old
                                       # one
    # ---> <---
    # At this point the eth0 interface will have all the same settings as
    # at the `freeze()` call moment. Newly added addresses will be removed,
    # all the deleted addresses will be restored.
    #
    # Please notice, that an address removal may cause also a routes removal,
    # and that is the thing that IPDB can not neither prevent, nor revert.

    ipdb.interfaces['eth0'].unfreeze()

Quickstart
----------

Simple tutorial::

    from pyroute2 import IPDB
    # several IPDB instances are supported within on process
    ipdb = IPDB()

    # commit is called automatically upon the exit from `with`
    # statement
    with ipdb.interfaces.eth0 as i:
        i.address = '00:11:22:33:44:55'
        i.ifname = 'bala'
        i.txqlen = 2000

    # basic routing support
    ipdb.routes.add({'dst': 'default',
                     'gateway': '10.0.0.1'}).commit()

    # do not forget to shutdown IPDB
    ipdb.release()

Please, notice `ip.release()` call in the end. Though it is
not forced in an interactive python session for the better
user experience, it is required in the scripts to sync the
IPDB state before exit.

IPDB supports functional-like syntax also::

    from pyroute2 import IPDB
    with IPDB() as ipdb:
        intf = (ipdb.interfaces['eth0']
                .add_ip('10.0.0.2/24')
                .add_ip('10.0.0.3/24')
                .set_address('00:11:22:33:44:55')
                .set_mtu(1460)
                .set_name('external')
                .commit())
        # ---> <--- here you have the interface reference with
        #           all the changes applied: renamed, added ipaddr,
        #           changed macaddr and mtu.
        ...  # some code

    # pls notice, that the interface reference will not work
    # outside of `with IPDB() ...`

Transaction modes
-----------------
IPDB has several operating modes:

    - 'implicit' (default) -- the first change starts an implicit
        transaction, that have to be committed
    - 'explicit' -- you have to begin() a transaction prior to
        make any change

The default is to use implicit transaction. This behaviour
can be changed in the future, so use 'mode' argument when
creating IPDB instances.

The sample session with explicit transactions::

    In [1]: from pyroute2 import IPDB
    In [2]: ip = IPDB(mode='explicit')
    In [3]: ifdb = ip.interfaces
    In [4]: ifdb.tap0.begin()
        Out[3]: UUID('7a637a44-8935-4395-b5e7-0ce40d31d937')
    In [5]: ifdb.tap0.up()
    In [6]: ifdb.tap0.address = '00:11:22:33:44:55'
    In [7]: ifdb.tap0.add_ip('10.0.0.1', 24)
    In [8]: ifdb.tap0.add_ip('10.0.0.2', 24)
    In [9]: ifdb.tap0.review()
        Out[8]:
        {'+ipaddr': set([('10.0.0.2', 24), ('10.0.0.1', 24)]),
         '-ipaddr': set([]),
         'address': '00:11:22:33:44:55',
         'flags': 4099}
    In [10]: ifdb.tap0.commit()


Note, that you can `review()` the `current_tx` transaction,
and `commit()` or `drop()` it. Also, multiple transactions
are supported, use uuid returned by `begin()` to identify
them.

Actually, the form like 'ip.tap0.address' is an eye-candy.
The IPDB objects are dictionaries, so you can write the code
above as that::

    ipdb.interfaces['tap0'].down()
    ipdb.interfaces['tap0']['address'] = '00:11:22:33:44:55'
    ...

Context managers
----------------

Transactional objects (interfaces, routes) can act as context
managers in the same way as IPDB does itself::

    with ipdb.interfaces.tap0 as i:
        i.address = '00:11:22:33:44:55'
        i.ifname = 'vpn'
        i.add_ip('10.0.0.1', 24)
        i.add_ip('10.0.0.1', 24)

On exit, the context manager will automatically `commit()`
the transaction.

Read-only interface views
-------------------------

Using an interface as a context manager **will** start a
transaction. Sometimes it is not what one needs. To avoid
unnecessary transactions, and to avoid the risk to occasionally
change interface attributes, one can use read-only views::

    with ipdb.interfaces[1].ro as iface:
        print(iface.ifname)
        print(iface.address)

The `.ro` view neither starts transactions, nor allows to
change anything, raising the `RuntimeError` exception.

The same read-only views are available for routes and rules.

Create interfaces
-----------------

IPDB can also create virtual interfaces::

    with ipdb.create(kind='bridge', ifname='control') as i:
        i.add_port(ip.interfaces.eth1)
        i.add_port(ip.interfaces.eth2)
        i.add_ip('10.0.0.1/24')


The `IPDB.create()` call has the same syntax as
`IPRoute.link('add', ...)`, except you shouldn't specify
the `'add'` command. Refer to `IPRoute` docs for details.

Please notice, that the interface object stays in the database
even if there was an error during the interface creation. It is
done so to make it possible to fix the interface object and try
to run `commit()` again. Or you can drop the interface object
with the `.remove().commit()` call.

IP address management
---------------------

IP addresses on interfaces may be managed using `add_ip()` and
`del_ip()`::

    with ipdb.interfaces['eth0'] as eth:
        eth.add_ip('10.0.0.1/24')
        eth.add_ip('10.0.0.2/24')
        eth.add_ip('2001:4c8:1023:108::39/64')
        eth.del_ip('172.16.12.5/24')

The address format may be either a string with `'address/mask'`
notation, or a pair of `'address', mask`::

    with ipdb.interfaces['eth0'] as eth:
        eth.add_ip('10.0.0.1', 24)
        eth.del_ip('172.16.12.5', 24)

The `ipaddr` attribute contains all the IP addresses of the
interface, which are accessible in different ways. Getting an
iterator from `ipaddr` gives you a sequence of tuples
`('address', mask)`:

.. doctest::
    :skipif: True

    >>> for addr in ipdb.interfaces['eth0'].ipaddr:
    ...    print(ipaddr)
    ...
    ('10.0.0.2', 24)
    ('10.0.0.1', 24)

Getting one IP from `ipaddr` returns a dict object with full spec:

.. doctest::
    :skipif: True

    >>> ipdb.interfaces['eth0'].ipaddr[0]
        {'family': 2,
         'broadcast': None,
         'flags': 128,
         'address': '10.0.0.2',
         'prefixlen': 24,
         'local': '10.0.0.2'}

    >>> ipdb.intefaces['eth0'].ipaddr['10.0.0.2/24']
        {'family': 2,
         'broadcast': None,
         'flags': 128,
         'address': '10.0.0.2',
         'prefixlen': 24,
         'local': '10.0.0.2'}

The API is a bit weird, but it's because of historical reasons. In
the future it may be changed.

Another feature of the `ipaddr` attribute is views:

.. doctest::
    :skipif: True

    >>> ipdb.interfaces['eth0'].ipaddr.ipv4:
        (('10.0.0.2', 24), ('10.0.0.1', 24))
    >>> ipdb.interfaces['eth0'].ipaddr.ipv6:
        (('2001:4c8:1023:108::39', 64),)

The views, as well as the `ipaddr` attribute itself are not supposed
to be changed by user, but only by the internal API.

Bridge interfaces
-----------------

Modern kernels provide possibility to manage bridge
interface properties such as STP, forward delay, ageing
time etc. Names of these properties start with `br_`, like
`br_ageing_time`, `br_forward_delay` e.g.::

    [x for x in dir(ipdb.interfaces.virbr0) if x.startswith('br_')]

Bridge ports
------------

IPDB supports specific bridge port parameters, such as proxyarp,
unicast/multicast flood, cost etc.::

    with ipdb.interfaces['br-port0'] as p:
        p.brport_cost = 200
        p.brport_unicast_flood = 0
        p.brport_proxyarp = 0

Ports management
----------------

IPDB provides a uniform API to manage bridge, bond and vrf ports::

    with ipdb.interfaces['br-int'] as br:
        br.add_port('veth0')
        br.add_port(ipdb.interfaces.veth1)
        br.add_port(700)
        br.del_port('veth2')

Both `add_port()` and `del_port()` accept three types of arguments:

    * `'veth0'` -- interface name as a string
    * `ipdb.interfaces.veth1` -- IPDB interface object
    * `700` -- interface index, an integer

Routes management
-----------------

IPDB has a simple yet useful routing management interface.

Create a route
~~~~~~~~~~~~~~

To add a route, there is an easy to use syntax::

    # spec as a dictionary
    spec = {'dst': '172.16.1.0/24',
            'oif': 4,
            'gateway': '192.168.122.60',
            'metrics': {'mtu': 1400,
                        'advmss': 500}}

    # pass spec as is
    ipdb.routes.add(spec).commit()

    # pass spec as kwargs
    ipdb.routes.add(**spec).commit()

    # use keyword arguments explicitly
    ipdb.routes.add(dst='172.16.1.0/24', oif=4, ...).commit()

Please notice, that the device can be specified with `oif`
(output interface) or `iif` (input interface), the `device`
keyword is not supported anymore.

More examples::

    # specify table and priority
    (ipdb.routes
     .add(dst='172.16.1.0/24',
          gateway='192.168.0.1',
          table=100,
          priority=10)
     .commit())

The `priority` field is what the `iproute2` utility calls
`metric` -- see also below.

Get a route
~~~~~~~~~~~

To access and change the routes, one can use notations as
follows::

    # default table (254)
    #
    # change the route gateway and mtu
    #
    with ipdb.routes['172.16.1.0/24'] as route:
        route.gateway = '192.168.122.60'
        route.metrics.mtu = 1500

    # access the default route
    print(ipdb.routes['default'])

    # change the default gateway
    with ipdb.routes['default'] as route:
        route.gateway = '10.0.0.1'

By default, the path `ipdb.routes` reflects only the main
routing table (254). But Linux supports much more routing
tables, so does IPDB::

    In [1]: ipdb.routes.tables.keys()
    Out[1]: [0, 254, 255]

    In [2]: len(ipdb.routes.tables[255])
    Out[2]: 11  # => 11 automatic routes in the table local

It is important to understand, that routing tables keys in
IPDB are not only the destination prefix. The key consists
of 'prefix/mask' string and the route priority (if any)::

    In [1]: ipdb.routes.tables[254].idx.keys()
    Out[1]:
    [RouteKey(dst='default', table=254, family=2, ...),
     RouteKey(dst='172.17.0.0/16', table=254, ...),
     RouteKey(dst='172.16.254.0/24', table=254, ...),
     RouteKey(dst='192.168.122.0/24', table=254, ...),
     RouteKey(dst='fe80::/64', table=254, family=10, ...)]

But a routing table in IPDB allows several variants of the
route spec. The simplest case is to retrieve a route by
prefix, if there is only one match::

    # get route by prefix
    ipdb.routes['172.16.1.0/24']

    # get route by a special name
    ipdb.routes['default']

If there are more than one route that matches the spec, only
the first one will be retrieved. One should iterate all the
records and filter by a key to retrieve all matches::

    # only one route will be retrieved
    ipdb.routes['fe80::/64']

    # get all routes by this prefix
    [ x for x in ipdb.routes if x['dst'] == 'fe80::/64' ]

It is also possible to use dicts as specs::

    # get IPv4 default route
    ipdb.routes[{'dst': 'default', 'family': AF_INET}]

    # get IPv6 default route
    ipdb.routes[{'dst': 'default', 'family': AF_INET6}]

    # get route by priority
    ipdb.routes.table[100][{'dst': '10.0.0.0/24', 'priority': 10}]

While this notation returns one route, there is a method to get
all the routes matching the spec::

    # get all the routes from all the tables via some interface
    ipdb.routes.filter({'oif': idx})

    # get all IPv6 routes from some table
    ipdb.routes.table[tnum].filter({'family': AF_INET6})

Route metrics
~~~~~~~~~~~~~

A special object is dedicated to route metrics, one can
access it via `route.metrics` or `route['metrics']`::

    # these two statements are equal:
    with ipdb.routes['172.16.1.0/24'] as route:
        route['metrics']['mtu'] = 1400

    with ipdb.routes['172.16.1.0/24'] as route:
        route.metrics.mtu = 1400

Possible metrics are defined in `rtmsg.py:rtmsg.metrics`,
e.g. `RTAX_HOPLIMIT` means `hoplimit` metric etc.

Multipath routing
~~~~~~~~~~~~~~~~~

Multipath nexthops are managed via `route.add_nh()` and
`route.del_nh()` methods. They are available to review via
`route.multipath`, but one should not directly
add/remove/modify nexthops in `route.multipath`, as the
changes will not be committed correctly.

To create a multipath route::

    ipdb.routes.add({'dst': '172.16.232.0/24',
                     'multipath': [{'gateway': '172.16.231.2',
                                    'hops': 2},
                                   {'gateway': '172.16.231.3',
                                    'hops': 1},
                                   {'gateway': '172.16.231.4'}]}).commit()

To change a multipath route::

    with ipdb.routes['172.16.232.0/24'] as r:
        r.add_nh({'gateway': '172.16.231.5'})
        r.del_nh({'gateway': '172.16.231.4'})

Another possible way is to create a normal route and turn
it into multipath by `add_nh()`::

    # create a non-MP route with one gateway:
    (ipdb
     .routes
     .add({'dst': '172.16.232.0/24',
           'gateway': '172.16.231.2'})
     .commit())

    # turn it to become a MP route:
    (ipdb
     .routes['172.16.232.0/24']
     .add_nh({'gateway': '172.16.231.3'})
     .commit())

    # here the route will contain two NH records, with
    # gateways 172.16.231.2 and 172.16.231.3

    # remove one NH and turn the route to be a normal one
    (ipdb
     .routes['172.16.232.0/24']
     .del_nh({'gateway': '172.16.231.2'})
     .commit())

    # thereafter the traffic to 172.16.232.0/24 will go only
    # via 172.16.231.3

Differences from the iproute2 syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By historical reasons, `iproute2` uses names that differs
from what the kernel uses. E.g., `iproute2` uses `weight`
for multipath route hops instead of `hops`, where
`weight == (hops + 1)`. Thus, a route created with
`hops == 2` will be listed by `iproute2` as `weight 3`.

Another significant difference is `metrics`. The `pyroute2`
library uses the kernel naming scheme, where `metrics` means
mtu, rtt, window etc. The `iproute2` utility uses `metric`
(not `metrics`) as a name for the `priority` field.

In examples::

    # -------------------------------------------------------
    # iproute2 command:
    $ ip route add default \\
        nexthop via 172.16.0.1 weight 2 \\
        nexthop via 172.16.0.2 weight 9

    # pyroute2 code:
    (ipdb
     .routes
     .add({'dst': 'default',
           'multipath': [{'gateway': '172.16.0.1', 'hops': 1},
                         {'gateway': '172.16.0.2', 'hops': 8}])
     .commit())

    # -------------------------------------------------------
    # iproute2 command:
    $ ip route add default via 172.16.0.2 metric 200

    # pyroute2 code:
    (ipdb
     .routes
     .add({'dst': 'default',
           'gateway': '172.16.0.2',
           'priority': 200})
     .commit())

    # -------------------------------------------------------
    # iproute2 command:
    $ ip route add default via 172.16.0.2 mtu 1460

    # pyroute2 code:
    (ipdb
     .routes
     .add({'dst': 'default',
           'gateway': '172.16.0.2',
           'metrics': {'mtu': 1460}})
     .commit())

Multipath default routes
~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::
    As of the merge of kill_rtcache into the kernel, and it's
    release in ~3.6, weighted default routes no longer work
    in Linux.

Please refer to
https://github.com/svinota/pyroute2/issues/171#issuecomment-149297244
for details.

Rules management
----------------

IPDB provides a basic IP rules management system.

Create a rule
~~~~~~~~~~~~~

Syntax is almost the same as for routes::

    # rule spec
    spec = {'src': '172.16.1.0/24',
            'table': 200,
            'priority': 15000}

    ipdb.rules.add(spec).commit()

Get a rule
~~~~~~~~~~

The way IPDB handles IP rules is almost the same as routes,
but rule keys are more complicated -- the Linux kernel
doesn't use keys for rules, but instead iterates all the
records until the first one w/o any attribute mismatch.

The fields that the kernel uses to compare rules, IPDB uses
as the key fields (see `pyroute2/ipdb/rule.py:RuleKey`)

There are also more ways to find a record, as with routes::

    # 1. iterate all the records
    for record in ipdb.rules:
        match(record)

    # 2. an integer as the key matches the first
    #    rule with that priority
    ipdb.rules[32565]

    # 3. a dict as the key returns the first match
    #    for all the specified attrs
    ipdb.rules[{'dst': '10.0.0.0/24', 'table': 200}]

Priorities
~~~~~~~~~~

Thus, the rule priority is **not** a key, neither in the
kernel, nor in IPDB. One should **not** rely on priorities
as on keys, there may be several rules with the same
priority, and it often happens, e.g. on Android systems.

Persistence
~~~~~~~~~~~

There is no *change* operation for the rule records in the
kernel, so only *add/del* work. When IPDB changes a record,
it effectively deletes the old one and creates the new with
new parameters, but the object, referring the record, stays
the same. Also that means, that IPDB can not recognize the
situation, when someone else does the same. So if there is
another program changing records by *del/add* operations,
even another IPDB instance, referring objects in the IPDB
will be recreated.

Performance issues
------------------

In the case of bursts of Netlink broadcast messages, all
the activity of the pyroute2-based code in the async mode
becomes suppressed to leave more CPU resources to the
packet reader thread. So please be ready to cope with
delays in the case of Netlink broadcast storms. It means
also, that IPDB state will be synchronized with OS also
after some delay.

The class API
-------------
'''
import atexit
import logging
import sys
import threading
import traceback
import warnings
import weakref

try:
    import queue
except ImportError:
    import Queue as queue  # The module is called 'Queue' in Python2
# prepare to deprecate the module
# import warnings
from functools import partial
from pprint import pprint

from pyroute2 import config
from pyroute2.common import basestring, uuid32
from pyroute2.ipdb import interfaces, routes, rules
from pyroute2.ipdb.exceptions import ShutdownException
from pyroute2.ipdb.linkedset import IPaddrSet, SortedIPaddrSet
from pyroute2.ipdb.routes import BaseRoute
from pyroute2.ipdb.transactional import SYNC_TIMEOUT
from pyroute2.ipdb.utils import test_reachable_icmp
from pyroute2.iproute import IPRoute
from pyroute2.netlink.rtnl import RTM_GETLINK, RTMGRP_DEFAULTS
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg

log = logging.getLogger(__name__)


class Watchdog(object):
    def __init__(self, ipdb, action, kwarg):
        self.event = threading.Event()
        self.is_set = False
        self.ipdb = ipdb

        def cb(ipdb, msg, _action):
            if _action != action:
                return

            for key in kwarg:
                if (msg.get(key, None) != kwarg[key]) and (
                    msg.get_attr(msg.name2nla(key)) != kwarg[key]
                ):
                    return

            self.is_set = True
            self.event.set()

        self.cb = cb
        # register callback prior to other things
        self.uuid = self.ipdb.register_callback(self.cb)

    def wait(self, timeout=SYNC_TIMEOUT):
        ret = self.event.wait(timeout=timeout)
        self.cancel()
        return ret

    def cancel(self):
        self.ipdb.unregister_callback(self.uuid)


class _evq_context(object):
    '''
    Context manager class for the event queue used by the event loop
    '''

    def __init__(self, ipdb, qsize, block, timeout):
        self._ipdb = ipdb
        self._qsize = qsize
        self._block = block
        self._timeout = timeout

    def __enter__(self):
        # Context manager protocol
        self._ipdb._evq_lock.acquire()
        self._ipdb._evq = queue.Queue(maxsize=self._qsize)
        self._ipdb._evq_drop = 0
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Context manager protocol
        self._ipdb._evq = None
        self._ipdb._evq_drop = 0
        self._ipdb._evq_lock.release()

    def __iter__(self):
        # Iterator protocol
        if not self._ipdb._evq:
            raise RuntimeError(
                'eventqueue must be used ' 'as a context manager'
            )
        return self

    def next(self):
        # Iterator protocol -- Python 2.x compatibility
        return self.__next__()

    def __next__(self):
        # Iterator protocol -- Python 3.x
        msg = self._ipdb._evq.get(self._block, self._timeout)
        self._ipdb._evq.task_done()
        if isinstance(msg, Exception):
            raise msg
        return msg


class IPDB(object):
    '''
    The class that maintains information about network setup
    of the host. Monitoring netlink events allows it to react
    immediately. It uses no polling.
    '''

    def __init__(
        self,
        nl=None,
        mode='implicit',
        restart_on_error=None,
        nl_async=None,
        sndbuf=1048576,
        rcvbuf=1048576,
        nl_bind_groups=RTMGRP_DEFAULTS,
        ignore_rtables=None,
        callbacks=None,
        sort_addresses=False,
        plugins=None,
        deprecation_warning=True,
    ):
        msg = 'https://docs.pyroute2.org/ipdb_toc.html'
        log.warning('Deprecation warning ' + msg)
        if deprecation_warning:
            log.warning(
                'To remove this DeprecationWarning exception, '
                'start IPDB(deprecation_warning=False, ...)'
            )
            warnings.warn(
                'IPDB module is deprecated and will be removed in 0.7.1',
                DeprecationWarning,
            )
        plugins = plugins or ['interfaces', 'routes', 'rules']
        pmap = {'interfaces': interfaces, 'routes': routes, 'rules': rules}
        self.mode = mode
        self.txdrop = False
        self._stdout = sys.stdout
        self._ipaddr_set = SortedIPaddrSet if sort_addresses else IPaddrSet
        self._event_map = {}
        self._deferred = {}
        self._ensure = []
        self._loaded = set()
        self._mthread = None
        self._nl_own = nl is None
        self._nl_async = config.ipdb_nl_async if nl_async is None else True
        self.mnl = None
        self.nl = nl
        self._sndbuf = sndbuf
        self._rcvbuf = rcvbuf
        self.nl_bind_groups = nl_bind_groups
        self._plugins = [pmap[x] for x in plugins if x in pmap]
        if isinstance(ignore_rtables, int):
            self._ignore_rtables = [ignore_rtables]
        elif isinstance(ignore_rtables, (list, tuple, set)):
            self._ignore_rtables = ignore_rtables
        else:
            self._ignore_rtables = []
        self._stop = False
        # see also 'register_callback'
        self._post_callbacks = {}
        self._pre_callbacks = {}

        # local event queues
        # - callbacks event queue
        self._cbq = queue.Queue(maxsize=8192)
        self._cbq_drop = 0
        # - users event queue
        self._evq = None
        self._evq_lock = threading.Lock()
        self._evq_drop = 0

        # locks and events
        self.exclusive = threading.RLock()
        self._shutdown_lock = threading.Lock()

        # register callbacks
        #
        # examples::
        #   def cb1(ipdb, msg, event):
        #       print(event, msg)
        #   def cb2(...):
        #       ...
        #
        #   # default mode: post
        #   IPDB(callbacks=[cb1, cb2])
        #   # specify the mode explicitly
        #   IPDB(callbacks=[(cb1, 'pre'), (cb2, 'post')])
        #
        for cba in callbacks or []:
            if not isinstance(cba, (tuple, list, set)):
                cba = (cba,)
            self.register_callback(*cba)

        # load information
        self.restart_on_error = (
            restart_on_error if restart_on_error is not None else nl is None
        )

        # init the database
        self.initdb()

        # init the dir() cache
        self.__dir_cache__ = [
            i for i in self.__class__.__dict__.keys() if i[0] != '_'
        ]
        self.__dir_cache__.extend(list(self._deferred.keys()))

        def cleanup(ref):
            ipdb_obj = ref()
            if (ipdb_obj is not None) and (not ipdb_obj._stop):
                ipdb_obj.release()

        atexit.register(cleanup, weakref.ref(self))

    def __dir__(self):
        return self.__dir_cache__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def _flush_db(self):
        def flush(idx):
            for key in tuple(idx.keys()):
                try:
                    del idx[key]
                except KeyError:
                    pass

        idx_list = []
        if 'interfaces' in self._loaded:
            for key, dev in self.by_name.items():
                try:
                    # FIXME
                    self.interfaces._detach(key, dev['index'], dev.nlmsg)
                except KeyError:
                    pass
            idx_list.append(self.ipaddr)
            idx_list.append(self.neighbours)
        if 'routes' in self._loaded:
            idx_list.extend(
                [self.routes.tables[x] for x in self.routes.tables.keys()]
            )
        if 'rules' in self._loaded:
            idx_list.append(self.rules)
        for idx in idx_list:
            flush(idx)

    def initdb(self):
        # flush all the DB objects
        with self.exclusive:
            # explicitly cleanup object references
            for event in tuple(self._event_map):
                del self._event_map[event]

            self._flush_db()

            # if the command socket is not provided, create it
            if self._nl_own:
                if self.nl is not None:
                    self.nl.close()
                self.nl = IPRoute(
                    sndbuf=self._sndbuf, rcvbuf=self._rcvbuf, async_qsize=0
                )  # OBS: legacy design
            # setup monitoring socket
            if self.mnl is not None:
                self._flush_mnl()
                self.mnl.close()
            self.mnl = self.nl.clone()
            try:
                self.mnl.bind(
                    groups=self.nl_bind_groups, async_cache=self._nl_async
                )
            except:
                self.mnl.close()
                if self._nl_own is None:
                    self.nl.close()
                raise

            # explicitly cleanup references
            for key in tuple(self._deferred):
                del self._deferred[key]

            for module in self._plugins:
                if (module.groups & self.nl_bind_groups) != module.groups:
                    continue
                for plugin in module.spec:
                    self._deferred[plugin['name']] = module.spec
                    if plugin['name'] in self._loaded:
                        delattr(self, plugin['name'])
                        self._loaded.remove(plugin['name'])

            # start service threads
            for tspec in (
                ('_mthread', '_serve_main', 'IPDB main event loop'),
                ('_cthread', '_serve_cb', 'IPDB cb event loop'),
            ):
                tg = getattr(self, tspec[0], None)
                if not getattr(tg, 'is_alive', lambda: False)():
                    tx = threading.Thread(
                        name=tspec[2], target=getattr(self, tspec[1])
                    )
                    setattr(self, tspec[0], tx)
                    tx.daemon = True
                    tx.start()

    def __getattribute__(self, name):
        deferred = super(IPDB, self).__getattribute__('_deferred')
        if name in deferred:
            register = []
            spec = deferred[name]
            for plugin in spec:
                obj = plugin['class'](self, **plugin['kwarg'])
                setattr(self, plugin['name'], obj)
                register.append(obj)
                self._loaded.add(plugin['name'])
                del deferred[plugin['name']]
            for obj in register:
                if hasattr(obj, '_register'):
                    obj._register()
                if hasattr(obj, '_event_map'):
                    for event in obj._event_map:
                        if event not in self._event_map:
                            self._event_map[event] = []
                        self._event_map[event].append(obj._event_map[event])
        return super(IPDB, self).__getattribute__(name)

    def register_callback(self, callback, mode='post'):
        '''
        IPDB callbacks are routines executed on a RT netlink
        message arrival. There are two types of callbacks:
        "post" and "pre" callbacks.

        ...

        "Post" callbacks are executed after the message is
        processed by IPDB and all corresponding objects are
        created or deleted. Using ipdb reference in "post"
        callbacks you will access the most up-to-date state
        of the IP database.

        "Post" callbacks are executed asynchronously in
        separate threads. These threads can work as long
        as you want them to. Callback threads are joined
        occasionally, so for a short time there can exist
        stopped threads.

        ...

        "Pre" callbacks are synchronous routines, executed
        before the message gets processed by IPDB. It gives
        you the way to patch arriving messages, but also
        places a restriction: until the callback exits, the
        main event IPDB loop is blocked.

        Normally, only "post" callbacks are required. But in
        some specific cases "pre" also can be useful.

        ...

        The routine, `register_callback()`, takes two arguments:
            - callback function
            - mode (optional, default="post")

        The callback should be a routine, that accepts three
        arguments::

            cb(ipdb, msg, action)

        Arguments are:

            - **ipdb** is a reference to IPDB instance, that invokes
                the callback.
            - **msg** is a message arrived
            - **action** is just a msg['event'] field

        E.g., to work on a new interface, you should catch
        action == 'RTM_NEWLINK' and with the interface index
        (arrived in msg['index']) get it from IPDB::

            index = msg['index']
            interface = ipdb.interfaces[index]
        '''
        lock = threading.Lock()

        def safe(*argv, **kwarg):
            with lock:
                callback(*argv, **kwarg)

        safe.hook = callback
        safe.lock = lock
        safe.uuid = uuid32()

        if mode == 'post':
            self._post_callbacks[safe.uuid] = safe
        elif mode == 'pre':
            self._pre_callbacks[safe.uuid] = safe
        else:
            raise KeyError('Unknown callback mode')
        return safe.uuid

    def unregister_callback(self, cuid, mode='post'):
        if mode == 'post':
            cbchain = self._post_callbacks
        elif mode == 'pre':
            cbchain = self._pre_callbacks
        else:
            raise KeyError('Unknown callback mode')
        safe = cbchain[cuid]
        with safe.lock:
            ret = cbchain.pop(cuid)
        return ret

    def eventqueue(self, qsize=8192, block=True, timeout=None):
        '''
        Initializes event queue and returns event queue context manager.
        Once the context manager is initialized, events start to be collected,
        so it is possible to read initial state from the system without losing
        last moment changes, and once that is done, start processing events.

        Example::

            ipdb = IPDB()
            with ipdb.eventqueue() as evq:
                my_state = ipdb.<needed_attribute>...
                for msg in evq:
                    update_state_by_msg(my_state, msg)
        '''
        return _evq_context(self, qsize, block, timeout)

    def eventloop(self, qsize=8192, block=True, timeout=None):
        """
        Event generator for simple cases when there is no need for initial
        state setup. Initialize event queue and yield events as they happen.
        """
        with self.eventqueue(qsize=qsize, block=block, timeout=timeout) as evq:
            for msg in evq:
                yield msg

    def release(self):
        '''
        Shutdown IPDB instance and sync the state. Since
        IPDB is asyncronous, some operations continue in the
        background, e.g. callbacks. So, prior to exit the
        script, it is required to properly shutdown IPDB.

        The shutdown sequence is not forced in an interactive
        python session, since it is easier for users and there
        is enough time to sync the state. But for the scripts
        the `release()` call is required.
        '''
        with self._shutdown_lock:
            if self._stop:
                log.warning("shutdown in progress")
                return
            self._stop = True
            self._cbq.put(ShutdownException("shutdown"))

            if self._mthread is not None:
                self._flush_mnl()
                self._mthread.join()

            if self.mnl is not None:
                self.mnl.close()
                self.mnl = None

            if self._nl_own:
                self.nl.close()
                self.nl = None

            self._flush_db()

    def _flush_mnl(self):
        if self.mnl is not None:
            # terminate the main loop
            for t in range(3):
                try:
                    msg = ifinfmsg()
                    msg['index'] = 1
                    msg.reset()
                    self.mnl.put(msg, RTM_GETLINK)
                except Exception as e:
                    log.error("shutdown error: %s", e)
                    # Just give up.
                    # We can not handle this case

    def create(self, kind, ifname, reuse=False, **kwarg):
        return self.interfaces.add(kind, ifname, reuse, **kwarg)

    def ensure(self, cmd='add', reachable=None, condition=None):
        if cmd == 'reset':
            self._ensure = []
        elif cmd == 'run':
            for f in self._ensure:
                f()
        elif cmd == 'add':
            if isinstance(reachable, basestring):
                reachable = reachable.split(':')
                if len(reachable) == 1:
                    f = partial(test_reachable_icmp, reachable[0])
                else:
                    raise NotImplementedError()
                self._ensure.append(f)
            else:
                if sys.stdin.isatty():
                    pprint(self._ensure, stream=self._stdout)
        elif cmd == 'print':
            pprint(self._ensure, stream=self._stdout)
        elif cmd == 'get':
            return self._ensure
        else:
            raise NotImplementedError()

    def items(self):
        # TODO: add support for filters?

        # iterate interfaces
        for ifname in getattr(self, 'by_name', {}):
            yield (('interfaces', ifname), self.interfaces[ifname])

        # iterate routes
        for table in getattr(getattr(self, 'routes', None), 'tables', {}):
            for key, route in self.routes.tables[table].items():
                yield (('routes', table, key), route)

    def dump(self):
        ret = {}
        for key, obj in self.items():
            ptr = ret
            for step in key[:-1]:
                if step not in ptr:
                    ptr[step] = {}
                ptr = ptr[step]
            ptr[key[-1]] = obj
        return ret

    def load(self, config, ptr=None):
        if ptr is None:
            ptr = self

        for key in config:
            obj = getattr(ptr, key, None)
            if obj is not None:
                if hasattr(obj, 'load'):
                    obj.load(config[key])
                else:
                    self.load(config[key], ptr=obj)
            elif hasattr(ptr, 'add'):
                ptr.add(**config[key])

        return self

    def review(self):
        ret = {}
        for key, obj in self.items():
            ptr = ret
            try:
                rev = obj.review()
            except TypeError:
                continue

            for step in key[:-1]:
                if step not in ptr:
                    ptr[step] = {}
                ptr = ptr[step]
            ptr[key[-1]] = rev

        if not ret:
            raise TypeError('no transaction started')
        return ret

    def drop(self):
        ok = False
        for key, obj in self.items():
            try:
                obj.drop()
            except TypeError:
                continue
            ok = True
        if not ok:
            raise TypeError('no transaction started')

    def commit(self, transactions=None, phase=1):
        # what to commit: either from transactions argument, or from
        # started transactions on existing objects
        if transactions is None:
            # collect interface transactions
            txlist = [
                (x, x.current_tx)
                for x in getattr(self, 'by_name', {}).values()
                if x.local_tx.values()
            ]
            # collect route transactions
            for table in getattr(
                getattr(self, 'routes', None), 'tables', {}
            ).keys():
                txlist.extend(
                    [
                        (x, x.current_tx)
                        for x in self.routes.tables[table]
                        if x.local_tx.values()
                    ]
                )
            transactions = txlist

        snapshots = []
        removed = []

        tx_ipdb_prio = []
        tx_main = []
        tx_prio1 = []
        tx_prio2 = []
        tx_prio3 = []
        for target, tx in transactions:
            # 8<------------------------------
            # first -- explicit priorities
            if tx['ipdb_priority']:
                tx_ipdb_prio.append((target, tx))
                continue
            # 8<------------------------------
            # routes
            if isinstance(target, BaseRoute):
                tx_prio3.append((target, tx))
                continue
            # 8<------------------------------
            # intefaces
            kind = target.get('kind', None)
            if kind in (
                'vlan',
                'vxlan',
                'gre',
                'tuntap',
                'vti',
                'vti6',
                'vrf',
                'xfrm',
            ):
                tx_prio1.append((target, tx))
            elif kind in ('bridge', 'bond'):
                tx_prio2.append((target, tx))
            else:
                tx_main.append((target, tx))
            # 8<------------------------------

        # explicitly sorted transactions
        tx_ipdb_prio = sorted(
            tx_ipdb_prio, key=lambda x: x[1]['ipdb_priority'], reverse=True
        )

        # FIXME: this should be documented
        #
        # The final transactions order:
        # 1. any txs with ipdb_priority (sorted by that field)
        #
        # Then come default priorities (no ipdb_priority specified):
        # 2. all the rest
        # 3. vlan, vxlan, gre, tuntap, vti, vrf
        # 4. bridge, bond
        # 5. routes
        transactions = tx_ipdb_prio + tx_main + tx_prio1 + tx_prio2 + tx_prio3

        try:
            for target, tx in transactions:
                if target['ipdb_scope'] == 'detached':
                    continue
                if tx['ipdb_scope'] == 'remove':
                    tx['ipdb_scope'] = 'shadow'
                    removed.append((target, tx))
                if phase == 1:
                    s = (target, target.pick(detached=True))
                    snapshots.append(s)
                # apply the changes, but NO rollback -- only phase 1
                target.commit(
                    transaction=tx, commit_phase=phase, commit_mask=phase
                )
                # if the commit above fails, the next code
                # branch will run rollbacks
        except Exception:
            if phase == 1:
                # run rollbacks for ALL the collected transactions,
                # even successful ones
                self.fallen = transactions
                txs = filter(
                    lambda x: not (
                        'create' == x[0]['ipdb_scope'] == x[1]['ipdb_scope']
                    ),
                    snapshots,
                )
                self.commit(transactions=txs, phase=2)
            raise
        else:
            if phase == 1:
                for target, tx in removed:
                    target['ipdb_scope'] = 'detached'
                    target.detach()
        finally:
            if phase == 1:
                for target, tx in transactions:
                    target.drop(tx.uid)

        return self

    def watchdog(self, wdops='RTM_NEWLINK', **kwarg):
        return Watchdog(self, wdops, kwarg)

    def _serve_cb(self):
        ###
        # Callbacks thread working on a dedicated event queue.
        ###

        while not self._stop:
            msg = self._cbq.get()
            self._cbq.task_done()
            if isinstance(msg, ShutdownException):
                return
            elif isinstance(msg, Exception):
                raise msg
            for cb in tuple(self._post_callbacks.values()):
                try:
                    cb(self, msg, msg['event'])
                except:
                    pass

    def _serve_main(self):
        ###
        # Main monitoring cycle. It gets messages from the
        # default iproute queue and updates objects in the
        # database.
        ###

        while not self._stop:
            try:
                messages = self.mnl.get()
                ##
                # Check it again
                #
                # NOTE: one should not run callbacks or
                # anything like that after setting the
                # _stop flag, since IPDB is not valid
                # anymore
                if self._stop:
                    break
            except Exception as e:
                with self.exclusive:
                    if self._evq:
                        self._evq.put(e)
                        return
                if self.restart_on_error:
                    log.error(
                        'Restarting IPDB instance after ' 'error:\n%s',
                        traceback.format_exc(),
                    )
                    try:
                        self.initdb()
                    except:
                        log.error(
                            'Error restarting DB:\n%s', traceback.format_exc()
                        )
                        return
                    continue
                else:
                    log.error('Emergency shutdown, cleanup manually')
                    raise RuntimeError('Emergency shutdown')

            for msg in messages:
                # Run pre-callbacks
                # NOTE: pre-callbacks are synchronous
                for cuid, cb in tuple(self._pre_callbacks.items()):
                    try:
                        cb(self, msg, msg['event'])
                    except:
                        pass

                with self.exclusive:
                    event = msg.get('event', None)
                    if event in self._event_map:
                        for func in self._event_map[event]:
                            func(msg)

                    # Post-callbacks
                    try:
                        self._cbq.put_nowait(msg)
                        if self._cbq_drop:
                            log.warning('dropped %d events', self._cbq_drop)
                            self._cbq_drop = 0
                    except queue.Full:
                        self._cbq_drop += 1
                    except Exception:
                        log.error('Emergency shutdown, cleanup manually')
                        raise RuntimeError('Emergency shutdown')

                    #
                    # Why not to put these two pieces of the code
                    # it in a routine?
                    #
                    # TODO: run performance tests with routines

                    # Users event queue
                    if self._evq:
                        try:
                            self._evq.put_nowait(msg)
                            if self._evq_drop:
                                log.warning(
                                    "dropped %d events", self._evq_drop
                                )
                                self._evq_drop = 0
                        except queue.Full:
                            self._evq_drop += 1
                        except Exception:
                            log.error('Emergency shutdown, cleanup manually')
                            raise RuntimeError('Emergency shutdown')
