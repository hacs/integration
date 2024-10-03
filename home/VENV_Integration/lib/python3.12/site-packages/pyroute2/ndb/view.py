'''
Accessing objects
=================

NDB objects are grouped into "views":

    * interfaces
    * addresses
    * routes
    * neighbours
    * rules
    * netns
    * ...

Views are dictionary-like objects that accept strings or dict selectors::

    # access eth0
    ndb.interfaces["eth0"]

    # access eth0 in the netns test01
    ndb.sources.add(netns="test01")
    ndb.interfaces[{"target": "test01", "ifname": "eth0"}]

    # access a route to 10.4.0.0/24
    ndb.routes["10.4.0.0/24"]

    # same with a dict selector
    ndb.routes[{"dst": "10.4.0.0", "dst_len": 24}]

Objects cache
=============

NDB create objects on demand, it doesn't create thousands of route objects
for thousands of routes by default. The object is being created only when
accessed for the first time, and stays in the cache as long as it has any
not committed changes. To inspect cached objects, use views' `.cache`::

    >>> ndb.interfaces.cache.keys()
    [(('target', u'localhost'), ('tflags', 0), ('index', 1)),  # lo
     (('target', u'localhost'), ('tflags', 0), ('index', 5))]  # eth3

There is no asynchronous cache invalidation, the cache is being cleaned up
every time when an object is accessed.

API
===
'''

import errno
import gc
import json
import queue
import threading
import time
from collections import OrderedDict
from functools import partial

from pyroute2 import cli, config
from pyroute2.common import basestring

##
# NDB stuff
from .auth_manager import check_auth
from .objects import RSLV_DELETE
from .objects.address import Address
from .objects.interface import Interface, Vlan
from .objects.neighbour import FDBRecord, Neighbour
from .objects.netns import NetNS
from .objects.route import Route
from .objects.rule import Rule
from .report import Record, RecordSet
from .source import Source, SourceProxy


