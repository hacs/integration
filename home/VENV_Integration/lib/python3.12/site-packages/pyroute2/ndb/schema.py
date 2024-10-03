'''
Backends
--------

NDB stores all the records in an SQL database. By default it uses
the SQLite3 module, which is a part of the Python stdlib, so no
extra packages are required::

    # SQLite3 -- simple in-memory DB
    ndb = NDB()

    # SQLite3 -- same as above with explicit arguments
    ndb = NDB(db_provider='sqlite3', db_spec=':memory:')

    # SQLite3 -- file DB
    ndb = NDB(db_provider='sqlite3', db_spec='test.db')

It is also possible to use a PostgreSQL database via psycopg2
module::

    # PostgreSQL -- local DB
    ndb = NDB(db_provider='psycopg2',
              db_spec={'dbname': 'test'})

    # PostgreSQL -- remote DB
    ndb = NDB(db_provider='psycopg2',
              db_spec={'dbname': 'test',
                       'host': 'db1.example.com'})

Database backup
---------------

Built-in database backup is implemented now only for SQLite3 backend.
For the PostgresSQL backend you have to use external utilities like
`pg_dump`::

    # create an NDB instance
    ndb = NDB()  # the defaults: db_provider='sqlite3', db_spec=':memory:'
    ...
    # dump the DB to a file
    ndb.backup('backup.db')

SQL schema
----------

By default NDB deletes the data from the DB upon exit. In order to preserve
the data, use `NDB(db_cleanup=False, ...)`

Here is an example schema (may be changed with releases)::

                List of relations
     Schema |       Name       | Type  | Owner
    --------+------------------+-------+-------
     public | addresses        | table | root
     public | af_bridge_fdb    | table | root
     public | af_bridge_ifs    | table | root
     public | af_bridge_vlans  | table | root
     public | enc_mpls         | table | root
     public | ifinfo_bond      | table | root
     public | ifinfo_bridge    | table | root
     public | ifinfo_gre       | table | root
     public | ifinfo_gretap    | table | root
     public | ifinfo_ip6gre    | table | root
     public | ifinfo_ip6gretap | table | root
     public | ifinfo_ip6tnl    | table | root
     public | ifinfo_ipip      | table | root
     public | ifinfo_ipvlan    | table | root
     public | ifinfo_macvlan   | table | root
     public | ifinfo_macvtap   | table | root
     public | ifinfo_sit       | table | root
     public | ifinfo_tun       | table | root
     public | ifinfo_vlan      | table | root
     public | ifinfo_vrf       | table | root
     public | ifinfo_vti       | table | root
     public | ifinfo_vti6      | table | root
     public | ifinfo_vxlan     | table | root
     public | interfaces       | table | root
     public | metrics          | table | root
     public | neighbours       | table | root
     public | netns            | table | root
     public | nh               | table | root
     public | p2p              | table | root
     public | routes           | table | root
     public | rules            | table | root
     public | sources          | table | root
     public | sources_options  | table | root
    (33 rows)

    rtnl=# select f_index, f_ifla_ifname from interfaces;
     f_index | f_ifla_ifname
    ---------+---------------
           1 | lo
           2 | eth0
          28 | ip_vti0
          31 | ip6tnl0
          32 | ip6_vti0
       36445 | br0
       11434 | dummy0
           3 | eth1
    (8 rows)

    rtnl=# select f_index, f_ifla_br_stp_state from ifinfo_bridge;
     f_index | f_ifla_br_stp_state
    ---------+---------------------
       36445 |                   0
    (1 row)

Database upgrade
----------------

There is no DB schema upgrade from release to release. All the
data stored in the DB is being fetched from the OS in the runtime,
thus no persistence required.

If you're using a PostgreSQL DB or a file based SQLite, simply drop
all the tables from the DB, and NDB will create them from scratch
on startup.
'''

import enum
import json
import random
import sqlite3
import sys
import time
import traceback
from collections import OrderedDict
from functools import partial

from pyroute2 import config
from pyroute2.common import basestring, uuid32

#
from .objects import address, interface, neighbour, netns, route, rule

