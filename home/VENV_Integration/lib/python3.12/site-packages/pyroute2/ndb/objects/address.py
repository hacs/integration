'''

.. testsetup:: *

    from socket import AF_INET
    from pyroute2 import NDB
    from pyroute2 import config
    config.mock_iproute = True
    ndb = NDB()

.. testcleanup:: *

    ndb.close()

Using the global view
=====================

The `addresses` view provides access to all the addresses registered in the DB,
as well as methods to create and remove them:

.. testcode::

    eth0 = ndb.interfaces['eth0']

    # create an address
    ndb.addresses.create(
        address='10.0.0.1',
        prefixlen=24,
        index=eth0['index'],
    ).commit()

    # remove it
    with ndb.addresses['10.0.0.1/24'] as addr:
        addr.remove()

    # list addresses
    for record in ndb.addresses.summary():
        print(record)

.. testoutput::
    :hide:

    ('localhost', 0, 'lo', '127.0.0.1', 8)
    ('localhost', 0, 'eth0', '192.168.122.28', 24)


Using ipaddr views
==================

Interfaces also provide address views as subsets of the global
address view:

.. testcode::

    with ndb.interfaces['eth0'] as eth0:
        for record in eth0.ipaddr.summary():
            print(record)

.. testoutput::

    ('localhost', 0, 'eth0', '192.168.122.28', 24)

It is possible use the same API as with the global address view:

.. testcode::

    with ndb.interfaces['eth0'] as eth0:
        eth0.ipaddr.create(
            address='10.0.0.1', prefixlen=24  # index is implied
        ).commit()
    for record in ndb.addresses.summary():
        print(record)

.. testoutput::

    ('localhost', 0, 'lo', '127.0.0.1', 8)
    ('localhost', 0, 'eth0', '10.0.0.1', 24)
    ('localhost', 0, 'eth0', '192.168.122.28', 24)

Using interface methods
=======================

Interfaces provide also simple methods to manage addresses:

.. testcode::

    with ndb.interfaces['eth0'] as eth0:
        eth0.del_ip('192.168.122.28/24')  # remove an existing address
        eth0.del_ip(family=AF_INET)  # ... or remove all IPv4 addresses
        eth0.add_ip('10.0.0.1/24')  # add a new IP address
        eth0.add_ip(address='10.0.0.2', prefixlen=24)  # ... or using keywords
        eth0.set('state', 'up')
    with ndb.addresses.summary() as report:
        report.select_records(ifname='eth0')
        for address in report:
            print(address)

.. testoutput::

    ('localhost', 0, 'eth0', '10.0.0.1', 24)
    ('localhost', 0, 'eth0', '10.0.0.2', 24)


Functions `add_ip()` and `del_ip()` return the interface object, so they
can be chained as in the example above, and the final `commit()` will
commit all the changes in the chain.

The keywords to `del_ip()` are the same object field names that may be used
in the selectors or report filters:

.. testcode::

    with ndb.interfaces['eth0'] as eth0:
        eth0.del_ip(prefixlen=24)  # remove all addresses with mask /24

A match function that may be passed to the `del_ip()` is the same as for
`addresses.dump().select_records()`, and it gets a named tuple as the argument.
The fields are named in the same way as address objects fields. So if you
want to filter addresses by a pattern or the `prefixlen` field with a
match function, you may use:

.. testcode:: x1

    with ndb.interfaces['eth0'] as eth0:
        eth0.add_ip('10.0.0.1/25')

    with ndb.interfaces['eth0'] as eth0:
        eth0.del_ip(lambda x: x.address.startswith('192.168'))
        eth0.del_ip(lambda x: x.prefixlen == 25)

An empty `del_ip()` removes all the IP addresses on the interface:

.. testcode:: x2

    with ndb.interfaces['eth0'] as eth0:
        eth0.del_ip()  # flush all the IP:s

Accessing one address details
=============================

Access an address as a separate RTNL object:

.. testcode:: x3

    print(ndb.addresses['192.168.122.28/24'])

.. testoutput:: x3
    :hide:

    {'target': 'localhost', 'address': '192.168.122.28', 'prefixlen': 24, \
'tflags': 0, 'family': 2, 'index': 2, 'local': '192.168.122.28', \
'flags': 512, 'scope': 0, 'label': 'eth0', 'broadcast': '192.168.122.255', \
'anycast': None, 'multicast': None}

Please notice that address objects are read-only, you may not change them,
only remove old ones, and create new.
'''

