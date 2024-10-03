import errno
import time
import traceback
from socket import AF_INET, AF_INET6
from socket import error as socket_error
from socket import inet_ntop, inet_pton

from pyroute2 import config
from pyroute2.common import Dotkeys, View, basestring, dqn2int
from pyroute2.config import AF_BRIDGE
from pyroute2.ipdb.exceptions import (
    CommitException,
    CreateException,
    PartialCommitException,
)
from pyroute2.ipdb.linkedset import LinkedSet
from pyroute2.ipdb.transactional import (
    SYNC_TIMEOUT,
    Transactional,
    with_transaction,
)
from pyroute2.netlink import rtnl
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.rtnl.ifinfmsg import IFF_MASK, ifinfmsg

supported_kinds = (
    'bridge',
    'bond',
    'tuntap',
    'vxlan',
    'gre',
    'gretap',
    'ip6gre',
    'ip6gretap',
    'macvlan',
    'macvtap',
    'ipvlan',
    'vrf',
    'vti',
)

groups = (
    rtnl.RTMGRP_LINK
    | rtnl.RTMGRP_NEIGH
    | rtnl.RTMGRP_IPV4_IFADDR
    | rtnl.RTMGRP_IPV6_IFADDR
)


def _get_data_fields():
    global supported_kinds

    ret = []
    for data in supported_kinds:
        msg = ifinfmsg.ifinfo.data_map.get(data)
        if msg is not None:
            if getattr(msg, 'prefix', None) is not None:
                ret += [msg.nla2name(i[0]) for i in msg.nla_map]
            else:
                ret += [ifinfmsg.nla2name(i[0]) for i in msg.nla_map]
    return ret


def _br_time_check(x, y):
    return abs(x - y) < 5


