import logging
import struct
import threading
import time
import traceback
import types
from collections import namedtuple
from socket import AF_INET, AF_INET6, AF_UNSPEC, inet_ntop, inet_pton

from pyroute2.common import AF_MPLS, basestring
from pyroute2.ipdb.exceptions import CommitException
from pyroute2.ipdb.linkedset import LinkedSet
from pyroute2.ipdb.transactional import (
    SYNC_TIMEOUT,
    Transactional,
    with_transaction,
)
from pyroute2.netlink import NLM_F_CREATE, NLM_F_MULTI, nlmsg, nlmsg_base, rtnl
from pyroute2.netlink.rtnl import encap_type, rt_proto, rt_type
from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_SECONDARY
from pyroute2.netlink.rtnl.rtmsg import rtmsg
from pyroute2.requests.main import RequestProcessor
from pyroute2.requests.route import RouteFieldFilter

log = logging.getLogger(__name__)
groups = (
    rtnl.RTMGRP_IPV4_ROUTE | rtnl.RTMGRP_IPV6_ROUTE | rtnl.RTMGRP_MPLS_ROUTE
)
IP6_RT_PRIO_USER = 1024


class Metrics(Transactional):
    _fields = [rtmsg.metrics.nla2name(i[0]) for i in rtmsg.metrics.nla_map]


class Encap(Transactional):
    _fields = ['type', 'labels']


class Via(Transactional):
    _fields = ['family', 'addr']


class NextHopSet(LinkedSet):
    def __init__(self, prime=None):
        super(NextHopSet, self).__init__()
        prime = prime or []
        for v in prime:
            self.add(v)

    def __sub__(self, vs):
        ret = type(self)()
        sub = set(self.raw.keys()) - set(vs.raw.keys())
        for v in sub:
            ret.add(self[v], raw=self.raw[v])
        return ret

    def __make_nh(self, prime):
        if isinstance(prime, BaseRoute):
            return prime.make_nh_key(prime)
        elif isinstance(prime, dict):
            if prime.get('family', None) == AF_MPLS:
                return MPLSRoute.make_nh_key(prime)
            else:
                return Route.make_nh_key(prime)
        elif isinstance(prime, tuple):
            return prime
        else:
            raise TypeError("unknown prime type %s" % type(prime))

    def __getitem__(self, key):
        return self.raw[key]

    def __iter__(self):
        def NHIterator():
            for x in tuple(self.raw.values()):
                yield x

        return NHIterator()

    def add(self, prime, raw=None, cascade=False):
        key = self.__make_nh(prime)
        req = key._required
        fields = key._fields
        skey = key[:req] + (None,) * (len(fields) - req)
        if skey in self.raw:
            del self.raw[skey]
        return super(NextHopSet, self).add(key, raw=prime)

    def remove(self, prime, raw=None, cascade=False):
        key = self.__make_nh(prime)
        try:
            super(NextHopSet, self).remove(key)
        except KeyError as e:
            req = key._required
            fields = key._fields
            skey = key[:req] + (None,) * (len(fields) - req)
            for rkey in tuple(self.raw.keys()):
                if skey == rkey[:req] + (None,) * (len(fields) - req):
                    break
            else:
                raise e
            super(NextHopSet, self).remove(rkey)


class WatchdogMPLSKey(dict):
    def __init__(self, route):
        dict.__init__(self)
        self['oif'] = route['oif']
        self['dst'] = [{'ttl': 0, 'bos': 1, 'tc': 0, 'label': route['dst']}]


class WatchdogKey(dict):
    '''
    Construct from a route a dictionary that could be used as
    a match for IPDB watchdogs.
    '''

    def __init__(self, route):
        dict.__init__(
            self,
            [
                x
                for x in RequestProcessor(
                    RouteFieldFilter(), context=route, prime=route
                ).items()
                if x[0]
                in (
                    'dst',
                    'dst_len',
                    'src',
                    'src_len',
                    'tos',
                    'priority',
                    'gateway',
                    'table',
                )
                and x[1]
            ],
        )


# Universal route key
# Holds the fields that the kernel uses to uniquely identify routes.
# IPv4 allows redundant routes with different 'tos' but IPv6 does not,
# so 'tos' is used for IPv4 but not IPv6.
# For reference, see fib_table_insert() in
# https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/ipv4/fib_trie.c#n1147
# and fib6_add_rt2node() in
# https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/ipv6/ip6_fib.c#n765
RouteKey = namedtuple(
    'RouteKey', ('dst', 'table', 'family', 'priority', 'tos')
)

# IP multipath NH key
IPNHKey = namedtuple('IPNHKey', ('gateway', 'encap', 'oif'))
IPNHKey._required = 2

# MPLS multipath NH key
MPLSNHKey = namedtuple('MPLSNHKey', ('newdst', 'via', 'oif'))
MPLSNHKey._required = 2