from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.requests.address import AddressFieldFilter

from ..objects import RTNL_Object


def load_ifaddrmsg(schema, target, event):
    #
    # bypass
    #
    schema.load_netlink('addresses', target, event)
    #
    # last address removal should trigger routes flush
    # Bug-Url: https://github.com/svinota/pyroute2/issues/849
    #
    if event['header']['type'] % 2 and event.get('index'):
        #
        # check IPv4 addresses on the interface
        #
        addresses = schema.execute(
            '''
                              SELECT * FROM addresses WHERE
                              f_target = %s AND
                              f_index = %s AND
                              f_family = 2
                              '''
            % (schema.plch, schema.plch),
            (target, event['index']),
        ).fetchmany()
        if not len(addresses):
            schema.execute(
                '''
                           DELETE FROM routes WHERE
                           f_target = %s AND
                           f_RTA_OIF = %s OR
                           f_RTA_IIF = %s
                           '''
                % (schema.plch, schema.plch, schema.plch),
                (target, event['index'], event['index']),
            )


ifaddr_spec = (
    ifaddrmsg.sql_schema()
    .unique_index('family', 'prefixlen', 'index', 'IFA_ADDRESS', 'IFA_LOCAL')
    .foreign_key(
        'interfaces',
        ('f_target', 'f_tflags', 'f_index'),
        ('f_target', 'f_tflags', 'f_index'),
    )
)

init = {
    'specs': [['addresses', ifaddr_spec]],
    'classes': [['addresses', ifaddrmsg]],
    'event_map': {ifaddrmsg: [load_ifaddrmsg]},
}


class Address(RTNL_Object):
    table = 'addresses'
    msg_class = ifaddrmsg
    field_filter = AddressFieldFilter
    api = 'addr'

    @classmethod
    def _count(cls, view):
        if view.chain:
            return view.ndb.task_manager.db_fetchone(
                'SELECT count(*) FROM %s WHERE f_index = %s'
                % (view.table, view.ndb.schema.plch),
                [view.chain['index']],
            )
        else:
            return view.ndb.task_manager.db_fetchone(
                'SELECT count(*) FROM %s' % view.table
            )

    @classmethod
    def _dump_where(cls, view):
        if view.chain:
            plch = view.ndb.schema.plch
            where = '''
                    WHERE
                        main.f_target = %s AND
                        main.f_index = %s
                    ''' % (
                plch,
                plch,
            )
            values = [view.chain['target'], view.chain['index']]
        else:
            where = ''
            values = []
        return (where, values)

    @classmethod
    def summary(cls, view):
        req = '''
              SELECT
                  main.f_target, main.f_tflags,
                  intf.f_IFLA_IFNAME, main.f_IFA_ADDRESS, main.f_prefixlen
              FROM
                  addresses AS main
              INNER JOIN
                  interfaces AS intf
              ON
                  main.f_index = intf.f_index
                  AND main.f_target = intf.f_target
              '''
        yield ('target', 'tflags', 'ifname', 'address', 'prefixlen')
        where, values = cls._dump_where(view)
        for record in view.ndb.task_manager.db_fetch(req + where, values):
            yield record

    def mark_tflags(self, mark):
        plch = (self.schema.plch,) * 3
        self.schema.execute(
            '''
                            UPDATE interfaces SET
                                f_tflags = %s
                            WHERE f_index = %s AND f_target = %s
                            '''
            % plch,
            (mark, self['index'], self['target']),
        )

    def __init__(self, *argv, **kwarg):
        kwarg['iclass'] = ifaddrmsg
        self.event_map = {ifaddrmsg: "load_rtnlmsg"}
        super(Address, self).__init__(*argv, **kwarg)

    @staticmethod
    def compare_record(left, right):
        if isinstance(right, str):
            return right == left['address'] or right == '%s/%i' % (
                left['address'],
                left['prefixlen'],
            )

    @classmethod
    def spec_normalize(cls, processed, spec):
        '''
        Address key normalization::

            { ... }        ->  { ... }
            "10.0.0.1/24"  ->  {"address": "10.0.0.1",
                                "prefixlen": 24}
        '''
        if isinstance(spec, str):
            processed['address'] = spec
        return processed

    def key_repr(self):
        return '%s/%s %s/%s' % (
            self.get('target', ''),
            self.get('label', self.get('index', '')),
            self.get('local', self.get('address', '')),
            self.get('prefixlen', ''),
        )