try:
    import psycopg2
except ImportError:
    psycopg2 = None

#
# the order is important
#
plugins = [interface, address, neighbour, route, netns, rule]

MAX_ATTEMPTS = 5


class DBProvider(enum.Enum):
    sqlite3 = 'sqlite3'
    psycopg2 = 'psycopg2'

    def __eq__(self, r):
        return str(self) == r


def publish(f):
    if isinstance(f, str):

        def decorate(m):
            m.publish = f
            return m

        return decorate

    f.publish = True
    return f


class DBDict(dict):
    def __init__(self, schema, table):
        self.schema = schema
        self.table = table

    @publish('get')
    def __getitem__(self, key):
        for (record,) in self.schema.fetch(
            f'''
            SELECT f_value FROM {self.table}
            WHERE f_key = {self.schema.plch}
            ''',
            (key,),
        ):
            return json.loads(record)
        raise KeyError(f'key {key} not found')

    @publish('set')
    def __setitem__(self, key, value):
        del self[key]
        self.schema.execute(
            f'''
            INSERT INTO {self.table}
            VALUES ({self.schema.plch}, {self.schema.plch})
            ''',
            (key, json.dumps(value)),
        )

    @publish('del')
    def __delitem__(self, key):
        self.schema.execute(
            f'''
            DELETE FROM {self.table}
            WHERE f_key = {self.schema.plch}
            ''',
            (key,),
        )

    @publish
    def keys(self):
        for (key,) in self.schema.fetch(f'SELECT f_key FROM {self.table}'):
            yield key

    @publish
    def items(self):
        for key, value in self.schema.fetch(
            f'SELECT f_key, f_value FROM {self.table}'
        ):
            yield key, json.loads(value)

    @publish
    def values(self):
        for (value,) in self.schema.fetch(f'SELECT f_value FROM {self.table}'):
            yield json.loads(value)