def _normalize_ipaddr(x, y):
    if isinstance(y, basestring) and y.find(':') > -1:
        y = inet_ntop(AF_INET6, inet_pton(AF_INET6, y))
    return x == y


def _normalize_ipnet(x, y):
    #
    # x -- incoming value
    # y -- transaction value
    #
    if isinstance(y, basestring) and y.find(':') > -1:
        s = y.split('/')
        ip = inet_ntop(AF_INET6, inet_pton(AF_INET6, s[0]))
        if len(s) > 1:
            y = '%s/%s' % (ip, s[1])
        else:
            y = ip
    return x == y


class BaseRoute(Transactional):
    '''
    Persistent transactional route object
    '''

    _fields = [rtmsg.nla2name(i[0]) for i in rtmsg.nla_map]
    for key, _ in rtmsg.fields:
        _fields.append(key)
    _fields.append('removal')
    _virtual_fields = ['ipdb_scope', 'ipdb_priority']
    _fields.extend(_virtual_fields)
    _linked_sets = ['multipath']
    _nested = []
    _gctime = None
    cleanup = ('attrs', 'header', 'event', 'cacheinfo')
    _fields_cmp = {
        'src': _normalize_ipnet,
        'dst': _normalize_ipnet,
        'gateway': _normalize_ipaddr,
        'prefsrc': _normalize_ipaddr,
    }

    def __init__(self, ipdb, mode=None, parent=None, uid=None):
        Transactional.__init__(self, ipdb, mode, parent, uid)
        with self._direct_state:
            self['ipdb_priority'] = 0

    @with_transaction
    def add_nh(self, prime):
        with self._write_lock:
            # if the multipath chain is empty, copy the current
            # nexthop as the first in the multipath
            if not self['multipath']:
                first = {}
                for key in ('oif', 'gateway', 'newdst'):
                    if self[key]:
                        first[key] = self[key]
                if first:
                    if self['family']:
                        first['family'] = self['family']
                    for key in ('encap', 'via', 'metrics'):
                        if self[key] and any(self[key].values()):
                            first[key] = self[key]
                            self[key] = None
                    self['multipath'].add(first)
                    # cleanup key fields
                    for key in ('oif', 'gateway', 'newdst'):
                        self[key] = None
            # add the prime as NH
            if self['family'] == AF_MPLS:
                prime['family'] = AF_MPLS
            self['multipath'].add(prime)

    @with_transaction
    def del_nh(self, prime):
        with self._write_lock:
            if not self['multipath']:
                raise KeyError(
                    'attempt to delete nexthop from ' 'non-multipath route'
                )
            nh = dict(prime)
            if self['family'] == AF_MPLS:
                nh['family'] = AF_MPLS
            self['multipath'].remove(nh)

    def load_netlink(self, msg):
        with self._direct_state:
            if self['ipdb_scope'] == 'locked':
                # do not touch locked interfaces
                return

            self['ipdb_scope'] = 'system'

            # IPv6 multipath via several devices (not networks) is a very
            # special case, since we get only the first hop notification. Ask
            # the kernel guys why. I've got no idea.
            #
            # So load all the rest
            flags = msg.get('header', {}).get('flags', 0)
            family = msg.get('family', 0)
            clean_mp = True
            table = msg.get_attr('RTA_TABLE') or msg.get('table')
            dst = msg.get_attr('RTA_DST')
            #
            # It MAY be a multipath hop
            #
            if family == AF_INET6 and not msg.get_attr('RTA_MULTIPATH'):
                #
                # It is a notification about the route created
                #
                if flags == NLM_F_CREATE:
                    #
                    # This routine can significantly slow down the IPDB
                    # instance, but I see no way around. Some are born
                    # to endless night.
                    #
                    clean_mp = False
                    msgs = self.nl.route(
                        'show', table=table, dst=dst, family=family
                    )
                    for nhmsg in msgs:
                        nh = type(self)(ipdb=self.ipdb, parent=self)
                        nh.load_netlink(nhmsg)
                        with nh._direct_state:
                            del nh['dst']
                            del nh['ipdb_scope']
                            del nh['ipdb_priority']
                            del nh['multipath']
                            del nh['metrics']
                        self.add_nh(nh)
                #
                # it IS a multipath hop loaded during IPDB init
                #
                elif flags == NLM_F_MULTI and self.get('dst'):
                    nh = type(self)(ipdb=self.ipdb, parent=self)
                    nh.load_netlink(msg)
                    with nh._direct_state:
                        del nh['dst']
                        del nh['ipdb_scope']
                        del nh['ipdb_priority']
                        del nh['multipath']
                        del nh['metrics']
                    self.add_nh(nh)
                    return

            for key, value in msg.items():
                self[key] = value

            # cleanup multipath NH
            if clean_mp:
                for nh in self['multipath']:
                    self.del_nh(nh)

            for cell in msg['attrs']:
                #
                # Parse on demand
                #
                norm = rtmsg.nla2name(cell[0])
                if norm in self.cleanup:
                    continue
                value = cell[1]
                # normalize RTAX
                if norm == 'metrics':
                    with self['metrics']._direct_state:
                        for metric in tuple(self['metrics'].keys()):
                            del self['metrics'][metric]
                        for rtax, rtax_value in value['attrs']:
                            rtax_norm = rtmsg.metrics.nla2name(rtax)
                            self['metrics'][rtax_norm] = rtax_value
                elif norm == 'multipath':
                    for record in value:
                        nh = type(self)(ipdb=self.ipdb, parent=self)
                        nh.load_netlink(record)
                        with nh._direct_state:
                            del nh['dst']
                            del nh['ipdb_scope']
                            del nh['ipdb_priority']
                            del nh['multipath']
                            del nh['metrics']
                        self['multipath'].add(nh)
                elif norm == 'encap':
                    with self['encap']._direct_state:
                        # WIP: should support encap_types other than MPLS
                        if value.get_attr('MPLS_IPTUNNEL_DST'):
                            ret = []
                            for dst in value.get_attr('MPLS_IPTUNNEL_DST'):
                                ret.append(str(dst['label']))
                            if ret:
                                self['encap']['labels'] = '/'.join(ret)
                elif norm == 'via':
                    with self['via']._direct_state:
                        self['via'] = value
                elif norm == 'newdst':
                    self['newdst'] = [x['label'] for x in value]
                else:
                    self[norm] = value

            if msg.get('family', 0) == AF_MPLS:
                dst = msg.get_attr('RTA_DST')
                if dst:
                    dst = dst[0]['label']
            else:
                if msg.get_attr('RTA_DST'):
                    dst = '%s/%s' % (msg.get_attr('RTA_DST'), msg['dst_len'])
                else:
                    dst = 'default'
            self['dst'] = dst

            # fix RTA_ENCAP_TYPE if needed
            if msg.get_attr('RTA_ENCAP'):
                if self['encap_type'] is not None:
                    with self['encap']._direct_state:
                        self['encap']['type'] = self['encap_type']
                    self['encap_type'] = None
            # or drop encap, if there is no RTA_ENCAP in msg
            elif self['encap'] is not None:
                self['encap_type'] = None
                with self['encap']._direct_state:
                    self['encap'] = {}

            # drop metrics, if there is no RTA_METRICS in msg
            if not msg.get_attr('RTA_METRICS') and self['metrics'] is not None:
                with self['metrics']._direct_state:
                    self['metrics'] = {}

            # same for via
            if not msg.get_attr('RTA_VIA') and self['via'] is not None:
                with self['via']._direct_state:
                    self['via'] = {}

            # one hop -> multihop transition
            if not msg.get_attr('RTA_GATEWAY') and self['gateway'] is not None:
                self['gateway'] = None
            if (
                'oif' not in msg
                and not msg.get_attr('RTA_OIF')
                and self['oif'] is not None
            ):
                self['oif'] = None

            # finally, cleanup all not needed
            for item in self.cleanup:
                if item in self:
                    del self[item]

    def commit(
        self, tid=None, transaction=None, commit_phase=1, commit_mask=0xFF
    ):
        if not commit_phase & commit_mask:
            return self

        error = None
        drop = self.ipdb.txdrop
        devop = 'set'
        cleanup = []
        # FIXME -- make a debug object
        debug = {'traceback': None, 'next_stage': None}
        notx = True

        if tid or transaction:
            notx = False

        if tid:
            transaction = self.global_tx[tid]
        else:
            transaction = transaction or self.current_tx

        # ignore global rollbacks on invalid routes
        if self['ipdb_scope'] == 'create' and commit_phase > 1:
            return

        # create a new route
        if self['ipdb_scope'] != 'system':
            devop = 'add'

        # work on an existing route
        snapshot = self.pick()
        added, removed = transaction // snapshot
        added.pop('ipdb_scope', None)
        removed.pop('ipdb_scope', None)

        try:
            # route set
            if self['family'] != AF_MPLS:
                cleanup = [
                    any(snapshot['metrics'].values())
                    and not any(added.get('metrics', {}).values()),
                    any(snapshot['encap'].values())
                    and not any(added.get('encap', {}).values()),
                ]
            if (
                any(added.values())
                or any(cleanup)
                or removed.get('multipath', None)
                or devop == 'add'
            ):
                # prepare multipath target sync
                wlist = []
                if transaction['multipath']:
                    mplen = len(transaction['multipath'])
                    if mplen == 1:
                        # set up local targets
                        for nh in transaction['multipath']:
                            for key in ('oif', 'gateway', 'newdst'):
                                if nh.get(key, None):
                                    self.set_target(key, nh[key])
                                    wlist.append(key)
                        mpt = None
                    else:

                        def mpcheck(mpset):
                            return len(mpset) == mplen

                        mpt = self['multipath'].set_target(mpcheck, True)
                else:
                    mpt = None

                # prepare the anchor key to catch *possible* route update
                old_key = self.make_key(self)
                new_key = self.make_key(transaction)
                if old_key != new_key:
                    # assume we can not move routes between tables (yet ;)
                    if self['family'] == AF_MPLS:
                        route_index = self.ipdb.routes.tables['mpls'].idx
                    else:
                        route_index = self.ipdb.routes.tables[
                            self['table'] or 254
                        ].idx
                    # re-link the route record
                    if new_key in route_index:
                        raise CommitException('route idx conflict')
                    else:
                        route_index[new_key] = {'key': new_key, 'route': self}
                    # wipe the old key, if needed
                    if old_key in route_index:
                        del route_index[old_key]
                self.nl.route(devop, **transaction)
                # delete old record, if required
                if (old_key != new_key) and (devop == 'set'):
                    req = dict(old_key._asdict())
                    # update the request with the scope.
                    #
                    # though the scope isn't a part of the
                    # key, it is required for the correct
                    # removal -- only if it is set
                    req['scope'] = self.get('scope', 0)
                    self.nl.route('del', **req)
                transaction.wait_all_targets()
                for key in ('metrics', 'via'):
                    if transaction[key] and transaction[key]._targets:
                        transaction[key].wait_all_targets()
                if mpt is not None:
                    mpt.wait(SYNC_TIMEOUT)
                    if not mpt.is_set():
                        raise CommitException('multipath target is not set')
                    self['multipath'].clear_target(mpt)
                for key in wlist:
                    self.wait_target(key)
            # route removal
            if (transaction['ipdb_scope'] in ('shadow', 'remove')) or (
                (transaction['ipdb_scope'] == 'create') and commit_phase == 2
            ):
                if transaction['ipdb_scope'] == 'shadow':
                    with self._direct_state:
                        self['ipdb_scope'] = 'locked'
                # create watchdog
                wd = self.ipdb.watchdog(
                    'RTM_DELROUTE', **self.wd_key(snapshot)
                )
                for route in self.nl.route('delete', **snapshot):
                    self.ipdb.routes.load_netlink(route)
                wd.wait()
                if transaction['ipdb_scope'] == 'shadow':
                    with self._direct_state:
                        self['ipdb_scope'] = 'shadow'

            # success, so it's safe to drop the transaction
            drop = True

        except Exception as e:
            error = e
            # prepare postmortem
            debug['traceback'] = traceback.format_exc()
            debug['error_stack'] = []
            debug['next_stage'] = None

            if commit_phase == 1:
                try:
                    self.commit(
                        transaction=snapshot,
                        commit_phase=2,
                        commit_mask=commit_mask,
                    )
                except Exception as i_e:
                    debug['next_stage'] = i_e
                    error = RuntimeError()

        if drop and notx:
            self.drop(transaction.uid)

        if error is not None:
            error.debug = debug
            raise error

        self.ipdb.routes.gc()
        return self

    def remove(self):
        self['ipdb_scope'] = 'remove'
        return self

    def shadow(self):
        self['ipdb_scope'] = 'shadow'
        return self

    def detach(self):
        if self.get('family') == AF_MPLS:
            table = 'mpls'
        else:
            table = self.get('table', 254)
        del self.ipdb.routes.tables[table][self.make_key(self)]


