'''
.. testsetup::

    from pyroute2 import NDB
    ndb = NDB(sources=[{'target': 'localhost', 'kind': 'IPMock'}])

.. testsetup:: netns

    from types import MethodType

    from pyroute2 import NDB

    ndb = NDB(sources=[{'target': 'localhost', 'kind': 'IPMock'}])

    def add_mock_netns(self, netns):
        return self.add_orig(target=netns, kind='IPMock', preset='netns')

    ndb.sources.add_orig = ndb.sources.add
    ndb.sources.add = MethodType(add_mock_netns, ndb.sources)

.. testcleanup:: *

    for key, value in tuple(globals().items()):
        if key.startswith('ndb') and hasattr(value, 'close'):
            value.close()

NDB is a high level network management module. IT allows to manage interfaces,
routes, addresses etc. of connected systems, containers and network
namespaces.

In a nutshell, NDB collects and aggregates netlink events in an SQL database,
provides Python objects to reflect the system state, and applies changes back
to the system. The database expects updates only from the sources, no manual
SQL updates are expected normally.

.. aafig::
    :scale: 80
    :textual:

        +----------------------------------------------------------------+
      +----------------------------------------------------------------+ |
    +----------------------------------------------------------------+ | |
    |                                                                | | |
    |                              kernel                            | |-+
    |                                                                |-+
    +----------------------------------------------------------------+
            |                      | ^                     | ^
            | `netlink events`     | |                     | |
            | `inotify events`     | |                     | |
            | `...`                | |                     | |
            v                      v |                     v |
     +--------------+        +--------------+        +--------------+
     |     source   |        |     source   |        |     source   |<--\\
     +--------------+        +--------------+        +--------------+   |
            |                       |                       |           |
            |                       |                       |           |
            \\-----------------------+-----------------------/           |
                                    |                                   |
              parsed netlink events | `NDB._event_queue`                |
                                    |                                   |
                                    v                                   |
                        +------------------------+                      |
                        | `NDB.__dbm__()` thread |                      |
                        +------------------------+                      |
                                    |                                   |
                                    v                                   |
                     +-----------------------------+                    |
                     | `NDB.schema.load_netlink()` |                    |
                     | `NDB.objects.*.load*()`     |                    |
                     +-----------------------------+                    |
                                    |                                   |
                                    v                                   |
                         +----------------------+                       |
                         |  SQL database        |                       |
                         |     `SQLite`         |                       |
                         |     `PostgreSQL`     |                       |
                         +----------------------+                       |
                                    |                                   |
                                    |                                   |
                                    V                                   |
                              +---------------+                         |
                            +---------------+ |                         |
                          +---------------+ | |  `RTNL_Object.apply()`  |
                          | NDB object:   | | |-------------------------/
                          |  `interface`  | | |
                          |  `address`    | | |
                          |  `route`      | |-+
                          |  `...`        |-+
                          +---------------+

.. container:: aafig-caption

    object names on the diagram are clickable

The goal of NDB is to provide an easy access to RTNL info and entities via
Python objects, like `pyroute2.ndb.objects.interface` (see also:
:ref:`ndbinterfaces`), `pyroute2.ndb.objects.route` (see also:
:ref:`ndbroutes`) etc. These objects do not
only reflect the system state for the time of their instantiation, but
continuously monitor the system for relevant updates. The monitoring is
done via netlink notifications, thus no polling. Also the objects allow
to apply changes back to the system and rollback the changes.

On the other hand it's too expensive to create Python objects for all the
available RTNL entities, e.g. when there are hundreds of interfaces and
thousands of routes. Thus NDB creates objects only upon request, when
the user calls `.create()` to create new objects or runs
`ndb.<view>[selector]` (e.g. `ndb.interfaces['eth0']`) to access an
existing object.

To list existing RTNL entities NDB uses objects of the class `RecordSet`
that `yield` individual `Record` objects for every entity (see also:
:ref:`ndbreports`). An object of the `Record` class is immutable, doesn't
monitor any updates, doesn't contain any links to other objects and essentially
behaves like a simple named tuple.

.. aafig::
    :scale: 80
    :textual:


      +---------------------+
      |                     |
      |                     |
      | `NDB() instance`    |
      |                     |
      |                     |
      +---------------------+
                 |
                 |
        +-------------------+
      +-------------------+ |
    +-------------------+ | |-----------+--------------------------+
    |                   | | |           |                          |
    |                   | | |           |                          |
    | `View()`          | | |           |                          |
    |                   | |-+           |                          |
    |                   |-+             |                          |
    +-------------------+               |                          |
                               +------------------+       +------------------+
                               |                  |       |                  |
                               |                  |       |                  |
                               | `.dump()`        |       | `.create()`      |
                               | `.summary()`     |       | `.__getitem__()` |
                               |                  |       |                  |
                               |                  |       |                  |
                               +------------------+       +------------------+
                                        |                           |
                                        |                           |
                                        v                           v
                              +-------------------+        +------------------+
                              |                   |      +------------------+ |
                              |                   |    +------------------+ | |
                              | `RecordSet()`     |    | `Interface()`    | | |
                              |                   |    | `Address()`      | | |
                              |                   |    | `Route()`        | | |
                              +-------------------+    | `Neighbour()`    | | |
                                        |              | `Rule()`         | |-+
                                        |              |  ...             |-+
                                        v              +------------------+
                                +-------------------+
                              +-------------------+ |
                            +-------------------+ | |
                            | `filter()`        | | |
                            | `select()`        | | |
                            | `transform()`     | | |
                            | `join()`          | |-+
                            |  ...              |-+
                            +-------------------+
                                        |
                                        v
                                +-------------------+
                              +-------------------+ |
                            +-------------------+ | |
                            |                   | | |
                            |                   | | |
                            | `Record()`        | | |
                            |                   | |-+
                            |                   |-+
                            +-------------------+

.. container:: aafig-caption

    object names on the diagram are clickable

Here are some simple NDB usage examples. More info see in the reference
documentation below.

Print all the interface names on the system, assume we have an NDB
instance `ndb`:

.. testcode::

    for interface in ndb.interfaces.dump():
        print(interface.ifname)

.. testoutput::

    lo
    eth0

Print the routing information in the CSV format:

.. testcode::

    for record in ndb.routes.summary().format('csv'):
        print(record)

.. testoutput::

    'target','tflags','table','ifname','dst','dst_len','gateway'
    'localhost',0,254,'eth0','',0,'192.168.122.1'
    'localhost',0,254,'eth0','192.168.122.0',24,
    'localhost',0,255,'lo','127.0.0.0',8,
    'localhost',0,255,'lo','127.0.0.1',32,
    'localhost',0,255,'lo','127.255.255.255',32,
    'localhost',0,255,'eth0','192.168.122.28',32,
    'localhost',0,255,'eth0','192.168.122.255',32,

.. note:: More on report filtering and formatting: :ref:`ndbreports`

Print IP addresses of interfaces in several network namespaces as:

.. testcode:: netns

    nslist = ['netns01',
              'netns02',
              'netns03']

    for nsname in nslist:
        ndb.sources.add(netns=nsname)

    report = ndb.addresses.summary()
    report.select_records(target=lambda x: x.startswith('netns'))
    report.select_fields('address', 'ifname', 'target')
    for line in report.format('json'):
        print(line)

.. testoutput:: netns

    [
        {
            "address": "127.0.0.1",
            "ifname": "lo",
            "target": "netns01"
        },
        {
            "address": "127.0.0.1",
            "ifname": "lo",
            "target": "netns02"
        },
        {
            "address": "127.0.0.1",
            "ifname": "lo",
            "target": "netns03"
        }
    ]

Add an IP address on an interface:

.. testcode::

    with ndb.interfaces['eth0'] as eth0:
        eth0.add_ip('10.0.0.1/24')
    # ---> <---  NDB waits until the address setup

Change an interface property:

.. testcode::

    with ndb.interfaces['eth0'] as eth0:
        eth0.set(
            state='up',
            address='00:11:22:33:44:55',
        )
    # ---> <---  NDB waits here for the changes to be applied
    #            the commit() is called automatically by the
    #            context manager's __exit__()

'''