class DBSchema:
    connection = None
    event_map = None
    key_defaults = None
    snapshots = None  # <table_name>: <obj_weakref>

    spec = OrderedDict()
    classes = {}
    #
    # OBS: field names MUST go in the same order as in the spec,
    # that's for the load_netlink() to work correctly -- it uses
    # one loop to fetch both index and row values
    #
    indices = {}
    foreign_keys = {}

    def __init__(self, config, sources, event_map, log_channel):
        global plugins
        self.sources = sources
        self.config = DBDict(self, 'config')
        self.stats = {}
        self.connection = None
        self.cursor = None
        self.log = log_channel
        self.snapshots = {}
        self.key_defaults = {}
        self.event_map = {}
        # cache locally these variables so they will not be
        # loaded from SQL for every incoming message; this
        # means also that these variables can not be changed
        # in runtime
        self.rtnl_log = config['rtnl_debug']
        self.provider = config['provider']
        #
        for plugin in plugins:
            #
            # 1. spec
            #
            for name, spec in plugin.init['specs']:
                self.spec[name] = spec.as_dict()
                self.indices[name] = spec.index
                self.foreign_keys[name] = spec.foreign_keys
            #
            # 2. classes
            #
            for name, cls in plugin.init['classes']:
                self.classes[name] = cls
        #
        self.initdb(config)
        #
        for plugin in plugins:
            #
            emap = plugin.init['event_map']
            #
            for etype, ehndl in emap.items():
                handlers = []
                for h in ehndl:
                    if isinstance(h, basestring):
                        handlers.append(partial(self.load_netlink, h))
                    else:
                        handlers.append(partial(h, self))
                self.event_map[etype] = handlers

        self.gctime = self.ctime = time.time()

    def initdb(self, config):
        if self.connection is not None:
            self.close()
        if config['provider'] == DBProvider.sqlite3:
            self.connection = sqlite3.connect(config['spec'])
            self.plch = '?'
            self.connection.execute('PRAGMA foreign_keys = ON')
        elif config['provider'] == DBProvider.psycopg2:
            self.connection = psycopg2.connect(**config['spec'])
            self.plch = '%s'
        else:
            raise TypeError('DB provider not supported')
        self.cursor = self.connection.cursor()
        #
        # compile request lines
        #
        self.compiled = {}
        for table in self.spec.keys():
            self.compiled[table] = self.compile_spec(
                table, self.spec[table], self.indices[table]
            )
            self.create_table(table)
        #
        # service tables
        #
        self.execute(
            '''
                     DROP TABLE IF EXISTS sources_options
                     '''
        )
        self.execute(
            '''
                     DROP TABLE IF EXISTS sources
                     '''
        )
        self.execute(
            '''
            DROP TABLE IF EXISTS config
        '''
        )
        self.execute(
            '''
            CREATE TABLE config
                (f_key TEXT PRIMARY KEY, f_value TEXT NOT NULL)
        '''
        )
        self.execute(
            '''
                     CREATE TABLE IF NOT EXISTS sources
                     (f_target TEXT PRIMARY KEY,
                      f_kind TEXT NOT NULL)
                     '''
        )
        self.execute(
            '''
                     CREATE TABLE IF NOT EXISTS sources_options
                     (f_target TEXT NOT NULL,
                      f_name TEXT NOT NULL,
                      f_type TEXT NOT NULL,
                      f_value TEXT NOT NULL,
                      FOREIGN KEY (f_target)
                          REFERENCES sources(f_target)
                          ON UPDATE CASCADE
                          ON DELETE CASCADE)
                     '''
        )
        for key, value in config.items():
            self.config[key] = value

    def merge_spec(self, table1, table2, table, schema_idx):
        spec1 = self.compiled[table1]
        spec2 = self.compiled[table2]
        names = spec1['names'] + spec2['names'][:-1]
        all_names = spec1['all_names'] + spec2['all_names'][2:-1]
        norm_names = spec1['norm_names'] + spec2['norm_names'][2:-1]
        idx = ('target', 'tflags') + schema_idx
        f_names = ['f_%s' % x for x in all_names]
        f_set = ['f_%s = %s' % (x, self.plch) for x in all_names]
        f_idx = ['f_%s' % x for x in idx]
        f_idx_match = ['%s.%s = %s' % (table2, x, self.plch) for x in f_idx]
        plchs = [self.plch] * len(f_names)
        return {
            'names': names,
            'all_names': all_names,
            'norm_names': norm_names,
            'idx': idx,
            'fnames': ','.join(f_names),
            'plchs': ','.join(plchs),
            'fset': ','.join(f_set),
            'knames': ','.join(f_idx),
            'fidx': ' AND '.join(f_idx_match),
        }

    def compile_spec(self, table, schema_names, schema_idx):
        # e.g.: index, flags, IFLA_IFNAME
        #
        names = []
        #
        # same + two internal fields
        #
        all_names = ['target', 'tflags']
        #
        #
        norm_names = ['target', 'tflags']

        bclass = self.classes.get(table)

        for name in schema_names:
            names.append(name[-1])
            all_names.append(name[-1])

            iclass = bclass
            if len(name) > 1:
                for step in name[:-1]:
                    imap = dict(iclass.nla_map)
                    iclass = getattr(iclass, imap[step])
            norm_names.append(iclass.nla2name(name[-1]))

        #
        # escaped names: f_index, f_flags, f_IFLA_IFNAME
        #
        # the reason: words like "index" are keywords in SQL
        # and we can not use them; neither can we change the
        # C structure
        #
        f_names = ['f_%s' % x for x in all_names]
        #
        # set the fields
        #
        # e.g.: f_flags = ?, f_IFLA_IFNAME = ?
        #
        # there are different placeholders:
        # ? -- SQLite3
        # %s -- PostgreSQL
        # so use self.plch here
        #
        f_set = ['f_%s = %s' % (x, self.plch) for x in all_names]
        #
        # the set of the placeholders to use in the INSERT statements
        #
        plchs = [self.plch] * len(f_names)
        #
        # the index schema; use target and tflags in every index
        #
        idx = ('target', 'tflags') + schema_idx
        #
        # the same, escaped: f_target, f_tflags etc.
        #
        f_idx = ['f_%s' % x for x in idx]
        #
        # normalized idx names
        #
        norm_idx = [iclass.nla2name(x) for x in idx]
        #
        # match the index fields, fully qualified
        #
        # interfaces.f_index = ?, interfaces.f_IFLA_IFNAME = ?
        #
        # the same issue with the placeholders
        #
        f_idx_match = ['%s.%s = %s' % (table, x, self.plch) for x in f_idx]

        return {
            'names': names,
            'all_names': all_names,
            'norm_names': norm_names,
            'idx': idx,
            'norm_idx': norm_idx,
            'fnames': ','.join(f_names),
            'plchs': ','.join(plchs),
            'fset': ','.join(f_set),
            'knames': ','.join(f_idx),
            'fidx': ' AND '.join(f_idx_match),
            'lookup_fallbacks': iclass.lookup_fallbacks,
        }

    @publish
    def add_nl_source(self, target, kind, spec):
        '''
        A temprorary method, to be moved out
        '''
        # flush
        self.execute(
            '''
                DELETE FROM sources_options
                WHERE f_target = %s
            '''
            % self.plch,
            (target,),
        )
        self.execute(
            '''
                DELETE FROM sources
                WHERE f_target = %s
            '''
            % self.plch,
            (target,),
        )
        # add
        self.execute(
            '''
                INSERT INTO sources (f_target, f_kind)
                VALUES (%s, %s)
            '''
            % (self.plch, self.plch),
            (target, kind),
        )
        for key, value in spec.items():
            vtype = 'int' if isinstance(value, int) else 'str'
            self.execute(
                '''
                    INSERT INTO sources_options
                    (f_target, f_name, f_type, f_value)
                    VALUES (%s, %s, %s, %s)
                '''
                % (self.plch, self.plch, self.plch, self.plch),
                (target, key, vtype, value),
            )

    def execute(self, *argv, **kwarg):
        try:
            #
            # FIXME: add logging
            #
            for _ in range(MAX_ATTEMPTS):
                try:
                    self.cursor.execute(*argv, **kwarg)
                    break
                except (sqlite3.InterfaceError, sqlite3.OperationalError) as e:
                    self.log.debug('%s' % e)
                    #
                    # Retry on:
                    # -- InterfaceError: Error binding parameter ...
                    # -- OperationalError: SQL logic error
                    #
                    pass
            else:
                raise Exception('DB execute error: %s %s' % (argv, kwarg))
        except Exception:
            raise
        finally:
            self.connection.commit()  # no performance optimisation yet
        return self.cursor

    @publish
    def fetchone(self, *argv, **kwarg):
        for row in self.fetch(*argv, **kwarg):
            return row
        return None

    @publish
    def fetch(self, *argv, **kwarg):
        self.execute(*argv, **kwarg)
        while True:
            row_set = self.cursor.fetchmany()
            if not row_set:
                return
            for row in row_set:
                yield row

    @publish
    def backup(self, spec):
        if sys.version_info >= (3, 7) and self.provider == DBProvider.sqlite3:
            backup_connection = sqlite3.connect(spec)
            self.connection.backup(backup_connection)
            backup_connection.close()
        else:
            raise NotImplementedError()

    @publish
    def export(self, f='stdout'):
        close = False
        if f in ('stdout', 'stderr'):
            f = getattr(sys, f)
        elif isinstance(f, basestring):
            f = open(f, 'w')
            close = True
        try:
            for table in self.spec.keys():
                f.write('\ntable %s\n' % table)
                for record in self.execute('SELECT * FROM %s' % table):
                    f.write(' '.join([str(x) for x in record]))
                    f.write('\n')
                if self.rtnl_log:
                    f.write('\ntable %s_log\n' % table)
                    for record in self.execute('SELECT * FROM %s_log' % table):
                        f.write(' '.join([str(x) for x in record]))
                        f.write('\n')
        finally:
            if close:
                f.close()

    def close(self):
        if self.config['spec'] != ':memory:':
            # simply discard in-memory sqlite db on exit
            self.purge_snapshots()
            self.connection.commit()
        self.connection.close()

    @publish
    def commit(self):
        self.connection.commit()

    def create_table(self, table):
        req = ['f_target TEXT NOT NULL', 'f_tflags BIGINT NOT NULL DEFAULT 0']
        fields = []
        self.key_defaults[table] = {}
        for field in self.spec[table].items():
            #
            # Why f_?
            # 'Cause there are attributes like 'index' and such
            # names may not be used in SQL statements
            #
            field = (field[0][-1], field[1])
            fields.append('f_%s %s' % field)
            req.append('f_%s %s' % field)
            if field[1].strip().startswith('TEXT'):
                self.key_defaults[table][field[0]] = ''
            else:
                self.key_defaults[table][field[0]] = 0
        if table in self.foreign_keys:
            for key in self.foreign_keys[table]:
                spec = (
                    '(%s)' % ','.join(key['fields']),
                    '%s(%s)' % (key['parent'], ','.join(key['parent_fields'])),
                )
                req.append(
                    'FOREIGN KEY %s REFERENCES %s '
                    'ON UPDATE CASCADE '
                    'ON DELETE CASCADE ' % spec
                )
                #
                # make a unique index for compound keys on
                # the parent table
                #
                # https://sqlite.org/foreignkeys.html
                #
                if len(key['fields']) > 1:
                    idxname = 'uidx_%s_%s' % (
                        key['parent'],
                        '_'.join(key['parent_fields']),
                    )
                    self.execute(
                        'CREATE UNIQUE INDEX '
                        'IF NOT EXISTS %s ON %s' % (idxname, spec[1])
                    )

        req = ','.join(req)
        req = 'CREATE TABLE IF NOT EXISTS ' '%s (%s)' % (table, req)
        self.execute(req)

        index = ','.join(
            ['f_target', 'f_tflags']
            + ['f_%s' % x for x in self.indices[table]]
        )
        req = 'CREATE UNIQUE INDEX IF NOT EXISTS ' '%s_idx ON %s (%s)' % (
            table,
            table,
            index,
        )
        self.execute(req)

        #
        # create table for the transaction buffer: there go the system
        # updates while the transaction is not committed.
        #
        # w/o keys (yet)
        #
        # req = ['f_target TEXT NOT NULL',
        #        'f_tflags INTEGER NOT NULL DEFAULT 0']
        # req = ','.join(req)
        # self.execute('CREATE TABLE IF NOT EXISTS '
        #              '%s_buffer (%s)' % (table, req))
        #
        # create the log table, if required
        #
        if self.rtnl_log:
            req = [
                'f_tstamp BIGINT NOT NULL',
                'f_target TEXT NOT NULL',
                'f_event INTEGER NOT NULL',
            ] + fields
            req = ','.join(req)
            self.execute(
                'CREATE TABLE IF NOT EXISTS ' '%s_log (%s)' % (table, req)
            )

    def mark(self, target, mark):
        for table in self.spec:
            self.execute(
                '''
                         UPDATE %s SET f_tflags = %s
                         WHERE f_target = %s
                         '''
                % (table, self.plch, self.plch),
                (mark, target),
            )

    @publish
    def flush(self, target):
        for table in self.spec:
            self.execute(
                '''
                         DELETE FROM %s WHERE f_target = %s
                         '''
                % (table, self.plch),
                (target,),
            )

    @publish
    def save_deps(self, ctxid, weak_ref, iclass):
        uuid = uuid32()
        obj = weak_ref()
        obj_k = obj.key
        idx = self.indices[obj.table]
        conditions = []
        values = []
        for key in idx:
            conditions.append('f_%s = %s' % (key, self.plch))
            if key in obj_k:
                values.append(obj_k[key])
            else:
                values.append(obj.get(iclass.nla2name(key)))
        #
        # save the old f_tflags value
        #
        tflags = self.execute(
            '''
                           SELECT f_tflags FROM %s
                           WHERE %s
                           '''
            % (obj.table, ' AND '.join(conditions)),
            values,
        ).fetchone()[0]
        #
        # mark tflags for obj
        #
        obj.mark_tflags(uuid)

        #
        # f_tflags is used in foreign keys ON UPDATE CASCADE, so all
        # related records will be marked
        #
        for table in self.spec:
            self.log.debug('create snapshot %s_%s' % (table, ctxid))
            #
            # create the snapshot table
            #
            self.execute(
                '''
                         CREATE TABLE IF NOT EXISTS %s_%s
                         AS SELECT * FROM %s
                         WHERE
                             f_tflags IS NULL
                         '''
                % (table, ctxid, table)
            )
            #
            # copy the data -- is it possible to do it in one step?
            #
            self.execute(
                '''
                         INSERT INTO %s_%s
                         SELECT * FROM %s
                         WHERE
                             f_tflags = %s
                         '''
                % (table, ctxid, table, self.plch),
                [uuid],
            )
        #
        # unmark all the data
        #
        obj.mark_tflags(tflags)

        for table in self.spec:
            self.execute(
                '''
                         UPDATE %s_%s SET f_tflags = %s
                         '''
                % (table, ctxid, self.plch),
                [tflags],
            )
            self.snapshots['%s_%s' % (table, ctxid)] = weak_ref

    @publish
    def purge_snapshots(self):
        for table in tuple(self.snapshots):
            for _ in range(MAX_ATTEMPTS):
                try:
                    if self.provider == DBProvider.sqlite3:
                        self.execute('DROP TABLE %s' % table)
                    elif self.provider == DBProvider.psycopg2:
                        self.execute('DROP TABLE %s CASCADE' % table)
                    self.connection.commit()
                    del self.snapshots[table]
                    break
                except sqlite3.OperationalError:
                    #
                    # Retry on:
                    # -- OperationalError: database table is locked
                    #
                    time.sleep(random.random())
            else:
                raise Exception('DB snapshot error')

    @publish
    def get(self, table, spec):
        #
        # Retrieve info from the DB
        #
        # ndb.interfaces.get({'ifname': 'eth0'})
        #
        conditions = []
        values = []
        cls = self.classes[table]
        cspec = self.compiled[table]
        for key, value in spec.items():
            if key not in cspec['all_names']:
                key = cls.name2nla(key)
            if key not in cspec['all_names']:
                raise KeyError('field name not found')
            conditions.append('f_%s = %s' % (key, self.plch))
            values.append(value)
        req = 'SELECT * FROM %s WHERE %s' % (table, ' AND '.join(conditions))
        for record in self.fetch(req, values):
            yield dict(zip(self.compiled[table]['all_names'], record))

    def log_netlink(self, table, target, event, ctable=None):
        #
        # RTNL Logs
        #
        fkeys = self.compiled[table]['names']
        fields = ','.join(
            ['f_tstamp', 'f_target', 'f_event'] + ['f_%s' % x for x in fkeys]
        )
        pch = ','.join([self.plch] * (len(fkeys) + 3))
        values = [
            int(time.time() * 1000),
            target,
            event.get('header', {}).get('type', 0),
        ]
        for field in fkeys:
            value = event.get_attr(field) or event.get(field)
            if value is None and field in self.indices[ctable or table]:
                value = self.key_defaults[table][field]
            if isinstance(value, (dict, list, tuple, set)):
                value = json.dumps(value)
            values.append(value)
        self.execute(
            'INSERT INTO %s_log (%s) VALUES (%s)' % (table, fields, pch),
            values,
        )

    def load_netlink(self, table, target, event, ctable=None, propagate=False):
        #
        if self.rtnl_log:
            self.log_netlink(table, target, event, ctable)
        #
        # Update metrics
        #
        if 'stats' in event['header']:
            self.stats[target] = event['header']['stats']
        #
        # Periodic jobs
        #
        if time.time() - self.gctime > config.gc_timeout:
            self.gctime = time.time()

            # clean dead snapshots after GC timeout
            for name, wref in tuple(self.snapshots.items()):
                if wref() is None:
                    del self.snapshots[name]
                    try:
                        self.execute('DROP TABLE %s' % name)
                    except Exception as e:
                        self.log.debug(
                            'failed to remove table %s: %s' % (name, e)
                        )

            # clean marked routes
            self.execute(
                'DELETE FROM routes WHERE ' '(f_gc_mark + 5) < %s' % self.plch,
                (int(time.time()),),
            )
        #
        # The event type
        #
        if event['header'].get('type', 0) % 2:
            #
            # Delete an object
            #
            conditions = ['f_target = %s' % self.plch]
            values = [target]
            for key in self.indices[table]:
                conditions.append('f_%s = %s' % (key, self.plch))
                value = event.get(key) or event.get_attr(key)
                if value is None:
                    value = self.key_defaults[table][key]
                if isinstance(value, (dict, list, tuple, set)):
                    value = json.dumps(value)
                values.append(value)
            self.execute(
                'DELETE FROM %s WHERE'
                ' %s' % (table, ' AND '.join(conditions)),
                values,
            )
        else:
            #
            # Create or set an object
            #
            # field values
            values = [target, 0]
            # index values
            ivalues = [target, 0]
            compiled = self.compiled[table]
            # a map of sub-NLAs
            nodes = {}

            # fetch values (exc. the first two columns)
            for fname, ftype in self.spec[table].items():
                node = event

                # if the field is located in a sub-NLA
                if len(fname) > 1:
                    # see if we tried to get it already
                    if fname[:-1] not in nodes:
                        # descend
                        for steg in fname[:-1]:
                            node = node.get_attr(steg)
                            if node is None:
                                break
                        nodes[fname[:-1]] = node
                    # lookup the sub-NLA in the map
                    node = nodes[fname[:-1]]
                    # the event has no such sub-NLA
                    if node is None:
                        values.append(None)
                        continue

                # NLA have priority
                value = node.get_attr(fname[-1])
                if value is None:
                    value = node.get(fname[-1])
                if value is None and fname[-1] in self.compiled[table]['idx']:
                    value = self.key_defaults[table][fname[-1]]
                    node['attrs'].append((fname[-1], value))
                if isinstance(value, (dict, list, tuple, set)):
                    value = json.dumps(value)
                if fname[-1] in compiled['idx']:
                    ivalues.append(value)
                values.append(value)

            try:
                if self.provider == DBProvider.psycopg2:
                    #
                    # run UPSERT -- the DB provider must support it
                    #
                    (
                        self.execute(
                            'INSERT INTO %s (%s) VALUES (%s) '
                            'ON CONFLICT (%s) '
                            'DO UPDATE SET %s WHERE %s'
                            % (
                                table,
                                compiled['fnames'],
                                compiled['plchs'],
                                compiled['knames'],
                                compiled['fset'],
                                compiled['fidx'],
                            ),
                            (values + values + ivalues),
                        )
                    )
                    #
                elif self.provider == DBProvider.sqlite3:
                    #
                    # SQLite3 >= 3.24 actually has UPSERT, but ...
                    #
                    # We can not use here INSERT OR REPLACE as well, since
                    # it drops (almost always) records with foreign key
                    # dependencies. Maybe a bug in SQLite3, who knows.
                    #
                    count = (
                        self.execute(
                            '''
                                      SELECT count(*) FROM %s WHERE %s
                                      '''
                            % (table, compiled['fidx']),
                            ivalues,
                        ).fetchone()
                    )[0]
                    if count == 0:
                        self.execute(
                            '''
                                     INSERT INTO %s (%s) VALUES (%s)
                                     '''
                            % (table, compiled['fnames'], compiled['plchs']),
                            values,
                        )
                    else:
                        self.execute(
                            '''
                                     UPDATE %s SET %s WHERE %s
                                     '''
                            % (table, compiled['fset'], compiled['fidx']),
                            (values + ivalues),
                        )
                else:
                    raise NotImplementedError()
                #
            except Exception as e:
                #
                if propagate:
                    raise e
                #
                # A good question, what should we do here
                self.log.debug(
                    'load_netlink: %s %s %s' % (table, target, event)
                )
                self.log.error('load_netlink: %s' % traceback.format_exc())