class Route(BaseRoute):
    _nested = ['encap', 'metrics']
    wd_key = WatchdogKey

    @classmethod
    def make_encap(cls, encap):
        '''
        Normalize encap object
        '''
        labels = encap.get('labels', None)
        if isinstance(labels, (list, tuple, set)):
            labels = '/'.join(
                map(
                    lambda x: (
                        str(x['label']) if isinstance(x, dict) else str(x)
                    ),
                    labels,
                )
            )
        if not isinstance(labels, basestring):
            raise TypeError('labels struct not supported')
        return {'type': encap.get('type', 'mpls'), 'labels': labels}

    @classmethod
    def make_nh_key(cls, msg):
        '''
        Construct from a netlink message a multipath nexthop key
        '''
        values = []
        if isinstance(msg, nlmsg_base):
            for field in IPNHKey._fields:
                v = msg.get_attr(msg.name2nla(field))
                if field == 'encap':
                    # 1. encap type
                    if msg.get_attr('RTA_ENCAP_TYPE') != 1:  # FIXME
                        values.append(None)
                        continue
                    # 2. encap_type == 'mpls'
                    v = '/'.join(
                        [
                            str(x['label'])
                            for x in v.get_attr('MPLS_IPTUNNEL_DST')
                        ]
                    )
                elif v is None:
                    v = msg.get(field, None)
                values.append(v)
        elif isinstance(msg, dict):
            for field in IPNHKey._fields:
                v = msg.get(field, None)
                if field == 'encap' and v and v['labels']:
                    v = v['labels']
                elif (field == 'encap') and (
                    len(msg.get('multipath', []) or []) == 1
                ):
                    v = (
                        tuple(msg['multipath'].raw.values())[0]
                        .get('encap', {})
                        .get('labels', None)
                    )
                elif field == 'encap':
                    v = None
                elif (
                    (field == 'gateway')
                    and (len(msg.get('multipath', []) or []) == 1)
                    and not v
                ):
                    v = tuple(msg['multipath'].raw.values())[0].get(
                        'gateway', None
                    )

                if field == 'encap' and isinstance(v, (list, tuple, set)):
                    v = '/'.join(
                        map(
                            lambda x: (
                                str(x['label'])
                                if isinstance(x, dict)
                                else str(x)
                            ),
                            v,
                        )
                    )
                values.append(v)
        else:
            raise TypeError('prime not supported: %s' % type(msg))
        return IPNHKey(*values)

    @classmethod
    def make_key(cls, msg):
        '''
        Construct from a netlink message a key that can be used
        to locate the route in the table
        '''
        values = []
        if isinstance(msg, nlmsg_base):
            for field in RouteKey._fields:
                v = msg.get_attr(msg.name2nla(field))
                if field == 'dst':
                    if v is not None:
                        v = '%s/%s' % (v, msg['dst_len'])
                    else:
                        v = 'default'
                elif field == 'tos' and msg.get('family') != AF_INET:
                    # ignore tos field for non-IPv6 routes,
                    # as it used as a key only there
                    v = None
                elif v is None:
                    v = msg.get(field, None)
                values.append(v)
        elif isinstance(msg, dict):
            for field in RouteKey._fields:
                v = msg.get(field, None)
                if (
                    field == 'dst'
                    and isinstance(v, basestring)
                    and v.find(':') > -1
                ):
                    v = v.split('/')
                    ip = inet_ntop(AF_INET6, inet_pton(AF_INET6, v[0]))
                    if len(v) > 1:
                        v = '%s/%s' % (ip, v[1])
                    else:
                        v = ip
                elif field == 'tos' and msg.get('family') != AF_INET:
                    # ignore tos field for non-IPv6 routes,
                    # as it used as a key only there
                    v = None
                values.append(v)
        else:
            raise TypeError('prime not supported: %s' % type(msg))
        return RouteKey(*values)

    def __setitem__(self, key, value):
        ret = value
        if (key in ('encap', 'metrics')) and isinstance(value, dict):
            # transactionals attach as is
            if type(value) in (Encap, Metrics):
                with self._direct_state:
                    return Transactional.__setitem__(self, key, value)

            # check, if it exists already
            ret = Transactional.__getitem__(self, key)
            # it doesn't
            # (plain dict can be safely discarded)
            if isinstance(ret, dict) or not ret:
                # bake transactionals in place
                if key == 'encap':
                    ret = Encap(parent=self)
                elif key == 'metrics':
                    ret = Metrics(parent=self)
                # attach transactional to the route
                with self._direct_state:
                    Transactional.__setitem__(self, key, ret)
                # begin() works only if the transactional is attached
                if any(value.values()):
                    if self._mode in ('implicit', 'explicit'):
                        ret._begin(tid=self.current_tx.uid)
                    [
                        ret.__setitem__(k, v)
                        for k, v in value.items()
                        if v is not None
                    ]
            # corresponding transactional exists
            else:
                # set fields
                for k in ret:
                    ret[k] = value.get(k, None)
            return
        elif key == 'multipath':
            cur = Transactional.__getitem__(self, key)
            if isinstance(cur, NextHopSet):
                # load entries
                vs = NextHopSet(value)
                for key in vs - cur:
                    cur.add(key)
                for key in cur - vs:
                    cur.remove(key)
            else:
                # drop any result of `update()`
                Transactional.__setitem__(self, key, NextHopSet(value))
            return
        elif key == 'encap_type' and not isinstance(value, int):
            ret = encap_type.get(value, value)
        elif key == 'type' and not isinstance(value, int):
            ret = rt_type.get(value, value)
        elif key == 'proto' and not isinstance(value, int):
            ret = rt_proto.get(value, value)
        elif (
            key == 'dst'
            and isinstance(value, basestring)
            and value in ('0.0.0.0/0', '::/0')
        ):
            ret = 'default'
        Transactional.__setitem__(self, key, ret)

    def __getitem__(self, key):
        ret = Transactional.__getitem__(self, key)
        if (key in ('encap', 'metrics', 'multipath')) and (ret is None):
            with self._direct_state:
                self[key] = [] if key == 'multipath' else {}
                ret = self[key]
        return ret


