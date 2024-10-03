'''

Local RTNL
----------

Local RTNL source is a simple `IPRoute` instance. By default NDB
starts with one local RTNL source names `localhost`::

    >>> ndb = NDB()
    >>> ndb.sources.summary().format("json")
    [
        {
            "name": "localhost",
            "spec": "{'target': 'localhost', 'nlm_generator': 1}",
            "state": "running"
        },
        {
            "name": "localhost/nsmanager",
            "spec": "{'target': 'localhost/nsmanager'}",
            "state": "running"
        }
    ]
    >>> ndb.sources['localhost']
    [running] <IPRoute {'target: 'localhost', 'nlm_generator': 1}>

The `localhost` RTNL source starts an additional async cache thread.
The `nlm_generator` option means that instead of collections the
`IPRoute` object returns generators, so `IPRoute` responses will not
consume memory regardless of the RTNL objects number::

    >>> ndb.sources['localhost'].nl.link('dump')
    <generator object RTNL_API.filter_messages at 0x7f61a99a34a0>

See also: :ref:`iproute`

Network namespaces
------------------

There are two ways to connect additional sources to an NDB instance.
One is to specify sources when creating an NDB object::

    ndb = NDB(sources=[{'target': 'localhost'}, {'netns': 'test01'}])

Another way is to call `ndb.sources.add()` method::

    ndb.sources.add(netns='test01')

This syntax: `{target': 'localhost'}` and `{'netns': 'test01'}` is the
short form. The full form would be::

    {'target': 'localhost', # the label for the DB
     'kind': 'local',       # use IPRoute class to start the source
     'nlm_generator': 1}    #

    {'target': 'test01',    # the label
     'kind': 'netns',       # use NetNS class
     'netns': 'test01'}     #

See also: :ref:`netns`

Remote systems
--------------

It is possible also to connect to remote systems using SSH. In order to
use this kind of sources it is required to install the
`mitogen <https://github.com/dw/mitogen>`_ module. The `remote` kind
of sources uses the `RemoteIPRoute` class. The short form::

    ndb.sources.add(hostname='worker1.example.com')


In some more extended form::

    ndb.sources.add(**{'target': 'worker1.example.com',
                       'kind': 'remote',
                       'hostname': 'worker1.example.com',
                       'username': 'jenkins',
                       'check_host_keys': False})

See also: :ref:`remote`
'''

import errno
import importlib
import queue
import socket
import struct
import sys
import threading
import time
import uuid

from pyroute2.common import basestring
from pyroute2.iproute import IPRoute
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.nlsocket import NetlinkSocketBase
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.remote import RemoteIPRoute

from .events import ShutdownException, State
from .messages import cmsg_event, cmsg_failed, cmsg_sstart

if sys.platform.startswith('linux'):
    from pyroute2 import netns
    from pyroute2.netns.manager import NetNSManager
    from pyroute2.nslink.nslink import NetNS
else:
    NetNS = None
    NetNSManager = None

SOURCE_FAIL_PAUSE = 1
SOURCE_MAX_ERRORS = 3


class SourceProxy(object):
    def __init__(self, ndb, target):
        self.ndb = ndb
        self.events = queue.Queue()
        self.target = target

    def api(self, name, *argv, **kwarg):
        call_id = str(uuid.uuid4().hex)
        self.ndb._call_registry[call_id] = event = threading.Event()
        event.clear()
        (
            self.ndb.messenger.emit(
                {
                    'type': 'api',
                    'target': self.target,
                    'call_id': call_id,
                    'name': name,
                    'argv': argv,
                    'kwarg': kwarg,
                }
            )
        )

        event.wait()
        response = self.ndb._call_registry.pop(call_id)
        if 'return' in response:
            return response['return']
        elif 'exception' in response:
            raise response['exception']