class Interface(Transactional):
    '''
    Objects of this class represent network interface and
    all related objects:
    * addresses
    * (todo) neighbours
    * (todo) routes

    Interfaces provide transactional model and can act as
    context managers. Any attribute change implicitly
    starts a transaction. The transaction can be managed
    with three methods:
    * review() -- review changes
    * rollback() -- drop all the changes
    * commit() -- try to apply changes

    If anything will go wrong during transaction commit,
    it will be rolled back authomatically and an
    exception will be raised. Failed transaction review
    will be attached to the exception.
    '''

    _fields_cmp = {
        'flags': lambda x, y: x & y & IFF_MASK == y & IFF_MASK,
        'br_hello_time': _br_time_check,
        'br_max_age': _br_time_check,
        'br_ageing_time': _br_time_check,
        'br_forward_delay': _br_time_check,
        'br_mcast_membership_intvl': _br_time_check,
        'br_mcast_querier_intvl': _br_time_check,
        'br_mcast_query_intvl': _br_time_check,
        'br_mcast_query_response_intvl': _br_time_check,
        'br_mcast_startup_query_intvl': _br_time_check,
    }
    _virtual_fields = [
        'ipdb_scope',
        'ipdb_priority',
        'vlans',
        'ipaddr',
        'ports',
        'vlan_flags',
        'net_ns_fd',
        'net_ns_pid',
    ]
    _fields = [ifinfmsg.nla2name(i[0]) for i in ifinfmsg.nla_map]
    for name in ('bridge_slave_data',):
        data = getattr(ifinfmsg.ifinfo, name)
        _fields.extend([ifinfmsg.nla2name(i[0]) for i in data.nla_map])
    _fields.append('index')
    _fields.append('flags')
    _fields.append('mask')
    _fields.append('change')
    _fields.append('kind')
    _fields.append('peer')
    _fields.append('vlan_id')
    _fields.append('vlan_protocol')
    _fields.append('bond_mode')
    _fields.extend(_get_data_fields())
    _fields.extend(_virtual_fields)

    def __init__(self, ipdb, mode=None, parent=None, uid=None):
        '''
        Parameters:
        * ipdb -- ipdb() reference
        * mode -- transaction mode
        '''
        Transactional.__init__(self, ipdb, mode)
        self.cleanup = (
            'header',
            'linkinfo',
            'protinfo',
            'af_spec',
            'attrs',
            'event',
            'map',
            'stats',
            'stats64',
            'change',
            '__align',
        )
        self.ingress = None
        self.egress = None
        self.nlmsg = None
        self.errors = []
        self.partial = False
        self._exception = None
        self._deferred_link = None
        self._tb = None
        self._linked_sets.add('ipaddr')
        self._linked_sets.add('ports')
        self._linked_sets.add('vlans')
        self._freeze = None
        self._delay_add_port = set()
        self._delay_del_port = set()
        # 8<-----------------------------------
        # local setup: direct state is required
        with self._direct_state:
            for i in ('change', 'mask'):
                del self[i]
            self['ipaddr'] = self.ipdb._ipaddr_set()
            self['ports'] = LinkedSet()
            self['vlans'] = LinkedSet()
            self['ipdb_priority'] = 0
        # 8<-----------------------------------

    def __hash__(self):
        return self['index']

    @property
    def if_master(self):
        '''
        [property] Link to the parent interface -- if it exists
        '''
        return self.get('master', None)

    def detach(self):
        self.ipdb.interfaces._detach(self['ifname'], self['index'], self.nlmsg)
        return self

    def freeze(self):
        if self._freeze is not None:
            raise RuntimeError("the interface is frozen already")

        dump = self.pick()

        def cb(ipdb, msg, action):
            if msg.get('index', -1) == dump['index']:
                try:
                    # important: that's a rollback, so do not
                    # try to revert changes in the case of failure
                    self.commit(
                        transaction=dump, commit_phase=2, commit_mask=2
                    )
                except Exception:
                    pass

        self._freeze = self.ipdb.register_callback(cb)
        return self

    def unfreeze(self):
        self.ipdb.unregister_callback(self._freeze)
        self._freeze = None
        return self

    def load(self, data):
        '''
        Load the data from a dictionary to an existing
        transaction. Requires `commit()` call, or must be
        called from within a `with` statement.

        Sample::

            data = json.loads(...)
            with ipdb.interfaces['dummy1'] as i:
                i.load(data)

        Sample, mode `explicit::

            data = json.loads(...)
            i = ipdb.interfaces['dummy1']
            i.begin()
            i.load(data)
            i.commit()
        '''
        for key in data:
            if data[key] is None:
                continue
            if key == 'ipaddr':
                for addr in self['ipaddr']:
                    self.del_ip(*addr)
                for addr in data[key]:
                    if isinstance(addr, basestring):
                        addr = (addr,)
                    self.add_ip(*addr)
            elif key == 'ports':
                for port in self['ports']:
                    self.del_port(port)
                for port in data[key]:
                    self.add_port(port)
            elif key == 'vlans':
                for vlan in self['vlans']:
                    self.del_vlan(vlan)
                for vlan in data[key]:
                    if vlan != 1:
                        self.add_vlan(vlan)
            elif key in ('neighbours', 'family'):
                # ignore on load
                pass
            else:
                self[key] = data[key]
        return self

    def load_dict(self, data):
        '''
        Update the interface info from a dictionary.

        This call always bypasses open transactions, loading
        changes directly into the interface data.
        '''
        with self._direct_state:
            self.load(data)

    def load_netlink(self, dev):
        '''
        Update the interface info from RTM_NEWLINK message.

        This call always bypasses open transactions, loading
        changes directly into the interface data.
        '''
        global supported_kinds

        with self._direct_state:
            if self['ipdb_scope'] == 'locked':
                # do not touch locked interfaces
                return

            if self['ipdb_scope'] in ('shadow', 'create'):
                # ignore non-broadcast messages
                if dev['header']['sequence_number'] != 0:
                    return
                # ignore ghost RTM_NEWLINK messages
                if (config.kernel[0] < 3) and (
                    not dev.get_attr('IFLA_AF_SPEC')
                ):
                    return

            for name, value in dev.items():
                self[name] = value
            for cell in dev['attrs']:
                #
                # Parse on demand
                #
                # At that moment, being not referenced, the
                # NLA is not decoded (yet). Calling
                # `__getitem__()` on nla_slot triggers the
                # NLA decoding, if the nla is referenced:
                #
                norm = ifinfmsg.nla2name(cell[0])
                if norm not in self.cleanup:
                    self[norm] = cell[1]
            # load interface kind
            linkinfo = dev.get_attr('IFLA_LINKINFO')
            if linkinfo is not None:
                kind = linkinfo.get_attr('IFLA_INFO_KIND')
                if kind is not None:
                    self['kind'] = kind
                    if kind == 'vlan':
                        data = linkinfo.get_attr('IFLA_INFO_DATA')
                        self['vlan_id'] = data.get_attr('IFLA_VLAN_ID')
                        self['vlan_protocol'] = data.get_attr(
                            'IFLA_VLAN_PROTOCOL'
                        )
                        self['vlan_flags'] = data.get_attr(
                            'IFLA_VLAN_FLAGS', {}
                        ).get('flags', 0)
                    if kind in supported_kinds:
                        data = linkinfo.get_attr('IFLA_INFO_DATA') or {}
                        for nla in data.get('attrs', []):
                            norm = ifinfmsg.nla2name(nla[0])
                            self[norm] = nla[1]
            # load vlans
            if dev['family'] == AF_BRIDGE:
                spec = dev.get_attr('IFLA_AF_SPEC')
                if spec is not None:
                    vlans = spec.get_attrs('IFLA_BRIDGE_VLAN_INFO')
                    vmap = {}
                    for vlan in vlans:
                        vmap[vlan['vid']] = vlan
                    vids = set(vmap.keys())
                    # remove vids we do not have anymore
                    for vid in self['vlans'] - vids:
                        self.del_vlan(vid)
                    for vid in vids - self['vlans']:
                        self.add_vlan(vmap[vid])
                protinfo = dev.get_attr('IFLA_PROTINFO')
                if protinfo is not None:
                    for attr, value in protinfo['attrs']:
                        attr = attr[5:].lower()
                        self[attr] = value
            # the rest is possible only when interface
            # is used in IPDB, not standalone
            if self.ipdb is not None:
                self['ipaddr'] = self.ipdb.ipaddr[self['index']]
                self['neighbours'] = self.ipdb.neighbours[self['index']]
            # finally, cleanup all not needed
            for item in self.cleanup:
                if item in self:
                    del self[item]

            # AF_BRIDGE messages for bridges contain
            # IFLA_MASTER == self.index, we should fix it
            if self.get('master', None) == self['index']:
                self['master'] = None

            self['ipdb_scope'] = 'system'

    def wait_ip(self, *argv, **kwarg):
        return self['ipaddr'].wait_ip(*argv, **kwarg)

    @with_transaction
    def add_ip(self, ip, mask=None, broadcast=None, anycast=None, scope=None):
        '''
        Add IP address to an interface

        Address formats:

            with ipdb.interfaces.eth0 as i:
                i.add_ip('192.168.0.1', 24)
                i.add_ip('192.168.0.2/24')
                i.add_ip('192.168.0.3/255.255.255.0')
                i.add_ip('192.168.0.4/24',
                         broadcast='192.168.0.255',
                         scope=254)
        '''
        family = 0
        # split mask
        if mask is None:
            ip, mask = ip.split('/')

        if ip.find(':') > -1:
            family = AF_INET6
            # normalize IPv6 format
            ip = inet_ntop(AF_INET6, inet_pton(AF_INET6, ip))
        else:
            family = AF_INET

        if isinstance(mask, basestring):
            try:
                mask = int(mask, 0)
            except:
                mask = dqn2int(mask, family)

        # if it is a transaction or an interface update, apply the change
        self['ipaddr'].unlink((ip, mask))
        request = {}
        if broadcast is not None:
            request['broadcast'] = broadcast
        if anycast is not None:
            request['anycast'] = anycast
        if scope is not None:
            request['scope'] = scope
        self['ipaddr'].add((ip, mask), raw=request)

    @with_transaction
    def del_ip(self, ip, mask=None):
        '''
        Delete IP address from an interface
        '''
        if mask is None:
            ip, mask = ip.split('/')
            if mask.find('.') > -1:
                mask = dqn2int(mask)
            else:
                mask = int(mask, 0)
        # normalize the address
        if ip.find(':') > -1:
            ip = inet_ntop(AF_INET6, inet_pton(AF_INET6, ip))
        if (ip, mask) in self['ipaddr']:
            self['ipaddr'].unlink((ip, mask))
            self['ipaddr'].remove((ip, mask))

    @with_transaction
    def add_vlan(self, vlan, flags=None):
        if isinstance(vlan, dict):
            vid = vlan['vid']
        else:
            vid = vlan
            vlan = {'vid': vlan, 'flags': 0}
        self['vlans'].unlink(vid)
        self['vlans'].add(vid, raw=(vlan, flags))

    @with_transaction
    def del_vlan(self, vlan):
        if vlan in self['vlans']:
            self['vlans'].unlink(vlan)
            self['vlans'].remove(vlan)

    @with_transaction
    def add_port(self, port):
        '''
        Add port to a bridge or bonding
        '''
        ifindex = self._resolve_port(port)
        if not ifindex:
            self._delay_add_port.add(port)
        else:
            self['ports'].unlink(ifindex)
            self['ports'].add(ifindex)

    @with_transaction
    def del_port(self, port):
        '''
        Remove port from a bridge or bonding
        '''
        ifindex = self._resolve_port(port)
        if not ifindex:
            self._delay_del_port.add(port)
        else:
            self['ports'].unlink(ifindex)
            self['ports'].remove(ifindex)

    def reload(self):
        '''
        Reload interface information
        '''
        countdown = 3
        while countdown:
            links = self.nl.get_links(self['index'])
            if links:
                self.load_netlink(links[0])
                break
            else:
                countdown -= 1
                time.sleep(1)
        return self

    def review(self):
        ret = super(Interface, self).review()
        last = self.current_tx
        if self['ipdb_scope'] == 'create':
            ret['+ipaddr'] = last['ipaddr']
            ret['+ports'] = last['ports']
            ret['+vlans'] = last['vlans']
            del ret['ports']
            del ret['ipaddr']
            del ret['vlans']
        if last._delay_add_port:
            ports = set(['*%s' % x for x in last._delay_add_port])
            if '+ports' in ret:
                ret['+ports'] |= ports
            else:
                ret['+ports'] = ports
        if last._delay_del_port:
            ports = set(['*%s' % x for x in last._delay_del_port])
            if '-ports' in ret:
                ret['-ports'] |= ports
            else:
                ret['-ports'] = ports
        return ret

    def _run(self, cmd, *argv, **kwarg):
        try:
            return cmd(*argv, **kwarg)
        except Exception as error:
            if self.partial:
                self.errors.append(error)
                return []
            raise error

    def _resolve_port(self, port):
        # for now just a stupid resolver, will be
        # improved later with search by mac, etc.
        if isinstance(port, Interface):
            return port['index']
        else:
            return self.ipdb.interfaces.get(port, {}).get('index', None)

    def commit(
        self,
        tid=None,
        transaction=None,
        commit_phase=1,
        commit_mask=0xFF,
        newif=False,
    ):
        '''
        Commit transaction. In the case of exception all
        changes applied during commit will be reverted.
        '''

        if not commit_phase & commit_mask:
            return self

        error = None
        added = None
        removed = None
        drop = self.ipdb.txdrop
        notx = True

        init = None
        debug = {'traceback': None, 'transaction': None, 'next_stage': None}

        if tid or transaction:
            notx = False

        if tid:
            transaction = self.global_tx[tid]
        else:
            transaction = transaction or self.current_tx

        if transaction.partial:
            transaction.errors = []

        with self._write_lock:
            # if the interface does not exist, create it first ;)
            if self['ipdb_scope'] != 'system':
                # a special case: transition "create" -> "remove"
                if (
                    transaction['ipdb_scope'] == 'remove'
                    and self['ipdb_scope'] == 'create'
                ):
                    self.invalidate()
                    return self

                newif = True
                self.set_target('ipdb_scope', 'system')
                try:
                    # 8<---------------------------------------------------
                    # link resolve
                    if self._deferred_link:
                        link_key, link_obj = self._deferred_link
                        transaction[link_key] = self._resolve_port(link_obj)
                        self._deferred_link = None

                    # 8<----------------------------------------------------
                    # ACHTUNG: hack for old platforms
                    if self['address'] == '00:00:00:00:00:00':
                        with self._direct_state:
                            self['address'] = None
                            self['broadcast'] = None
                    # 8<----------------------------------------------------
                    init = self.pick()
                    try:
                        request = {
                            key: transaction[key]
                            for key in filter(
                                lambda x: x[:5] != 'bond_'
                                and x[:7] != 'brport_'
                                and x[:3] != 'br_',
                                transaction,
                            )
                            if transaction[key] is not None
                        }
                        for key in ('net_ns_fd', 'net_ns_pid'):
                            if key in request:
                                with self._direct_state:
                                    self[key] = None
                                    del request[key]
                        self.nl.link('add', **request)
                    except NetlinkError as x:
                        # File exists
                        if x.code == errno.EEXIST:
                            # A bit special case, could be one of two cases:
                            #
                            # 1. A race condition between two different IPDB
                            #    processes
                            # 2. An attempt to create dummy0, gre0, bond0 when
                            #    the corrseponding module is not loaded. Being
                            #    loaded, the module creates a default interface
                            #    by itself, causing the request to fail
                            #
                            # The exception in that case can cause the DB
                            # inconsistence, since there can be queued not only
                            # the interface creation, but also IP address
                            # changes etc.
                            #
                            # So we ignore this particular exception and try to
                            # continue, as it is created by us.
                            #
                            # 3. An attempt to create VLAN or VXLAN interface
                            #    with the same ID but under different name
                            #
                            # In that case we should forward error properly
                            if self['kind'] in ('vlan', 'vxlan'):
                                newif = x

                        else:
                            raise
                except Exception as e:
                    if transaction.partial:
                        transaction.errors.append(e)
                        raise PartialCommitException()
                    else:
                        # If link('add', ...) raises an exception, no netlink
                        # broadcast will be sent, and the object is unmodified.
                        # After the exception forwarding, the object is ready
                        # to repeat the commit() call.
                        if drop and notx:
                            self.drop(transaction.uid)
                        raise

        if transaction['ipdb_scope'] == 'create' and commit_phase > 1:
            if self['index']:
                wd = self.ipdb.watchdog('RTM_DELLINK', ifname=self['ifname'])
                with self._direct_state:
                    self['ipdb_scope'] = 'locked'
                self.nl.link('delete', index=self['index'])
                wd.wait()
            self.load_dict(transaction)
            return self

        elif newif:
            # Here we come only if a new interface is created
            #
            if commit_phase == 1 and not self.wait_target('ipdb_scope'):
                if drop and notx:
                    self.drop(transaction.uid)
                self.invalidate()
                if isinstance(newif, Exception):
                    raise newif
                else:
                    raise CreateException()

            # Re-populate transaction.ipaddr to have a proper IP target
            #
            # The reason behind the code is that a new interface in the
            # "up" state will have automatic IPv6 addresses, that aren't
            # reflected in the transaction. This may cause a false IP
            # target mismatch and a commit failure.
            #
            # To avoid that, collect automatic addresses to the
            # transaction manually, since it is not yet properly linked.
            #
            for addr in self.ipdb.ipaddr[self['index']]:
                transaction['ipaddr'].add(addr)

            # Reload the interface data
            try:
                self.load_netlink(self.nl.link('get', **request)[0])
            except Exception:
                pass

        # now we have our index and IP set and all other stuff
        snapshot = self.pick()

        # make snapshots of all dependent routes
        if commit_phase == 1 and hasattr(self.ipdb, 'routes'):
            self.routes = []
            for record in self.ipdb.routes.filter({'oif': self['index']}):
                # For MPLS routes the key is an integer
                # They should match anyways
                if getattr(record['key'], 'table', None) != 255:
                    self.routes.append(
                        (record['route'], record['route'].pick())
                    )

        # resolve all delayed ports
        def resolve_ports(transaction, ports, callback, self, drop):
            def error(x):
                return KeyError('can not resolve port %s' % x)

            for port in tuple(ports):
                ifindex = self._resolve_port(port)
                if not ifindex:
                    if transaction.partial:
                        transaction.errors.append(error(port))
                    else:
                        if drop:
                            self.drop(transaction.uid)
                        raise error(port)
                else:
                    ports.remove(port)
                    with transaction._direct_state:  # ????
                        callback(ifindex)

        resolve_ports(
            transaction,
            transaction._delay_add_port,
            transaction.add_port,
            self,
            drop and notx,
        )
        resolve_ports(
            transaction,
            transaction._delay_del_port,
            transaction.del_port,
            self,
            drop and notx,
        )

        try:
            removed, added = snapshot // transaction

            run = transaction._run
            nl = transaction.nl

            # 8<---------------------------------------------
            # Port vlans
            if removed['vlans'] or added['vlans']:
                self['vlans'].set_target(transaction['vlans'])

                for i in removed['vlans']:
                    # remove vlan from the port
                    run(
                        nl.vlan_filter,
                        'del',
                        index=self['index'],
                        vlan_info=self['vlans'][i][0],
                    )

                for i in added['vlans']:
                    # add vlan to the port
                    vinfo = transaction['vlans'][i][0]
                    flags = transaction['vlans'][i][1]
                    req = {'index': self['index'], 'vlan_info': vinfo}
                    if flags == 'self':
                        req['vlan_flags'] = flags
                        # this request will NOT give echo,
                        # so bypass the check
                        with self._direct_state:
                            self.add_vlan(vinfo['vid'])
                    run(nl.vlan_filter, 'add', **req)

                self['vlans'].target.wait(SYNC_TIMEOUT)
                if not self['vlans'].target.is_set():
                    raise CommitException('vlans target is not set')

            # 8<---------------------------------------------
            # Ports
            if removed['ports'] or added['ports']:
                self['ports'].set_target(transaction['ports'])

                for i in removed['ports']:
                    # detach port
                    if i in self.ipdb.interfaces:
                        (
                            self.ipdb.interfaces[i]
                            .set_target('master', None)
                            .mirror_target('master', 'link')
                        )
                        run(nl.link, 'update', index=i, master=0)
                    else:
                        transaction.errors.append(KeyError(i))

                for i in added['ports']:
                    # attach port
                    if i in self.ipdb.interfaces:
                        (
                            self.ipdb.interfaces[i]
                            .set_target('master', self['index'])
                            .mirror_target('master', 'link')
                        )
                        run(nl.link, 'update', index=i, master=self['index'])
                    else:
                        transaction.errors.append(KeyError(i))

                self['ports'].target.wait(SYNC_TIMEOUT)
                if self['ports'].target.is_set():
                    for msg in self.nl.get_vlans(index=self['index']):
                        self.load_netlink(msg)
                else:
                    raise CommitException('ports target is not set')

                # 1. wait for proper targets on ports
                # 2. wait for mtu sync
                #
                # the bridge mtu is set from the port, if the latter is smaller
                # the bond mtu sets the port mtu, if the latter is smaller
                #
                # FIXME: team interfaces?
                for i in list(added['ports']) + list(removed['ports']):
                    port = self.ipdb.interfaces[i]
                    # port update
                    target = port._local_targets['master']
                    target.wait(SYNC_TIMEOUT)
                    with port._write_lock:
                        del port._local_targets['master']
                        del port._local_targets['link']
                    if not target.is_set():
                        raise CommitException('master target failed')
                    if i in added['ports']:
                        if port.if_master != self['index']:
                            raise CommitException('master set failed')
                    else:
                        if port.if_master == self['index']:
                            raise CommitException('master unset failed')
                    # master update
                    if self['kind'] == 'bridge' and self['mtu'] > port['mtu']:
                        self.set_target('mtu', port['mtu'])
                        self.wait_target('mtu')

            # 8<---------------------------------------------
            # Interface changes
            request = {}
            brequest = {}
            prequest = {}
            # preseed requests with the interface kind
            request['kind'] = self['kind']
            brequest['kind'] = self['kind']
            wait_all = False
            for key, value in added.items():
                if (
                    value is not None
                    and (key not in self._virtual_fields)
                    and (key != 'kind')
                ):
                    if key[:3] == 'br_':
                        brequest[key] = added[key]
                    elif key[:7] == 'brport_':
                        prequest[key[7:]] = added[key]
                    else:
                        if key == 'address' and added[key] is not None:
                            self[key] = added[key].lower()
                        request[key] = added[key]
            # FIXME: flush the interface type so the next two conditions
            # will work correctly
            request['kind'] = None
            brequest['kind'] = None

            # apply changes only if there is something to apply
            if (self['kind'] == 'bridge') and any(
                [brequest[item] is not None for item in brequest]
            ):
                brequest['index'] = self['index']
                brequest['kind'] = self['kind']
                brequest['family'] = AF_BRIDGE
                wait_all = True
                run(nl.link, 'set', **brequest)

            if any([request[item] is not None for item in request]):
                request['index'] = self['index']
                request['kind'] = self['kind']
                if request.get('address', None) == '00:00:00:00:00:00':
                    request.pop('address')
                    request.pop('broadcast', None)
                wait_all = True
                run(nl.link, 'update', **request)
                # Yet another trick: setting ifalias doesn't cause
                # netlink updates
                if 'ifalias' in request:
                    self.reload()

            if any([prequest[item] is not None for item in prequest]):
                prequest['index'] = self['index']
                run(nl.brport, 'set', **prequest)

            if (wait_all) and (not transaction.partial):
                transaction.wait_all_targets()

            # 8<---------------------------------------------
            # VLAN flags -- a dirty hack, pls do something with it
            if added.get('vlan_flags') is not None:
                run(
                    nl.link,
                    'set',
                    **{
                        'kind': 'vlan',
                        'index': self['index'],
                        'vlan_flags': added['vlan_flags'],
                    }
                )

            # 8<---------------------------------------------
            # IP address changes
            for _ in range(3):
                ip2add = transaction['ipaddr'] - self['ipaddr']
                ip2remove = self['ipaddr'] - transaction['ipaddr']

                if not ip2add and not ip2remove:
                    break

                self['ipaddr'].set_target(transaction['ipaddr'])
                ###
                # Remove
                #
                # The promote_secondaries sysctl causes the kernel
                # to add secondary addresses back after the primary
                # address is removed.
                #
                # The library can not tell this from the result of
                # an external program.
                #
                # One simple way to work that around is to remove
                # secondaries first.
                rip = sorted(
                    ip2remove,
                    key=lambda x: self['ipaddr'][x]['flags'],
                    reverse=True,
                )
                # 8<--------------------------------------
                for i in rip:
                    # When you remove a primary IP addr, all the
                    # subnetwork can be removed. In this case you
                    # will fail, but it is OK, no need to roll back
                    try:
                        run(
                            nl.addr,
                            'delete',
                            index=self['index'],
                            address=i[0],
                            prefixlen=i[1],
                        )
                    except NetlinkError as x:
                        # bypass only errno 99,
                        # 'Cannot assign address'
                        if x.code != errno.EADDRNOTAVAIL:
                            raise
                    except socket_error as x:
                        # bypass illegal IP requests
                        if isinstance(x.args[0], basestring) and x.args[
                            0
                        ].startswith('illegal IP'):
                            continue
                        raise
                ###
                # Add addresses
                # 8<--------------------------------------
                for i in ip2add:
                    # Try to fetch additional address attributes
                    try:
                        kwarg = dict(
                            [
                                k
                                for k in transaction['ipaddr'][i].items()
                                if k[0] in ('broadcast', 'anycast', 'scope')
                            ]
                        )
                    except KeyError:
                        kwarg = None
                    try:
                        # feed the address to the OS
                        kwarg = kwarg or {}
                        kwarg['index'] = self['index']
                        kwarg['address'] = i[0]
                        kwarg['prefixlen'] = i[1]
                        run(nl.addr, 'add', **kwarg)
                    except NetlinkError as x:
                        if x.code != errno.EEXIST:
                            raise

                # 8<--------------------------------------
                # some interfaces do not send IPv6 address
                # updates, when are down
                #
                # beside of that, bridge interfaces are
                # down by default, so they never send
                # address updates from beginning
                #
                # FIXME:
                #
                # that all is a dirtiest hack ever, pls do
                # something with it
                #
                if (not self['flags'] & 1) or hasattr(self.ipdb.nl, 'netns'):
                    # 1. flush old IPv6 addresses
                    for addr in list(self['ipaddr'].ipv6):
                        self['ipaddr'].remove(addr)
                    # 2. reload addresses
                    for addr in self.nl.get_addr(
                        index=self['index'], family=AF_INET6
                    ):
                        self.ipdb.ipaddr._new(addr)
                    # if there are tons of IPv6 addresses, it may take a
                    # really long time, and that's bad, but it's broken in
                    # the kernel :|

                # 8<--------------------------------------
                self['ipaddr'].target.wait(SYNC_TIMEOUT)
                if self['ipaddr'].target.is_set():
                    break
            else:
                raise CommitException('ipaddr target is not set')

            # 8<---------------------------------------------
            # Iterate callback chain
            for ch in self._commit_hooks:
                # An exception will rollback the transaction
                ch(self.dump(), snapshot.dump(), transaction.dump())

            # 8<---------------------------------------------
            # Move the interface to a netns
            if ('net_ns_fd' in added) or ('net_ns_pid' in added):
                request = {}
                for key in ('net_ns_fd', 'net_ns_pid'):
                    if key in added:
                        request[key] = added[key]

                request['index'] = self['index']
                run(nl.link, 'update', **request)

                countdown = 10
                while countdown:
                    # wait until the interface will disappear
                    # from the current network namespace --
                    # up to 1 second (make it configurable?)
                    try:
                        self.nl.get_links(self['index'])
                    except NetlinkError as e:
                        if e.code == errno.ENODEV:
                            break
                        raise
                    except Exception:
                        raise
                    countdown -= 1
                    time.sleep(0.1)

            # 8<---------------------------------------------
            # Interface removal
            if added.get('ipdb_scope') in ('shadow', 'remove'):
                wd = self.ipdb.watchdog('RTM_DELLINK', ifname=self['ifname'])
                with self._direct_state:
                    self['ipdb_scope'] = 'locked'
                self.nl.link('delete', index=self['index'])
                wd.wait()

                with self._direct_state:
                    self['ipdb_scope'] = 'shadow'

                # system-wide checks
                if commit_phase == 1:
                    self.ipdb.ensure('run')

                if added.get('ipdb_scope') == 'remove':
                    self.ipdb.interfaces._detach(None, self['index'], None)

                if notx:
                    self.drop(transaction.uid)

                return self
            # 8<---------------------------------------------

            # system-wide checks
            if commit_phase == 1:
                self.ipdb.ensure('run')

            # so far all's ok
            drop = True

        except Exception as e:
            error = e
            # log the error environment
            debug['traceback'] = traceback.format_exc()
            debug['transaction'] = transaction
            debug['next_stage'] = None

            # something went wrong: roll the transaction back
            if commit_phase == 1:
                if newif:
                    drop = False
                try:
                    self.commit(
                        transaction=init if newif else snapshot,
                        commit_phase=2,
                        commit_mask=commit_mask,
                        newif=newif,
                    )

                except Exception as i_e:
                    debug['next_stage'] = i_e
                    error = RuntimeError()
            else:
                # reload all the database -- it can take a long time,
                # but it is required since we have no idea, what is
                # the result of the failure
                links = self.nl.get_links()
                for link in links:
                    self.ipdb.interfaces._new(link)
                links = self.nl.get_vlans()
                for link in links:
                    self.ipdb.interfaces._new(link)
                for addr in self.nl.get_addr():
                    self.ipdb.ipaddr._new(addr)

            for key in ('ipaddr', 'ports', 'vlans'):
                self[key].clear_target()

        # raise partial commit exceptions
        if transaction.partial and transaction.errors:
            error = PartialCommitException('partial commit error')

        # drop only if required
        if drop and notx:
            # drop last transaction in any case
            self.drop(transaction.uid)

        # raise exception for failed transaction
        if error is not None:
            error.debug = debug
            raise error

        # restore dependent routes for successful rollback
        if commit_phase == 2:
            for route in self.routes:
                with route[0]._direct_state:
                    route[0]['ipdb_scope'] = 'restore'
                try:
                    route[0].commit(
                        transaction=route[1], commit_phase=2, commit_mask=2
                    )
                except RuntimeError as x:
                    # RuntimeError is raised due to phase 2, so
                    # an additional check is required
                    if (
                        isinstance(x.cause, NetlinkError)
                        and x.cause.code == errno.EEXIST
                    ):
                        pass

        time.sleep(config.commit_barrier)

        # drop all collected errors, if any
        self.errors = []
        return self

    def up(self):
        '''
        Shortcut: change the interface state to 'up'.
        '''
        self['state'] = 'up'
        return self

    def down(self):
        '''
        Shortcut: change the interface state to 'down'.
        '''
        self['state'] = 'down'
        return self

    def remove(self):
        '''
        Mark the interface for removal
        '''
        self['ipdb_scope'] = 'remove'
        return self

    def shadow(self):
        '''
        Remove the interface from the OS, but leave it in the
        database. When one will try to re-create interface with
        the same name, all the old saved attributes will apply
        to the new interface, incl. MAC-address and even the
        interface index. Please be aware, that the interface
        index can be reused by OS while the interface is "in the
        shadow state", in this case re-creation will fail.
        '''
        self['ipdb_scope'] = 'shadow'
        return self