class MPLSRoute(BaseRoute):
    wd_key = WatchdogMPLSKey
    _nested = ['via']

    @classmethod
    def make_nh_key(cls, msg):
        '''
        Construct from a netlink message a multipath nexthop key
        '''
        return MPLSNHKey(
            newdst=tuple(msg['newdst']),
            via=msg.get('via', {}).get('addr', None),
            oif=msg.get('oif', None),
        )

    @classmethod
    def make_key(cls, msg):
        '''
        Construct from a netlink message a key that can be used
        to locate the route in the table
        '''
        ret = None
        if isinstance(msg, nlmsg):
            ret = msg.get_attr('RTA_DST')
        elif isinstance(msg, dict):
            ret = msg.get('dst', None)
        else:
            raise TypeError('prime not supported')
        if isinstance(ret, list):
            ret = ret[0]['label']
        return ret

    def __setitem__(self, key, value):
        if key == 'via' and isinstance(value, dict):
            # replace with a new transactional
            if isinstance(value, Via):
                with self._direct_state:
                    return BaseRoute.__setitem__(self, key, value)
            # or load the dict
            ret = BaseRoute.__getitem__(self, key)
            if not isinstance(ret, Via):
                ret = Via(parent=self)
                # attach new transactional -- replace any
                # non-Via object (may be a result of update())
                with self._direct_state:
                    BaseRoute.__setitem__(self, key, ret)
                # load value into the new object
                if any(value.values()):
                    if self._mode in ('implicit', 'explicit'):
                        ret._begin(tid=self.current_tx.uid)
                    [
                        ret.__setitem__(k, v)
                        for k, v in value.items()
                        if v is not None
                    ]
            else:
                # load value into existing object
                for k in ret:
                    ret[k] = value.get(k, None)
            return
        elif key == 'multipath':
            cur = BaseRoute.__getitem__(self, key)
            if isinstance(cur, NextHopSet):
                # load entries
                vs = NextHopSet(value)
                for key in vs - cur:
                    cur.add(key)
                for key in cur - vs:
                    cur.remove(key)
            else:
                BaseRoute.__setitem__(self, key, NextHopSet(value))
        else:
            BaseRoute.__setitem__(self, key, value)

    def __getitem__(self, key):
        with self._direct_state:
            ret = BaseRoute.__getitem__(self, key)
            if key == 'multipath' and ret is None:
                self[key] = []
                ret = self[key]
            elif key == 'via' and ret is None:
                self[key] = {}
                ret = self[key]
            return ret


