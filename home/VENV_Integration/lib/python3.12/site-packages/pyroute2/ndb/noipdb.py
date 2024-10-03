import logging

from pyroute2.ndb.main import NDB

log = logging.getLogger(__name__)


class ObjectProxy(dict):
    def __init__(self, obj):
        self._obj = obj

    def __getattribute__(self, key):
        if key[:4] == 'set_':

            def set_value(value):
                self[key[4:]] = value
                return self

            return set_value
        try:
            return self[key]
        except KeyError:
            return super(ObjectProxy, self).__getattribute__(key)

    def __setattr__(self, key, value):
        if key == '_obj':
            super(ObjectProxy, self).__setattr__(key, value)
        else:
            super(ObjectProxy, self).__getattribute__('_obj')[key] = value

    def __getitem__(self, key):
        return super(ObjectProxy, self).__getattribute__('_obj')[key]

    def __setitem__(self, key, value):
        super(ObjectProxy, self).__getattribute__('_obj')[key] = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if hasattr(self, 'commit'):
            self.commit()

    def __repr__(self):
        return repr(super(ObjectProxy, self).__getattribute__('_obj'))

    def __contains__(self, key):
        return key in super(ObjectProxy, self).__getattribute__('_obj')

    def get_ndb_object(self):
        return self._obj

    def keys(self):
        return self._obj.keys()

    def items(self):
        return self._obj.items()

    def values(self):
        return self._obj.values()

    def __iter__(self):
        return self._obj.__iter__()

    @property
    def _mode(self):
        return 'implicit'


class Interface(ObjectProxy):
    def add_ip(self, *argv, **kwarg):
        self._obj.add_ip(*argv, **kwarg)
        return self

    def del_ip(self, *argv, **kwarg):
        self._obj.del_ip(*argv, **kwarg)
        return self

    def add_port(self, *argv, **kwarg):
        self._obj.add_port(*argv, **kwarg)
        return self

    def del_port(self, *argv, **kwarg):
        self._obj.del_port(*argv, **kwarg)
        return self

    def commit(self, *argv, **kwarg):
        self._obj.commit(*argv, **kwarg)
        return self

    def up(self):
        self._obj.set('state', 'up')
        return self

    def down(self):
        self._obj.set('state', 'down')
        return self

    def remove(self):
        self._obj.remove()
        return self

    @property
    def if_master(self):
        return self._obj.get('master', None)

    @property
    def ipaddr(self):
        return tuple(self._obj.ipaddr.dump().select('address', 'prefixlen'))


class Interfaces(ObjectProxy):
    text_create = '''
When `create().commit()` fails, the failed interface object behaves
differently in IPDB and NDB. IPDB saves the failed object in the database,
while the NDB database contains only the system reflection, and the failed
object may stay only being referenced by a variable.

`KeyError: 'object exists'` vs. `CreateException`
'''

    def __getitem__(self, key):
        return Interface(super(Interfaces, self).__getitem__(key))

    def __iter__(self):
        return iter(self.keys())

    def add(self, *argv, **kwarg):
        return self.create(*argv, **kwarg)

    def create(self, *argv, **kwarg):
        log.warning(self.text_create)
        return Interface(self._obj.create(*argv, **kwarg))

    def keys(self):
        ret = []
        for record in self._obj.dump():
            ret += [record.ifname, record.index]
        return ret

    def has_key(self, key):
        return key in self.keys()


class NoIPDB(object):
    text_create = '''
IPDB has a shortcut method to create interfaces: `ipdb.create(...)`.

NDB has `create()` methods only under respective views:
`ndb.interfaces.create(...)`, `ndb.addresses.create(...)` etc.
'''

    text_nl = '''
Unlike IPDB, NDB can work with many netlink sources. The default one
referenced as `localhost`::

    #
    # these two statements are equivalent:
    #
    ndb.sources['localhost'].nl.get_links()
    ipdb.nl.get_links()

'''

    def __init__(self, *argv, **kwarg):
        if argv or kwarg:
            log.warning(
                '%s does not support IPDB parameters, ignoring',
                self.__class__.__name__,
            )
        if len(argv) > 0 or 'nl' in kwarg:
            log.warning(
                '%s does not support shared netlink sources,'
                ' ignoring `nl` and starting with local IPRoute',
                self.__class__.__name__,
            )

        self._ndb = NDB()
        self.interfaces = Interfaces(self._ndb.interfaces)

    @property
    def nl(self):
        log.warning(self.text_nl)
        return self._ndb.sources['localhost'].nl

    @property
    def ipaddr(self):
        ret = dict([(x.index, []) for x in self._ndb.interfaces.dump()])
        for record in self._ndb.addresses.dump():
            ret[record.index].append((record.address, record.prefixlen))
        return ret

    def create(self, *argv, **kwarg):
        log.warning(self.text_create)
        return self.interfaces.create(*argv, **kwarg)

    def release(self):
        self._ndb.close()