class Source(dict):
    '''
    The RNTL source. The source that is used to init the object
    must comply to IPRoute API, must support the async_cache. If
    the source starts additional threads, they must be joined
    in the source.close()
    '''

    table_alias = 'src'
    dump_header = None
    summary_header = None
    view = None
    table = 'sources'
    vmap = {
        'local': IPRoute,
        'netns': NetNS,
        'remote': RemoteIPRoute,
        'nsmanager': NetNSManager,
    }

    def __init__(self, ndb, **spec):
        self.th = None
        self.nl = None
        self.ndb = ndb
        self.evq = self.ndb._event_queue
        # the target id -- just in case
        self.target = spec['target']
        self.kind = spec.pop('kind', 'local')
        self.max_errors = spec.pop('max_errors', SOURCE_MAX_ERRORS)
        self.event = spec.pop('event')
        # RTNL API
        self.nl_prime = self.get_prime(self.kind)
        self.nl_kwarg = spec
        #
        if self.ndb.messenger is not None:
            self.ndb.messenger.targets.add(self.target)
        #
        self.errors_counter = 0
        self.shutdown = threading.Event()
        self.started = threading.Event()
        self.lock = threading.RLock()
        self.shutdown_lock = threading.RLock()
        self.started.clear()
        self.log = ndb.log.channel('sources.%s' % self.target)
        self.state = State(log=self.log, wait_list=['running'])
        self.state.set('init')
        self.ndb.task_manager.db_add_nl_source(self.target, self.kind, spec)
        self.load_sql()

    @classmethod
    def _count(cls, view):
        return view.ndb.task_manager.db_fetchone(
            "SELECT count(*) FROM %s" % view.table
        )

    @property
    def must_restart(self):
        if self.max_errors < 0 or self.errors_counter <= self.max_errors:
            return True
        return False

    @property
    def bind_arguments(self):
        return dict(
            filter(
                lambda x: x[1] is not None,
                (
                    ('async_cache', True),
                    ('clone_socket', True),
                    ('groups', self.nl_kwarg.get('groups')),
                ),
            )
        )

    def set_ready(self):
        try:
            if self.event is not None:
                self.evq.put(
                    (cmsg_event(self.target, self.event),), source=self.target
                )
            else:
                self.evq.put((cmsg_sstart(self.target),), source=self.target)
        except ShutdownException:
            self.state.set('stop')
            return False
        return True

    @classmethod
    def defaults(cls, spec):
        ret = dict(spec)
        defaults = {}
        if 'hostname' in spec:
            defaults['kind'] = 'remote'
            defaults['protocol'] = 'ssh'
            defaults['target'] = spec['hostname']
        if 'netns' in spec:
            defaults['kind'] = 'netns'
            defaults['target'] = spec['netns']
            ret['netns'] = netns._get_netnspath(spec['netns'])
        for key in defaults:
            if key not in ret:
                ret[key] = defaults[key]
        return ret

    def __repr__(self):
        if isinstance(self.nl_prime, NetlinkSocketBase):
            name = self.nl_prime.__class__.__name__
        elif isinstance(self.nl_prime, type):
            name = self.nl_prime.__name__

        return '[%s] <%s %s>' % (self.state.get(), name, self.nl_kwarg)

    @classmethod
    def nla2name(cls, name):
        return name

    @classmethod
    def name2nla(cls, name):
        return name

    @classmethod
    def summary(cls, view):
        yield ('state', 'name', 'spec')
        for key in view.keys():
            yield (view[key].state.get(), key, '%s' % (view[key].nl_kwarg,))

    @classmethod
    def dump(cls, view):
        return cls.summary(view)

    @classmethod
    def compare_record(self, left, right):
        # specific compare
        if isinstance(right, basestring):
            return right == left['name']

    def get_prime(self, name):
        return self.vmap.get(self.kind, None) or getattr(
            importlib.import_module('pyroute2'), self.kind
        )

    def api(self, name, *argv, **kwarg):
        for _ in range(100):  # FIXME make a constant
            with self.lock:
                try:
                    self.log.debug(f'source api run {name} {argv} {kwarg}')
                    return getattr(self.nl, name)(*argv, **kwarg)
                except (
                    NetlinkError,
                    AttributeError,
                    ValueError,
                    KeyError,
                    TypeError,
                    socket.error,
                    struct.error,
                ):
                    raise
                except Exception as e:
                    # probably the source is restarting
                    self.errors_counter += 1
                    self.log.debug(f'source api error: <{e}>')
                    time.sleep(1)
        raise RuntimeError('api call failed')

    def fake_zero_if(self):
        url = 'https://github.com/svinota/pyroute2/issues/737'
        zero_if = ifinfmsg()
        zero_if['index'] = 0
        zero_if['state'] = 'up'
        zero_if['flags'] = 1
        zero_if['header']['flags'] = 2
        zero_if['header']['type'] = 16
        zero_if['header']['target'] = self.target
        zero_if['event'] = 'RTM_NEWLINK'
        zero_if['attrs'] = [
            ('IFLA_IFNAME', url),
            ('IFLA_ADDRESS', '00:00:00:00:00:00'),
        ]
        zero_if.encode()
        self.evq.put([zero_if], source=self.target)

    def receiver(self):
        #
        # The source thread routine -- get events from the
        # channel and forward them into the common event queue
        #
        # The routine exists on an event with error code == 104
        #
        while self.state.get() != 'stop':
            if self.shutdown.is_set():
                break

            with self.lock:
                if self.nl is not None:
                    try:
                        self.nl.close(code=0)
                    except Exception as e:
                        self.log.warning('source restart: %s' % e)
                try:
                    self.state.set('connecting')
                    if isinstance(self.nl_prime, type):
                        spec = {}
                        spec.update(self.nl_kwarg)
                        if self.kind in ('nsmanager',):
                            spec['libc'] = self.ndb.libc
                        self.nl = self.nl_prime(**spec)
                    else:
                        raise TypeError('source channel not supported')
                    self.state.set('loading')
                    #
                    self.nl.bind(**self.bind_arguments)
                    #
                    # Initial load -- enqueue the data
                    #
                    try:
                        self.ndb.task_manager.db_flush(self.target)
                        if self.kind in ('local', 'netns', 'remote'):
                            self.fake_zero_if()
                        self.evq.put(self.nl.dump(), source=self.target)
                    finally:
                        pass
                    self.errors_counter = 0
                except Exception as e:
                    self.errors_counter += 1
                    self.started.set()
                    self.state.set(f'failed, counter {self.errors_counter}')
                    self.log.error(f'source error: {type(e)} {e}')
                    try:
                        self.evq.put(
                            (cmsg_failed(self.target),), source=self.target
                        )
                    except ShutdownException:
                        self.state.set('stop')
                        break
                    if self.must_restart:
                        self.log.debug('sleeping before restart')
                        self.state.set('restart')
                        self.shutdown.wait(SOURCE_FAIL_PAUSE)
                        if self.shutdown.is_set():
                            self.log.debug('source shutdown')
                            self.state.set('stop')
                            break
                    else:
                        return self.set_ready()
                    continue

            with self.lock:
                if self.state.get() == 'loading':
                    if not self.set_ready():
                        break
                    self.started.set()
                    self.shutdown.clear()
                    self.state.set('running')

            while self.state.get() not in ('stop', 'restart'):
                try:
                    msg = tuple(self.nl.get())
                except Exception as e:
                    self.errors_counter += 1
                    self.log.error('source error: %s %s' % (type(e), e))
                    msg = None
                    if self.must_restart:
                        self.state.set('restart')
                    else:
                        self.state.set('stop')
                    break

                code = 0
                if msg and msg[0]['header']['error']:
                    code = msg[0]['header']['error'].code

                if msg is None or code == errno.ECONNRESET:
                    self.state.set('stop')
                    break

                try:
                    self.evq.put(msg, source=self.target)
                except ShutdownException:
                    self.state.set('stop')
                    break

        # thus we make sure that all the events from
        # this source are consumed by the main loop
        # in __dbm__() routine
        try:
            self.sync()
            self.log.debug('flush DB for the target')
            self.ndb.task_manager.db_flush(self.target)
        except ShutdownException:
            self.log.debug('shutdown handled by the main thread')
            pass
        self.state.set('stopped')

    def sync(self):
        self.log.debug('sync')
        sync = threading.Event()
        self.evq.put((cmsg_event(self.target, sync),), source=self.target)
        sync.wait()

    def start(self):
        #
        # Start source thread
        with self.lock:
            self.log.debug('starting the source')
            if (self.th is not None) and self.th.is_alive():
                raise RuntimeError('source is running')

            self.th = threading.Thread(
                target=self.receiver,
                name='NDB event source: %s' % (self.target),
            )
            self.th.start()
            return self

    def close(self, code=errno.ECONNRESET, sync=True):
        with self.shutdown_lock:
            if self.shutdown.is_set():
                self.log.debug('already stopped')
                return
            self.log.debug('source shutdown')
            self.shutdown.set()
            if self.nl is not None:
                try:
                    self.nl.close(code=code)
                except Exception as e:
                    self.log.error('source close: %s' % e)
        if sync:
            if self.th is not None:
                self.th.join()
                self.th = None
            else:
                self.log.debug('receiver thread missing')

    def restart(self, reason='unknown'):
        with self.lock:
            with self.shutdown_lock:
                self.log.debug('restarting the source, reason <%s>' % (reason))
                self.started.clear()
                try:
                    self.close()
                    if self.th:
                        self.th.join()
                    self.shutdown.clear()
                    self.start()
                finally:
                    pass
        self.started.wait()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def load_sql(self):
        #
        spec = self.ndb.task_manager.db_fetchone(
            '''
                                        SELECT * FROM sources
                                        WHERE f_target = %s
                                        '''
            % self.ndb.schema.plch,
            (self.target,),
        )
        self['target'], self['kind'] = spec
        for spec in self.ndb.task_manager.db_fetch(
            '''
                                          SELECT * FROM sources_options
                                          WHERE f_target = %s
                                          '''
            % self.ndb.schema.plch,
            (self.target,),
        ):
            f_target, f_name, f_type, f_value = spec
            self[f_name] = int(f_value) if f_type == 'int' else f_value