class TmpHandler:
    def __init__(self, ndb, event, handler):
        self.ndb = ndb
        self.event = event
        self.handler = handler

    def __enter__(self):
        self.ndb.task_manager.register_handler(
            self.ndb.schema.classes[self.event], self.handler
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.ndb.task_manager.unregister_handler(
            self.ndb.schema.classes[self.event], self.handler
        )


class View(dict):
    '''
    The View() object returns RTNL objects on demand::

        ifobj1 = ndb.interfaces['eth0']
        ifobj2 = ndb.interfaces['eth0']
        # ifobj1 != ifobj2
    '''

    def __init__(self, ndb, table, chain=None, auth_managers=None):
        self.ndb = ndb
        self.log = ndb.log.channel('view.%s' % table)
        self.table = table
        self.event = table  # FIXME
        self.chain = chain
        self.cache = {}
        if auth_managers is None:
            auth_managers = []
        if chain:
            auth_managers += chain.auth_managers
        self.auth_managers = auth_managers
        self.constraints = {}
        self.classes = OrderedDict()
        self.classes['interfaces'] = Interface
        self.classes['addresses'] = Address
        self.classes['neighbours'] = Neighbour
        self.classes['af_bridge_fdb'] = FDBRecord
        self.classes['routes'] = Route
        self.classes['rules'] = Rule
        self.classes['netns'] = NetNS
        self.classes['af_bridge_vlans'] = Vlan

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @property
    def default_target(self):
        if self.table == 'netns':
            return self.ndb.nsmanager
        else:
            return self.ndb.localhost

    @property
    def context(self):
        if self.chain is not None:
            return self.chain.context
        else:
            return {}

    def getmany(self, spec, table=None):
        return self.ndb.task_manager.db_get(table or self.table, spec)

    def getone(self, spec, table=None):
        for obj in self.getmany(spec, table):
            return obj

    @cli.change_pointer
    @check_auth('obj:read')
    def get(self, spec=None, table=None, **kwarg):
        spec = spec or kwarg
        try:
            return self.__getitem__(spec, table)
        except KeyError:
            return None

    def template(self, key, table=None):
        if self.chain:
            context = self.chain.context
        else:
            context = {}
        iclass = self.classes[table or self.table]
        spec = iclass.new_spec(key, context, self.default_target)
        return iclass(
            self,
            spec,
            load=False,
            master=self.chain,
            auth_managers=self.auth_managers,
        )

    @cli.change_pointer
    @check_auth('obj:modify')
    def create(self, *argspec, **kwspec):
        iclass = self.classes[self.table]
        if self.chain:
            context = self.chain.context
        else:
            context = {}
        spec = iclass.new_spec(
            kwspec or argspec[0], context, self.default_target
        )
        if self.chain:
            spec['ndb_chain'] = self.chain
        spec['create'] = True
        return self[spec]

    @cli.change_pointer
    @check_auth('obj:modify')
    def ensure(self, *argspec, **kwspec):
        try:
            obj = self.locate(**kwspec)
        except KeyError:
            obj = self.create(**kwspec)
        for key, value in kwspec.items():
            obj[key] = value
        return obj

    @cli.change_pointer
    @check_auth('obj:modify')
    def add(self, *argspec, **kwspec):
        self.log.warning(
            '''\n
        The name add() will be removed in future releases, use create()
        instead. If you believe that the idea to rename is wrong, please
        file your opinion to the project's bugtracker.

        The reason behind the rename is not to confuse interfaces.add() with
        bridge and bond port operations, that don't create any new interfaces
        but work on existing ones.
        '''
        )
        return self.create(*argspec, **kwspec)

    @check_auth('obj:read')
    def wait(self, **spec):
        ret = None
        timeout = spec.pop('timeout', -1)
        action = spec.pop('action', 'add')
        ctime = time.time()

        # install a limited events queue -- for a possible immediate reaction
        evq = queue.Queue(maxsize=100)

        def handler(evq, target, event):
            # ignore the "queue full" exception
            #
            # if we miss some events here, nothing bad happens: we just
            # load them from the DB after a timeout, falling back to
            # the DB polling
            #
            # the most important here is not to allocate too much memory
            try:
                evq.put_nowait((target, event))
            except queue.Full:
                pass

        with TmpHandler(self.ndb, self.event, partial(handler, evq)):
            while True:
                ret = self.get(spec)
                if (ret and action == 'add') or (
                    ret is None and action == 'remove'
                ):
                    return ret
                try:
                    target, msg = evq.get(timeout=1)
                except queue.Empty:
                    pass
                if timeout > -1:
                    if ctime + timeout < time.time():
                        raise TimeoutError()

    @check_auth('obj:read')
    def locate(self, spec=None, table=None, **kwarg):
        '''
        This method works like `__getitem__()`, but the important
        difference is that it uses only key fields to locate the
        object in the DB, ignoring all other keys.

        It is useful to locate objects that may change attributes
        during request, like an interface may come up/down, or an
        address may become primary/secondary, so plain
        `__getitem__()` will not match while the object still
        exists.
        '''
        if isinstance(spec, Record):
            spec = spec._as_dict()
        spec = spec or kwarg
        if not spec:
            raise TypeError('got an empty spec')

        table = table or self.table
        iclass = self.classes[table]
        spec = iclass.new_spec(spec)
        kspec = self.ndb.schema.compiled[table]['norm_idx']
        lookup_fallbacks = self.ndb.schema.compiled[table]['lookup_fallbacks']
        request = {}
        for name in kspec:
            name = iclass.nla2name(name)
            if name in spec:
                request[name] = spec[name]
            elif name in lookup_fallbacks:
                fallback = lookup_fallbacks[name]
                if fallback in spec:
                    request[fallback] = spec[fallback]

        if not request:
            raise KeyError('got an empty key')
        return self[request]

    @check_auth('obj:read')
    def __getitem__(self, key, table=None):
        ret = self.template(key, table)

        # rtnl_object.key() returns a dictionary that can not
        # be used as a cache key. Create here a tuple from it.
        # The key order guaranteed by the dictionary.
        cache_key = tuple(ret.key.items())

        rtime = time.time()

        # Iterate all the cache to remove unused and clean
        # (without any started transaction) objects.
        for ckey in tuple(self.cache):
            # Skip the current cache_key to avoid extra
            # cache del/add records in the logs
            if ckey == cache_key:
                continue
            # 1. Remove only expired items
            # 2. The number of changed rtnl_object fields must
            #    be 0 which means that no transaction is started
            # 3. The number of referrers must be > 1, the first
            #    one is the cache itself        <- this op is expensive!
            if (
                rtime - self.cache[ckey].atime > config.cache_expire
                and self.cache[ckey].clean
                and gc.get_referrers(self.cache[ckey])
            ):
                self.log.debug('cache del %s' % (ckey,))
                self.cache.pop(ckey, None)

        if cache_key in self.cache:
            self.log.debug('cache hit %s' % (cache_key,))
            # Explicitly get rid of the created object
            del ret
            # The object from the cache has already
            # registered callbacks, simply return it
            ret = self.cache[cache_key]
            ret.atime = rtime
            return ret
        else:
            # Cache only existing objects
            if self.exists(key):
                ret.load_sql()
                self.log.debug('cache add %s' % (cache_key,))
                self.cache[cache_key] = ret

        ret.register()
        return ret

    def exists(self, key, table=None):
        '''
        Check if the specified object exists in the database::

            ndb.interfaces.exists('eth0')
            ndb.interfaces.exists({'ifname': 'eth0', 'target': 'localhost'})
            ndb.addresses.exists('127.0.0.1/8')
        '''
        if self.chain:
            context = self.chain.context
        else:
            context = {}

        iclass = self.classes[self.table]
        key = iclass.new_spec(key, context, self.default_target)

        iclass.resolve(
            view=self,
            spec=key,
            fields=iclass.resolve_fields,
            policy=RSLV_DELETE,
        )

        table = table or self.table
        schema = self.ndb.schema
        task_manager = self.ndb.task_manager
        names = schema.compiled[self.table]['all_names']

        self.log.debug('check if the key %s exists in table %s' % (key, table))
        keys = []
        values = []
        for name, value in key.items():
            nla_name = iclass.name2nla(name)
            if nla_name in names:
                name = nla_name
            if value is not None and name in names:
                keys.append('f_%s = %s' % (name, schema.plch))
                if isinstance(value, (dict, list, tuple, set)):
                    value = json.dumps(value)
                values.append(value)
        spec = task_manager.db_fetchone(
            'SELECT * FROM %s WHERE %s' % (self.table, ' AND '.join(keys)),
            values,
        )
        if spec is not None:
            self.log.debug('exists')
            return True
        else:
            self.log.debug('not exists')
            return False

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def __iter__(self):
        return self.keys()

    def __contains__(self, key):
        return key in self.dump()

    @check_auth('obj:list')
    def keys(self):
        for record in self.dump():
            yield record

    @check_auth('obj:list')
    def values(self):
        for key in self.keys():
            yield self[key]

    @check_auth('obj:list')
    def items(self):
        for key in self.keys():
            yield (key, self[key])

    @cli.show_result
    def count(self):
        return self.classes[self.table]._count(self)[0]

    def __len__(self):
        return self.count()

    def _keys(self, iclass):
        return ['target', 'tflags'] + self.ndb.schema.compiled[
            iclass.view or iclass.table
        ]['names']

    def _native(self, dump):
        fnames = next(dump)
        for record in dump:
            yield Record(fnames, record, self.classes[self.table])

    @cli.show_result
    @check_auth('obj:list')
    def dump(self):
        iclass = self.classes[self.table]
        return RecordSet(
            self._native(iclass.dump(self)),
            config={
                'recordset_pipe': self.ndb.config.get(
                    'recordset_pipe', 'false'
                )
            },
        )

    @cli.show_result
    @check_auth('obj:list')
    def summary(self):
        iclass = self.classes[self.table]
        return RecordSet(
            self._native(iclass.summary(self)),
            config={
                'recordset_pipe': self.ndb.config.get(
                    'recordset_pipe', 'false'
                )
            },
        )

    def __repr__(self):
        if self.chain and 'ifname' in self.chain:
            parent = f'{self.chain["ifname"]}/'
        else:
            parent = ''
        return f'''
NDB view for {parent}{self.table}
Number of objects: {self.count()}

to list objects use .summary() or .dump()
    -> RecordSet (generator)
        -> Record

key: Union[Record, dict, spec]
to get objects use ...[key] / .__getitem__(key)
    -> RTNL_Object
'''


class SourcesView(View):
    def __init__(self, ndb, auth_managers=None):
        super(SourcesView, self).__init__(ndb, 'sources')
        self.classes['sources'] = Source
        self.cache = {}
        self.proxy = {}
        self.lock = threading.Lock()
        if auth_managers is None:
            auth_managers = []
        self.auth_managers = auth_managers

    def async_add(self, **spec):
        spec = dict(Source.defaults(spec))
        self.cache[spec['target']] = Source(self.ndb, **spec).start()
        return self.cache[spec['target']]

    def add(self, **spec):
        spec = dict(Source.defaults(spec))
        target = spec['target']
        if target in self:
            raise KeyError(f'source {target} exists')
        if 'event' not in spec:
            sync = True
            spec['event'] = threading.Event()
        else:
            sync = False
        self.cache[spec['target']] = Source(self.ndb, **spec).start()
        if sync:
            self.cache[spec['target']].event.wait()
        return self.cache[spec['target']]

    def remove(self, target, code=errno.ECONNRESET, sync=True):
        if target not in self:
            raise KeyError(f'source {target} does not exist')
        with self.lock:
            if target in self.cache:
                source = self.cache[target]
                source.close(code=code, sync=sync)
                return self.cache.pop(target)

    @check_auth('obj:list')
    def keys(self):
        for key in self.cache:
            yield key

    def _keys(self, iclass):
        return ['target', 'kind']

    def wait(self, **spec):
        raise NotImplementedError()

    def _summary(self, *argv, **kwarg):
        return self._dump(*argv, **kwarg)

    def __getitem__(self, key, table=None):
        if isinstance(key, basestring):
            target = key
        elif isinstance(key, dict) and 'target' in key.keys():
            target = key['target']
        else:
            raise KeyError()

        if target in self.cache:
            return self.cache[target]
        elif target in self.proxy:
            return self.proxy[target]
        else:
            proxy = SourceProxy(self.ndb, target)
            self.proxy[target] = proxy
            return proxy