class InterfacesDict(Dotkeys):
    def __init__(self, ipdb):
        self.ipdb = ipdb
        self._event_map = {'RTM_NEWLINK': self._new, 'RTM_DELLINK': self._del}

    def _register(self):
        links = self.ipdb.nl.get_links()
        # iterate twice to map port/master relations
        for link in links:
            self._new(link, skip_master=True)
        for link in links:
            self._new(link)
        # load bridge vlan information
        links = self.ipdb.nl.get_vlans()
        for link in links:
            self._new(link)

    def add(self, kind, ifname, reuse=False, **kwarg):
        '''
        Create new network interface
        '''
        with self.ipdb.exclusive:
            # check for existing interface
            if ifname in self:
                if (self[ifname]['ipdb_scope'] == 'shadow') or reuse:
                    device = self[ifname]
                    kwarg['kind'] = kind
                    device.load_dict(kwarg)
                    if self[ifname]['ipdb_scope'] == 'shadow':
                        with device._direct_state:
                            device['ipdb_scope'] = 'create'
                    device.begin()
                else:
                    raise CreateException("interface %s exists" % ifname)
            else:
                device = self[ifname] = Interface(
                    ipdb=self.ipdb, mode='snapshot'
                )
                # delay link resolve?
                for key in kwarg:
                    # any /.+link$/ attr
                    if key[-4:] == 'link':
                        if isinstance(kwarg[key], Interface):
                            kwarg[key] = kwarg[key].get('index') or kwarg[
                                key
                            ].get('ifname')
                        if not isinstance(kwarg[key], int):
                            device._deferred_link = (key, kwarg[key])
                device._mode = self.ipdb.mode
                with device._direct_state:
                    device['kind'] = kind
                    device['index'] = kwarg.get('index', 0)
                    device['ifname'] = ifname
                    device['ipdb_scope'] = 'create'
                    # set some specific attrs
                    for attr in (
                        'peer',
                        'uid',
                        'gid',
                        'ifr',
                        'mode',
                        'bond_mode',
                        'address',
                    ):
                        if attr in kwarg:
                            device[attr] = kwarg.pop(attr)
                device.begin()
                device.load(kwarg)
        return device

    def _del(self, msg):
        target = self.get(msg['index'])
        if target is None:
            return

        if msg['family'] == AF_BRIDGE:
            with target._direct_state:
                for vlan in tuple(target['vlans']):
                    target.del_vlan(vlan)

        # check for freezed devices
        if getattr(target, '_freeze', None):
            with target._direct_state:
                target['ipdb_scope'] = 'shadow'
            return

        # check for locked devices
        if target.get('ipdb_scope') in ('locked', 'shadow'):
            return

        self._detach(None, msg['index'], msg)

    def _new(self, msg, skip_master=False):
        # check, if a record exists
        index = msg.get('index', None)
        ifname = msg.get_attr('IFLA_IFNAME', None)
        device = None
        cleanup = None

        # scenario #1: no matches for both: new interface
        #
        # scenario #2: ifname exists, index doesn't:
        #              index changed
        # scenario #3: index exists, ifname doesn't:
        #              name changed
        # scenario #4: both exist: assume simple update and
        #              an optional name change

        if (index not in self) and (ifname not in self):
            # scenario #1, new interface
            device = self[index] = self[ifname] = Interface(ipdb=self.ipdb)
        elif (index not in self) and (ifname in self):
            # scenario #2, index change
            old_index = self[ifname]['index']
            device = self[index] = self[ifname]
            if old_index in self:
                cleanup = old_index

            if old_index in self.ipdb.ipaddr:
                self.ipdb.ipaddr[index] = self.ipdb.ipaddr[old_index]
                del self.ipdb.ipaddr[old_index]

            if old_index in self.ipdb.neighbours:
                self.ipdb.neighbours[index] = self.ipdb.neighbours[old_index]
                del self.ipdb.neighbours[old_index]
        else:
            # scenario #3, interface rename
            # scenario #4, assume rename
            old_name = self[index]['ifname']
            if old_name != ifname:
                # unlink old name
                cleanup = old_name
            device = self[ifname] = self[index]

        if index not in self.ipdb.ipaddr:
            self.ipdb.ipaddr[index] = self.ipdb._ipaddr_set()

        if index not in self.ipdb.neighbours:
            self.ipdb.neighbours[index] = LinkedSet()

        # update port references
        old_master = device.get('master', None)
        new_master = msg.get_attr('IFLA_MASTER')

        if old_master != new_master:
            if old_master in self:
                with self[old_master]._direct_state:
                    if index in self[old_master]['ports']:
                        self[old_master].del_port(index)
            if new_master in self and new_master != index:
                with self[new_master]._direct_state:
                    self[new_master].add_port(index)

        if cleanup is not None:
            del self[cleanup]

        if skip_master:
            msg.strip('IFLA_MASTER')

        device.load_netlink(msg)
        if new_master is None:
            with device._direct_state:
                device['master'] = None

    def _detach(self, name, idx, msg=None):
        with self.ipdb.exclusive:
            if msg is not None:
                if (
                    msg['event'] == 'RTM_DELLINK'
                    and msg['change'] != 0xFFFFFFFF
                ):
                    return
            if idx is None or idx < 1:
                target = self[name]
                idx = target['index']
            else:
                target = self[idx]
                name = target['ifname']
            # clean up port, if exists
            master = target.get('master', None)
            if master in self and target['index'] in self[master]['ports']:
                with self[master]._direct_state:
                    self[master].del_port(target)
            self.pop(name, None)
            self.pop(idx, None)
            self.ipdb.ipaddr.pop(idx, None)
            self.ipdb.neighbours.pop(idx, None)
            with target._direct_state:
                target['ipdb_scope'] = 'detached'