class RoutingTable(object):
    route_class = Route

    def __init__(self, ipdb, prime=None):
        self.ipdb = ipdb
        self.lock = threading.Lock()
        self.idx = {}
        self.kdx = {}

    def __nogc__(self):
        return self.filter(lambda x: x['route']['ipdb_scope'] != 'gc')

    def __repr__(self):
        return repr([x['route'] for x in self.__nogc__()])

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        for record in self.__nogc__():
            yield record['route']

    def gc(self):
        now = time.time()
        for route in self.filter({'ipdb_scope': 'gc'}):
            if now - route['route']._gctime < 2:
                continue
            try:
                if not self.ipdb.nl.route('dump', **route['route']):
                    raise
                with route['route']._direct_state:
                    route['route']['ipdb_scope'] = 'system'
            except:
                del self.idx[route['key']]

    def keys(self, key='dst'):
        with self.lock:
            return [x['route'][key] for x in self.__nogc__()]

    def items(self):
        for key in self.keys():
            yield (key, self[key])

    def filter(self, target, oneshot=False):
        #
        if isinstance(target, types.FunctionType):
            return filter(target, [x for x in tuple(self.idx.values())])

        if isinstance(target, basestring):
            target = {'dst': target}

        if not isinstance(target, dict):
            raise TypeError('target type not supported: %s' % type(target))

        ret = []
        for record in tuple(self.idx.values()):
            for key, value in tuple(target.items()):
                if (key not in record['route']) or (
                    value != record['route'][key]
                ):
                    break
            else:
                ret.append(record)
                if oneshot:
                    return ret

        return ret

    def describe(self, target, forward=False):
        # match the route by index -- a bit meaningless,
        # but for compatibility
        if isinstance(target, int):
            keys = [x['key'] for x in self.__nogc__()]
            return self.idx[keys[target]]

        # match the route by key
        if isinstance(target, (tuple, list)):
            # full match
            return self.idx[RouteKey(*target)]

        if isinstance(target, nlmsg):
            return self.idx[Route.make_key(target)]

        # match the route by filter
        ret = self.filter(target, oneshot=True)
        if ret:
            return ret[0]

        if not forward:
            raise KeyError('record not found')

        # match the route by dict spec
        if not isinstance(target, dict):
            raise TypeError('lookups can be done only with dict targets')

        # split masks
        if target.get('dst', '').find('/') >= 0:
            dst = target['dst'].split('/')
            target['dst'] = dst[0]
            target['dst_len'] = int(dst[1])

        if target.get('src', '').find('/') >= 0:
            src = target['src'].split('/')
            target['src'] = src[0]
            target['src_len'] = int(src[1])

        # load and return the route, if exists
        route = Route(self.ipdb)
        ret = self.ipdb.nl.get_routes(**target)
        if not ret:
            raise KeyError('record not found')
        route.load_netlink(ret[0])
        return {'route': route, 'key': None}

    def __delitem__(self, key):
        with self.lock:
            item = self.describe(key, forward=False)
            del self.idx[self.route_class.make_key(item['route'])]

    def load(self, msg):
        key = self.route_class.make_key(msg)
        self[key] = msg
        return key

    def __setitem__(self, key, value):
        with self.lock:
            try:
                record = self.describe(key, forward=False)
            except KeyError:
                record = {'route': self.route_class(self.ipdb), 'key': None}

            if isinstance(value, nlmsg):
                record['route'].load_netlink(value)
            elif isinstance(value, self.route_class):
                record['route'] = value
            elif isinstance(value, dict):
                with record['route']._direct_state:
                    record['route'].update(value)

            key = self.route_class.make_key(record['route'])
            if record['key'] is None:
                self.idx[key] = {'route': record['route'], 'key': key}
            else:
                self.idx[key] = record
                if record['key'] != key:
                    del self.idx[record['key']]
                    record['key'] = key

    def __getitem__(self, key):
        with self.lock:
            return self.describe(key, forward=False)['route']

    def __contains__(self, key):
        try:
            with self.lock:
                self.describe(key, forward=False)
            return True
        except KeyError:
            return False