import atexit
import ctypes
import ctypes.util
import logging
import logging.handlers
import sys
import threading

from pyroute2 import config
from pyroute2.common import basestring

##
# NDB stuff
from .auth_manager import AuthManager
from .events import ShutdownException
from .messages import cmsg
from .schema import DBProvider
from .task_manager import TaskManager
from .transaction import Transaction
from .view import SourcesView, View

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

try:
    import queue
except ImportError:
    import Queue as queue

log = logging.getLogger(__name__)


NDB_VIEWS_SPECS = (
    ('interfaces', 'interfaces'),
    ('addresses', 'addresses'),
    ('routes', 'routes'),
    ('neighbours', 'neighbours'),
    ('af_bridge_fdb', 'fdb'),
    ('rules', 'rules'),
    ('netns', 'netns'),
    ('af_bridge_vlans', 'vlans'),
)


class Log:
    def __init__(self, log_id=None):
        self.logger = None
        self.state = False
        self.log_id = log_id or id(self)
        self.logger = logging.getLogger('pyroute2.ndb.%s' % self.log_id)
        self.main = self.channel('main')

    def __call__(self, target=None, level=logging.INFO):
        if target is None:
            return self.logger is not None

        if self.logger is not None:
            for handler in tuple(self.logger.handlers):
                self.logger.removeHandler(handler)

        if target in ('off', False):
            if self.state:
                self.logger.setLevel(0)
                self.logger.addHandler(logging.NullHandler())
            return

        if target in ('on', 'stderr'):
            handler = logging.StreamHandler()
        elif target == 'debug':
            handler = logging.StreamHandler()
            level = logging.DEBUG
        elif isinstance(target, basestring):
            url = urlparse(target)
            if not url.scheme and url.path:
                handler = logging.FileHandler(url.path)
            elif url.scheme == 'syslog':
                handler = logging.handlers.SysLogHandler(
                    address=url.netloc.split(':')
                )
            else:
                raise ValueError('logging scheme not supported')
        else:
            handler = target

        # set formatting only for new created logging handlers
        if handler is not target:
            fmt = '%(asctime)s %(levelname)8s %(name)s: %(message)s'
            formatter = logging.Formatter(fmt)
            handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.setLevel(level)

    @property
    def on(self):
        self.__call__(target='on')

    @property
    def off(self):
        self.__call__(target='off')

    def close(self):
        manager = self.logger.manager
        name = self.logger.name
        # the loggerDict can be huge, so don't
        # cache all the keys -- cache only the
        # needed ones
        purge_list = []
        for logger in manager.loggerDict.keys():
            if logger.startswith(name):
                purge_list.append(logger)
        # now shoot them one by one
        for logger in purge_list:
            del manager.loggerDict[logger]
        # don't force GC, leave it to the user
        del manager
        del name
        del purge_list

    def channel(self, name):
        return logging.getLogger('pyroute2.ndb.%s.%s' % (self.log_id, name))

    def debug(self, *argv, **kwarg):
        return self.main.debug(*argv, **kwarg)

    def info(self, *argv, **kwarg):
        return self.main.info(*argv, **kwarg)

    def warning(self, *argv, **kwarg):
        return self.main.warning(*argv, **kwarg)

    def error(self, *argv, **kwarg):
        return self.main.error(*argv, **kwarg)

    def critical(self, *argv, **kwarg):
        return self.main.critical(*argv, **kwarg)