class AddressesDict(dict):
    def __init__(self, ipdb):
        self.ipdb = ipdb
        self._event_map = {'RTM_NEWADDR': self._new, 'RTM_DELADDR': self._del}

    def _register(self):
        for msg in self.ipdb.nl.get_addr():
            self._new(msg)

    def reload(self):
        # Reload addresses from the kernel.
        # (This is a workaround to reorder primary and secondary addresses.)
        for k in self.keys():
            self[k] = self.ipdb._ipaddr_set()
        for msg in self.ipdb.nl.get_addr():
            self._new(msg)
        for idx in self.keys():
            iff = self.ipdb.interfaces[idx]
            with iff._direct_state:
                iff['ipaddr'] = self[idx]

    def _new(self, msg):
        if msg['family'] == AF_INET:
            addr = msg.get_attr('IFA_LOCAL')
        elif msg['family'] == AF_INET6:
            addr = msg.get_attr('IFA_LOCAL')
            if not addr:
                addr = msg.get_attr('IFA_ADDRESS')
        else:
            return
        raw = {
            'local': msg.get_attr('IFA_LOCAL'),
            'broadcast': msg.get_attr('IFA_BROADCAST'),
            'address': msg.get_attr('IFA_ADDRESS'),
            'flags': msg.get_attr('IFA_FLAGS') or msg.get('flags'),
            'prefixlen': msg['prefixlen'],
            'family': msg['family'],
            'cacheinfo': msg.get_attr('IFA_CACHEINFO'),
        }
        try:
            self[msg['index']].add(key=(addr, raw['prefixlen']), raw=raw)
        except:
            pass

    def _del(self, msg):
        if msg['family'] == AF_INET:
            addr = msg.get_attr('IFA_LOCAL')
        elif msg['family'] == AF_INET6:
            addr = msg.get_attr('IFA_ADDRESS')
        else:
            return
        try:
            self[msg['index']].remove((addr, msg['prefixlen']))
        except:
            pass