class MPLSTable(RoutingTable):
    route_class = MPLSRoute

    def keys(self):
        return self.idx.keys()

    def describe(self, target, forward=False):
        # match by key
        if isinstance(target, int):
            return self.idx[target]

        # match by rtmsg
        if isinstance(target, rtmsg):
            return self.idx[self.route_class.make_key(target)]

        raise KeyError('record not found')


class RoutingTableSet(object):
    def __init__(self, ipdb):
        self.ipdb = ipdb
        self._gctime = time.time()
        self.ignore_rtables = ipdb._ignore_rtables or []
        self.tables = {254: RoutingTable(self.ipdb)}
        self._event_map = {
            'RTM_NEWROUTE': self.load_netlink,
            'RTM_DELROUTE': self.load_netlink,
            'RTM_NEWLINK': self.gc_mark_link,
            'RTM_DELLINK': self.gc_mark_link,
            'RTM_DELADDR': self.gc_mark_addr,
        }

    def _register(self):
        for msg in self.ipdb.nl.get_routes(
            family=AF_INET, match={'family': AF_INET}
        ):
            self.load_netlink(msg)
        for msg in self.ipdb.nl.get_routes(
            family=AF_INET6, match={'family': AF_INET6}
        ):
            self.load_netlink(msg)
        for msg in self.ipdb.nl.get_routes(
            family=AF_MPLS, match={'family': AF_MPLS}
        ):
            self.load_netlink(msg)

    def add(self, spec=None, **kwarg):
        '''
        Create a route from a dictionary
        '''
        spec = dict(spec or kwarg)
        gateway = spec.get('gateway') or ''
        dst = spec.get('dst') or ''
        if 'tos' not in spec:
            spec['tos'] = 0
        if 'scope' not in spec:
            spec['scope'] = 0
        if 'table' not in spec:
            spec['table'] = 254
        if 'family' not in spec:
            if (dst.find(':') > -1) or (gateway.find(':') > -1):
                spec['family'] = AF_INET6
            else:
                spec['family'] = AF_INET
        if not dst:
            raise ValueError('dst not specified')
        if (
            isinstance(dst, basestring)
            and (dst not in ('', 'default'))
            and ('/' not in dst)
        ):
            if spec['family'] == AF_INET:
                spec['dst'] = dst + '/32'
            elif spec['family'] == AF_INET6:
                spec['dst'] = dst + '/128'
        if 'priority' not in spec:
            if spec['family'] == AF_INET6:
                spec['priority'] = IP6_RT_PRIO_USER
            else:
                spec['priority'] = None
        multipath = spec.pop('multipath', [])
        if spec.get('family', 0) == AF_MPLS:
            table = 'mpls'
            if table not in self.tables:
                self.tables[table] = MPLSTable(self.ipdb)
            route = MPLSRoute(self.ipdb)
        else:
            table = spec.get('table', 254)
            if table not in self.tables:
                self.tables[table] = RoutingTable(self.ipdb)
            route = Route(self.ipdb)
        route.update(spec)
        with route._direct_state:
            route['ipdb_scope'] = 'create'
            for nh in multipath:
                if 'encap' in nh:
                    nh['encap'] = route.make_encap(nh['encap'])
                if table == 'mpls':
                    nh['family'] = AF_MPLS
                route.add_nh(nh)
        route.begin()
        for key, value in spec.items():
            if key == 'encap':
                route[key] = route.make_encap(value)
            else:
                route[key] = value
        self.tables[table][route.make_key(route)] = route
        return route

    def load_netlink(self, msg):
        '''
        Loads an existing route from a rtmsg
        '''
        if not isinstance(msg, rtmsg):
            return

        if msg['family'] == AF_MPLS:
            table = 'mpls'
        else:
            table = msg.get_attr('RTA_TABLE', msg['table'])

        if table in self.ignore_rtables:
            return

        now = time.time()
        if now - self._gctime > 5:
            self._gctime = now
            self.gc()

        # RTM_DELROUTE
        if msg['event'] == 'RTM_DELROUTE':
            try:
                # locate the record
                record = self.tables[table][msg]
                # delete the record
                if record['ipdb_scope'] not in ('locked', 'shadow'):
                    del self.tables[table][msg]
                    with record._direct_state:
                        record['ipdb_scope'] = 'detached'
            except Exception as e:
                # just ignore this failure for now
                log.debug("delroute failed for %s", e)
            return

        # RTM_NEWROUTE
        if table not in self.tables:
            if table == 'mpls':
                self.tables[table] = MPLSTable(self.ipdb)
            else:
                self.tables[table] = RoutingTable(self.ipdb)
        self.tables[table].load(msg)

    def gc_mark_addr(self, msg):
        ##
        # Find invalid IPv4 route records after addr delete
        #
        # Example::
        #   $ sudo ip link add test0 type dummy
        #   $ sudo ip link set dev test0 up
        #   $ sudo ip addr add 172.18.0.5/24 dev test0
        #   $ sudo ip route add 10.1.2.0/24 via 172.18.0.1
        #   ...
        #   $ sudo ip addr flush dev test0
        #
        # The route {'dst': '10.1.2.0/24', 'gateway': '172.18.0.1'}
        # will stay in the routing table being removed from the system.
        # That's because the kernel doesn't send IPv4 route updates in
        # that case, so we have to calculate the update here -- or load
        # all the routes from scratch. The latter may be far too
        # expensive.
        #
        # See http://www.spinics.net/lists/netdev/msg254186.html for
        # background on this kernel behavior.

        # Simply ignore secondary addresses, as they don't matter
        if msg['flags'] & IFA_F_SECONDARY:
            return

        # When the primary address is removed, corresponding routes
        # may be silently discarded. But if promote_secondaries is set
        # to 1, the next secondary becomes a new primary, and routes
        # stay. There is no way to know here, whether promote_secondaries
        # was set at the moment of the address removal, so we have to
        # act as if it wasn't.

        # Get the removed address:
        family = msg['family']

        if family == AF_INET:
            addr = msg.get_attr('IFA_LOCAL')
            net = struct.unpack('>I', inet_pton(family, addr))[0] & (
                0xFFFFFFFF << (32 - msg['prefixlen'])
            )

            # now iterate all registered routes and mark those with
            # gateway from that network
            for record in self.filter({'family': family}):
                gw = record['route'].get('gateway')
                if gw:
                    gwnet = struct.unpack('>I', inet_pton(family, gw))[0] & net
                    if gwnet == net:
                        with record['route']._direct_state:
                            record['route']['ipdb_scope'] = 'gc'
                            record['route']._gctime = time.time()

        elif family == AF_INET6:
            # Unlike IPv4, IPv6 route updates are sent after addr
            # delete, so no need to delete them here.
            pass
        else:
            # ignore not (IPv4 or IPv6)
            return

    def gc_mark_link(self, msg):
        ###
        # mark route records for GC after link delete
        #
        if msg['family'] != 0 or msg['state'] != 'down':
            return

        for record in self.filter({'oif': msg['index']}):
            with record['route']._direct_state:
                record['route']['ipdb_scope'] = 'gc'
                record['route']._gctime = time.time()
        for record in self.filter({'iif': msg['index']}):
            with record['route']._direct_state:
                record['route']['ipdb_scope'] = 'gc'
                record['route']._gctime = time.time()

    def gc(self):
        for table in self.tables.keys():
            self.tables[table].gc()

    def remove(self, route, table=None):
        if isinstance(route, Route):
            table = route.get('table', 254) or 254
            route = route.get('dst', 'default')
        else:
            table = table or 254
        self.tables[table][route].remove()

    def filter(self, target):
        # FIXME: turn into generator!
        ret = []
        for table in tuple(self.tables.values()):
            if table is not None:
                ret.extend(table.filter(target))
        return ret

    def describe(self, spec, table=254):
        return self.tables[table].describe(spec)

    def get(self, dst, table=None):
        table = table or 254
        return self.tables[table][dst]

    def keys(self, table=254, family=AF_UNSPEC):
        return [
            x['dst']
            for x in self.tables[table]
            if (x.get('family') == family) or (family == AF_UNSPEC)
        ]

    def has_key(self, key, table=254):
        return key in self.tables[table]

    def __contains__(self, key):
        return key in self.tables[254]

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        if key != value['dst']:
            raise ValueError("dst doesn't match key")
        return self.add(value)

    def __delitem__(self, key):
        return self.remove(key)

    def __repr__(self):
        return repr(self.tables[254])


spec = [{'name': 'routes', 'class': RoutingTableSet, 'kwarg': {}}]