class DeadEnd:
    def put(self, *argv, **kwarg):
        raise ShutdownException('shutdown in progress')


class EventQueue:
    def __init__(self, *argv, **kwarg):
        self._bypass = self._queue = queue.Queue(*argv, **kwarg)

    def put(self, msg, source=None):
        return self._queue.put((source, msg))

    def shutdown(self):
        self._queue = DeadEnd()

    def bypass(self, msg, source=None):
        return self._bypass.put((source, msg))

    def get(self, *argv, **kwarg):
        return self._bypass.get(*argv, **kwarg)

    def qsize(self):
        return self._bypass.qsize()


class AuthProxy:
    def __init__(self, ndb, auth_managers):
        self._ndb = ndb
        self._auth_managers = auth_managers

        for vtable, vname in NDB_VIEWS_SPECS:
            view = View(self._ndb, vtable, auth_managers=self._auth_managers)
            setattr(self, vname, view)


class NDB:
    @property
    def nsmanager(self):
        return '%s/nsmanager' % self.localhost

    def __init__(
        self,
        sources=None,
        localhost='localhost',
        db_provider='sqlite3',
        db_spec=':memory:',
        db_cleanup=True,
        rtnl_debug=False,
        log=False,
        auto_netns=False,
        libc=None,
    ):
        if db_provider == 'postgres':
            db_provider = 'psycopg2'

        self.localhost = localhost
        self.schema = None
        self.libc = libc or ctypes.CDLL(
            ctypes.util.find_library('c'), use_errno=True
        )
        self.log = Log(log_id=id(self))
        self._db = None
        self._dbm_thread = None
        self._dbm_ready = threading.Event()
        self._dbm_shutdown = threading.Event()
        self._global_lock = threading.Lock()
        self._event_queue = EventQueue(maxsize=100)
        self.messenger = None
        #
        if log:
            if isinstance(log, basestring):
                self.log(log)
            elif isinstance(log, (tuple, list)):
                self.log(*log)
            elif isinstance(log, dict):
                self.log(**log)
            else:
                raise TypeError('wrong log spec format')
        #
        # fix sources prime
        if sources is None:
            if config.mock_iproute:
                sources = [{'target': 'localhost', 'kind': 'IPMock'}]
            else:
                sources = [
                    {
                        'target': self.localhost,
                        'kind': 'local',
                        'nlm_generator': 1,
                    }
                ]
                if sys.platform.startswith('linux'):
                    sources.append(
                        {'target': self.nsmanager, 'kind': 'nsmanager'}
                    )
        elif not isinstance(sources, (list, tuple)):
            raise ValueError('sources format not supported')

        for spec in sources:
            if 'target' not in spec:
                spec['target'] = self.localhost
                break

        am = AuthManager(
            {'obj:list': True, 'obj:read': True, 'obj:modify': True},
            self.log.channel('auth'),
        )
        self.sources = SourcesView(self, auth_managers=[am])
        self._call_registry = {}
        self._nl = sources
        atexit.register(self.close)
        self._dbm_ready.clear()
        self._dbm_error = None
        self.config = {
            'provider': str(DBProvider(db_provider)),
            'spec': db_spec,
            'rtnl_debug': rtnl_debug,
            'db_cleanup': db_cleanup,
            'auto_netns': auto_netns,
            'recordset_pipe': 'false',
        }
        self.task_manager = TaskManager(self)
        self._dbm_thread = threading.Thread(
            target=self.task_manager.run, name='NDB main loop'
        )
        self._dbm_thread.daemon = True
        self._dbm_thread.start()
        self._dbm_ready.wait()
        if self._dbm_error is not None:
            raise self._dbm_error
        for vtable, vname in NDB_VIEWS_SPECS:
            view = View(self, vtable, auth_managers=[am])
            setattr(self, vname, view)
        # self.query = Query(self.schema)

    def _get_view(self, table, chain=None, auth_managers=None):
        return View(self, table, chain, auth_managers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def begin(self):
        return Transaction(self.log.channel('transaction'))

    def readonly(self):
        return self.auth_proxy(
            AuthManager(
                {'obj:list': True, 'obj:read': True, 'obj:modify': False},
                self.log.channel('auth'),
            )
        )

    def auth_proxy(self, auth_manager):
        return AuthProxy(self, [auth_manager])

    def close(self):
        with self._global_lock:
            if self._dbm_shutdown.is_set():
                return
            else:
                self._dbm_shutdown.set()
            if hasattr(atexit, 'unregister'):
                atexit.unregister(self.close)
            else:
                try:
                    atexit._exithandlers.remove((self.close, (), {}))
                except ValueError:
                    pass
            # shutdown the _dbm_thread
            self._event_queue.shutdown()
            self._event_queue.bypass((cmsg(None, ShutdownException()),))
            self._dbm_thread.join()
            # shutdown the logger -- free the resources
            self.log.close()

    def backup(self, spec):
        self.task_manager.db_backup(spec)

    def reload(self, kinds=None):
        for source in self.sources.values():
            if kinds is not None and source.kind in kinds:
                source.restart()