class NeighboursDict(dict):
    def __init__(self, ipdb):
        self.ipdb = ipdb
        self._event_map = {
            'RTM_NEWNEIGH': self._new,
            'RTM_DELNEIGH': self._del,
        }

    def _register(self):
        for msg in self.ipdb.nl.get_neighbours():
            self._new(msg)

    def _new(self, msg):
        if msg['family'] == AF_BRIDGE:
            return

        try:
            (
                self[msg['ifindex']].add(
                    key=msg.get_attr('NDA_DST'),
                    raw={'lladdr': msg.get_attr('NDA_LLADDR')},
                )
            )
        except:
            pass

    def _del(self, msg):
        if msg['family'] == AF_BRIDGE:
            return
        try:
            (self[msg['ifindex']].remove(msg.get_attr('NDA_DST')))
        except:
            pass


spec = [
    {'name': 'interfaces', 'class': InterfacesDict, 'kwarg': {}},
    {
        'name': 'by_name',
        'class': View,
        'kwarg': {
            'path': 'interfaces',
            'constraint': lambda k, v: isinstance(k, basestring),
        },
    },
    {
        'name': 'by_index',
        'class': View,
        'kwarg': {
            'path': 'interfaces',
            'constraint': lambda k, v: isinstance(k, int),
        },
    },
    {'name': 'ipaddr', 'class': AddressesDict, 'kwarg': {}},
    {'name': 'neighbours', 'class': NeighboursDict, 'kwarg': {}},
]
