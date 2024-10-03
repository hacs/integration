# -*- coding: utf-8 -*-
import logging
import os
import time
import warnings
from functools import partial
from itertools import chain
from socket import AF_INET, AF_INET6, AF_UNSPEC

from pyroute2 import config
from pyroute2.common import AF_MPLS, basestring
from pyroute2.config import AF_BRIDGE
from pyroute2.lab import LAB_API
from pyroute2.netlink import (
    NLM_F_ACK,
    NLM_F_APPEND,
    NLM_F_ATOMIC,
    NLM_F_CREATE,
    NLM_F_DUMP,
    NLM_F_ECHO,
    NLM_F_EXCL,
    NLM_F_REPLACE,
    NLM_F_REQUEST,
    NLM_F_ROOT,
    NLMSG_ERROR,
)
from pyroute2.netlink.exceptions import (
    NetlinkDumpInterrupted,
    NetlinkError,
    SkipInode,
)
from pyroute2.netlink.rtnl import (
    RTM_DELADDR,
    RTM_DELLINK,
    RTM_DELLINKPROP,
    RTM_DELNEIGH,
    RTM_DELQDISC,
    RTM_DELROUTE,
    RTM_DELRULE,
    RTM_DELTCLASS,
    RTM_DELTFILTER,
    RTM_GETADDR,
    RTM_GETLINK,
    RTM_GETNEIGH,
    RTM_GETNEIGHTBL,
    RTM_GETNSID,
    RTM_GETQDISC,
    RTM_GETROUTE,
    RTM_GETRULE,
    RTM_GETSTATS,
    RTM_GETTCLASS,
    RTM_GETTFILTER,
    RTM_NEWADDR,
    RTM_NEWLINK,
    RTM_NEWLINKPROP,
    RTM_NEWNEIGH,
    RTM_NEWNETNS,
    RTM_NEWNSID,
    RTM_NEWQDISC,
    RTM_NEWROUTE,
    RTM_NEWRULE,
    RTM_NEWTCLASS,
    RTM_NEWTFILTER,
    RTM_SETLINK,
    RTMGRP_IPV4_IFADDR,
    RTMGRP_IPV4_ROUTE,
    RTMGRP_IPV4_RULE,
    RTMGRP_IPV6_IFADDR,
    RTMGRP_IPV6_ROUTE,
    RTMGRP_IPV6_RULE,
    RTMGRP_LINK,
    RTMGRP_MPLS_ROUTE,
    RTMGRP_NEIGH,
    TC_H_ROOT,
    ndmsg,
    rt_proto,
    rt_scope,
    rt_type,
)
from pyroute2.netlink.rtnl.fibmsg import fibmsg
from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.netlink.rtnl.ifstatsmsg import ifstatsmsg
from pyroute2.netlink.rtnl.iprsocket import (
    ChaoticIPRSocket,
    IPBatchSocket,
    IPRSocket,
)
from pyroute2.netlink.rtnl.ndtmsg import ndtmsg
from pyroute2.netlink.rtnl.nsidmsg import nsidmsg
from pyroute2.netlink.rtnl.nsinfmsg import nsinfmsg
from pyroute2.netlink.rtnl.riprsocket import RawIPRSocket
from pyroute2.netlink.rtnl.rtmsg import rtmsg
from pyroute2.netlink.rtnl.tcmsg import plugins as tc_plugins
from pyroute2.netlink.rtnl.tcmsg import tcmsg
from pyroute2.requests.address import AddressFieldFilter, AddressIPRouteFilter
from pyroute2.requests.bridge import (
    BridgeFieldFilter,
    BridgeIPRouteFilter,
    BridgePortFieldFilter,
)
from pyroute2.requests.link import LinkFieldFilter, LinkIPRouteFilter
from pyroute2.requests.main import RequestProcessor
from pyroute2.requests.neighbour import (
    NeighbourFieldFilter,
    NeighbourIPRouteFilter,
)
from pyroute2.requests.route import RouteFieldFilter, RouteIPRouteFilter
from pyroute2.requests.rule import RuleFieldFilter, RuleIPRouteFilter

from .parsers import default_routes

DEFAULT_TABLE = 254
log = logging.getLogger(__name__)


def get_dump_filter(kwarg):
    if 'match' in kwarg:
        return kwarg.pop('match'), kwarg
    else:
        new_kwarg = {}
        if 'family' in kwarg:
            new_kwarg['family'] = kwarg.pop('family')
        return kwarg, new_kwarg


def transform_handle(handle):
    if isinstance(handle, basestring):
        (major, minor) = [int(x if x else '0', 16) for x in handle.split(':')]
        handle = (major << 8 * 2) | minor
    return handle


class RTNL_API:
    '''
    `RTNL_API` should not be instantiated by itself. It is intended
    to be used as a mixin class. Following classes use `RTNL_API`:

    * `IPRoute` -- RTNL API to the current network namespace
    * `NetNS` -- RTNL API to another network namespace
    * `IPBatch` -- RTNL compiler
    * `ShellIPR` -- RTNL via standard I/O, runs IPRoute in a shell

    It is an old-school API, that provides access to rtnetlink as is.
    It helps you to retrieve and change almost all the data, available
    through rtnetlink::

        from pyroute2 import IPRoute
        ipr = IPRoute()
        # create an interface
        ipr.link('add', ifname='brx', kind='bridge')
        # lookup the index
        dev = ipr.link_lookup(ifname='brx')[0]
        # bring it down
        ipr.link('set', index=dev, state='down')
        # change the interface MAC address and rename it just for fun
        ipr.link('set', index=dev,
                 address='00:11:22:33:44:55',
                 ifname='br-ctrl')
        # add primary IP address
        ipr.addr('add', index=dev,
                 address='10.0.0.1', mask=24,
                 broadcast='10.0.0.255')
        # add secondary IP address
        ipr.addr('add', index=dev,
                 address='10.0.0.2', mask=24,
                 broadcast='10.0.0.255')
        # bring it up
        ipr.link('set', index=dev, state='up')
    '''

    def __init__(self, *argv, **kwarg):
        if 'netns_path' in kwarg:
            self.netns_path = kwarg['netns_path']
        else:
            self.netns_path = config.netns_path
        super().__init__(*argv, **kwarg)
        if not self.nlm_generator:

            def filter_messages(*argv, **kwarg):
                return tuple(self._genmatch(*argv, **kwarg))

            self._genmatch = self.filter_messages
            self.filter_messages = filter_messages

    def make_request_type(self, command, command_map):
        if isinstance(command, basestring):
            return (lambda x: (x[0], self.make_request_flags(x[1])))(
                command_map[command]
            )
        elif isinstance(command, int):
            return command, self.make_request_flags('create')
        elif isinstance(command, (list, tuple)):
            return command
        else:
            raise TypeError('allowed command types: int, str, list, tuple')

    def make_request_flags(self, mode):
        flags = {
            'dump': NLM_F_REQUEST | NLM_F_DUMP,
            'get': NLM_F_REQUEST | NLM_F_ACK,
            'req': NLM_F_REQUEST | NLM_F_ACK,
        }
        flags['create'] = flags['req'] | NLM_F_CREATE | NLM_F_EXCL
        flags['append'] = flags['req'] | NLM_F_CREATE | NLM_F_APPEND
        flags['change'] = flags['req'] | NLM_F_REPLACE
        flags['replace'] = flags['change'] | NLM_F_CREATE

        return flags[mode] | (
            NLM_F_ECHO
            if (self.config['nlm_echo'] and mode not in ('get', 'dump'))
            else 0
        )

    def filter_messages(self, dump_filter, msgs):
        '''
        Filter messages using `dump_filter`. The filter might be a
        callable, then it will be called for every message in the list.
        Or it might be a dict, where keys are used to get values
        from messages, and dict values are used to match the message.

        The method might be called directly. It is also used by calls
        like `ipr.link('dump', ....)`, where keyword arguments work as
        `dump_filter` for `ipr.filter_messages()`.

        A callable `dump_filter` must return True or False:

        .. code-block:: python

            # get all links with names starting with eth:
            #
            ipr.filter_messages(
                lambda x: x.get_attr('IFLA_IFNAME').startswith('eth'),
                ipr.link('dump')
            )

        A dict `dump_filter` can have callables as values:

        .. code-block:: python

            # get all links with names starting with eth, and
            # MAC address in a database:
            #
            ipr.filter_messages(
                {
                    'ifname': lambda x: x.startswith('eth'),
                    'address': lambda x: x in database,
                },
                ipr.link('dump')
            )

        ... or constants to compare with:

        .. code-block:: python

            # get all links in state up:
            #
            ipr.filter_message({'state': 'up'}, ipr.link('dump'))
        '''
        # filtered results, the generator version
        for msg in msgs:
            if hasattr(dump_filter, '__call__'):
                if dump_filter(msg):
                    yield msg
            elif isinstance(dump_filter, dict):
                matches = []
                for key in dump_filter:
                    # get the attribute
                    if isinstance(key, str):
                        nkey = (key,)
                    elif isinstance(key, tuple):
                        nkey = key
                    else:
                        continue
                    value = msg.get_nested(*nkey)
                    if value is not None and callable(dump_filter[key]):
                        matches.append(dump_filter[key](value))
                    else:
                        matches.append(dump_filter[key] == value)
                if all(matches):
                    yield msg

    # 8<---------------------------------------------------------------
    #
    def dump(self, groups=None):
        '''
        Dump network objects.

        On OpenBSD:

        * get_links()
        * get_addr()
        * get_neighbours()
        * get_routes()

        On Linux:

        * get_links()
        * get_addr()
        * get_neighbours()
        * get_vlans()
        * dump FDB
        * IPv4 and IPv6 rules
        '''
        ##
        # Well, it's the Linux API, why OpenBSD / FreeBSD here?
        #
        # 'Cause when you run RemoteIPRoute, it uses this class,
        # and the code may be run on BSD systems as well, though
        # BSD systems have only subset of the API
        #
        if self.uname[0] == 'OpenBSD':
            groups_map = {
                1: [
                    self.get_links,
                    self.get_addr,
                    self.get_neighbours,
                    self.get_routes,
                ]
            }
        else:
            groups_map = {
                RTMGRP_LINK: [
                    self.get_links,
                    self.get_vlans,
                    partial(self.fdb, 'dump'),
                ],
                RTMGRP_IPV4_IFADDR: [partial(self.get_addr, family=AF_INET)],
                RTMGRP_IPV6_IFADDR: [partial(self.get_addr, family=AF_INET6)],
                RTMGRP_NEIGH: [self.get_neighbours],
                RTMGRP_IPV4_ROUTE: [partial(self.get_routes, family=AF_INET)],
                RTMGRP_IPV6_ROUTE: [partial(self.get_routes, family=AF_INET6)],
                RTMGRP_MPLS_ROUTE: [partial(self.get_routes, family=AF_MPLS)],
                RTMGRP_IPV4_RULE: [partial(self.get_rules, family=AF_INET)],
                RTMGRP_IPV6_RULE: [partial(self.get_rules, family=AF_INET6)],
            }
        for group, methods in groups_map.items():
            if group & (groups if groups is not None else self.groups):
                for method in methods:
                    for msg in method():
                        yield msg

    def poll(self, method, command, timeout=10, interval=0.2, **spec):
        '''
        Run `method` with a positional argument `command` and keyword
        arguments `**spec` every `interval` seconds, but not more than
        `timeout`, until it returns a result which doesn't evaluate to
        `False`.

        Example:

        .. code-block:: python

            # create a bridge interface and wait for it:
            #
            spec = {
                'ifname': 'br0',
                'kind': 'bridge',
                'state': 'up',
                'br_stp_state': 1,
            }
            ipr.link('add', **spec)
            ret = ipr.poll(ipr.link, 'dump', **spec)

            assert ret[0].get('ifname') == 'br0'
            assert ret[0].get('state') == 'up'
            assert ret[0].get(('linkinfo', 'data', 'br_stp_state')) == 1
        '''
        ctime = time.time()
        ret = tuple()
        while ctime + timeout > time.time():
            try:
                ret = method(command, **spec)
                if ret:
                    return ret
                time.sleep(interval)
            except NetlinkDumpInterrupted:
                pass
        raise TimeoutError()

    # 8<---------------------------------------------------------------
    #
    # Listing methods
    #
    def get_qdiscs(self, index=None):
        '''
        Get all queue disciplines for all interfaces or for specified
        one.
        '''
        msg = tcmsg()
        msg['family'] = AF_UNSPEC
        ret = self.nlm_request(msg, RTM_GETQDISC)
        if index is None:
            return tuple(ret)
        else:
            return [x for x in ret if x['index'] == index]

    def get_filters(self, index=0, handle=0, parent=0):
        '''
        Get filters for specified interface, handle and parent.
        '''
        msg = tcmsg()
        msg['family'] = AF_UNSPEC
        msg['index'] = index
        msg['handle'] = transform_handle(handle)
        msg['parent'] = transform_handle(parent)
        return tuple(self.nlm_request(msg, RTM_GETTFILTER))

    def get_classes(self, index=0):
        '''
        Get classes for specified interface.
        '''
        msg = tcmsg()
        msg['family'] = AF_UNSPEC
        msg['index'] = index
        return tuple(self.nlm_request(msg, RTM_GETTCLASS))

    def get_vlans(self, **kwarg):
        '''
        Dump available vlan info on bridge ports
        '''
        # IFLA_EXT_MASK, extended info mask
        #
        # include/uapi/linux/rtnetlink.h
        # 1 << 0 => RTEXT_FILTER_VF
        # 1 << 1 => RTEXT_FILTER_BRVLAN
        # 1 << 2 => RTEXT_FILTER_BRVLAN_COMPRESSED
        # 1 << 3 => RTEXT_FILTER_SKIP_STATS
        #
        # maybe place it as mapping into ifinfomsg.py?
        #
        dump_filter, kwarg = get_dump_filter(kwarg)
        return self.link(
            'dump', family=AF_BRIDGE, ext_mask=2, match=dump_filter
        )

    def get_links(self, *argv, **kwarg):
        '''
        Get network interfaces.

        By default returns all interfaces. Arguments vector
        can contain interface indices or a special keyword
        'all'::

            ip.get_links()
            ip.get_links('all')
            ip.get_links(1, 2, 3)

            interfaces = [1, 2, 3]
            ip.get_links(*interfaces)
        '''
        result = []
        links = argv or [0]
        if links[0] == 'all':  # compat syntax
            links = [0]

        if links[0] == 0:
            cmd = 'dump'
        else:
            cmd = 'get'

        for index in links:
            if index > 0:
                kwarg['index'] = index
            result.extend(self.link(cmd, **kwarg))
        return result

    def get_neighbours(self, family=AF_UNSPEC, match=None, **kwarg):
        '''
        Dump ARP cache records.

        The `family` keyword sets the family for the request:
        e.g. `AF_INET` or `AF_INET6` for arp cache, `AF_BRIDGE`
        for fdb.

        If other keyword arguments not empty, they are used as
        filter. Also, one can explicitly set filter as a function
        with the `match` parameter.

        Examples::

            # get neighbours on the 3rd link:
            ip.get_neighbours(ifindex=3)

            # get a particular record by dst:
            ip.get_neighbours(dst='172.16.0.1')

            # get fdb records:
            ip.get_neighbours(AF_BRIDGE)

            # and filter them by a function:
            ip.get_neighbours(AF_BRIDGE, match=lambda x: x['state'] == 2)
        '''
        return self.neigh('dump', family=family, match=match or kwarg)

    def get_ntables(self, family=AF_UNSPEC):
        '''
        Get neighbour tables
        '''
        msg = ndtmsg()
        msg['family'] = family
        return tuple(self.nlm_request(msg, RTM_GETNEIGHTBL))

    def get_addr(self, family=AF_UNSPEC, match=None, **kwarg):
        '''
        Dump addresses.

        If family is not specified, both AF_INET and AF_INET6 addresses
        will be dumped::

            # get all addresses
            ip.get_addr()

        It is possible to apply filters on the results::

            # get addresses for the 2nd interface
            ip.get_addr(index=2)

            # get addresses with IFA_LABEL == 'eth0'
            ip.get_addr(label='eth0')

            # get all the subnet addresses on the interface, identified
            # by broadcast address (should be explicitly specified upon
            # creation)
            ip.get_addr(index=2, broadcast='192.168.1.255')

        A custom predicate can be used as a filter::

            ip.get_addr(match=lambda x: x['index'] == 1)
        '''
        return self.addr('dump', family=family, match=match or kwarg)

    def get_rules(self, family=AF_UNSPEC, match=None, **kwarg):
        '''
        Get all rules. By default return all rules. To explicitly
        request the IPv4 rules use `family=AF_INET`.

        Example::
            ip.get_rules() # get all the rules for all families
            ip.get_rules(family=AF_INET6)  # get only IPv6 rules
        '''
        return self.rule(
            (RTM_GETRULE, NLM_F_REQUEST | NLM_F_ROOT | NLM_F_ATOMIC),
            family=family,
            match=match or kwarg,
        )

    def get_routes(self, family=255, match=None, **kwarg):
        '''
        Get all routes. You can specify the table. There
        are up to 4294967295 routing classes (tables), and the kernel
        returns all the routes on each request. So the
        routine filters routes from full output. Note the number of
        tables is increased from 255 in Linux 2.6+.

        Example::

            ip.get_routes()  # get all the routes for all families
            ip.get_routes(family=AF_INET6)  # get only IPv6 routes
            ip.get_routes(table=254)  # get routes from 254 table

        The default family=255 is a hack. Despite the specs,
        the kernel returns only IPv4 routes for AF_UNSPEC family.
        But it returns all the routes for all the families if one
        uses an invalid value here. Hack but true. And let's hope
        the kernel team will not fix this bug.
        '''
        # get a particular route?
        if isinstance(kwarg.get('dst'), str):
            return self.route('get', dst=kwarg['dst'])
        else:
            return self.route('dump', family=family, match=match or kwarg)

    # 8<---------------------------------------------------------------

    # 8<---------------------------------------------------------------
    @staticmethod
    def open_file(path):
        '''Open a file (read only) and return its (fd, inode).'''
        fd = os.open(path, os.O_RDONLY)
        inode = os.fstat(fd).st_ino
        return (fd, inode)

    @staticmethod
    def close_file(fd):
        '''Close a file that was previously opened with open_file().'''
        os.close(fd)

    @staticmethod
    def get_pid():
        '''Return the PID of the current process.'''
        return os.getpid()

    def register_link_kind(self, path=None, pkg=None, module=None):
        return ifinfmsg.ifinfo.register_link_kind(path, pkg, module)

    def unregister_link_kind(self, kind):
        return ifinfmsg.ifinfo.unregister_link_kind(kind)

    def list_link_kind(self):
        return ifinfmsg.ifinfo.list_link_kind()

    #
    # List NetNS info
    #
    def _dump_one_ns(self, path, registry):
        item = nsinfmsg()
        item['netnsid'] = 0xFFFFFFFF  # default netnsid "unknown"
        nsfd = 0
        info = nsidmsg()
        msg = nsidmsg()
        try:
            (nsfd, inode) = self.open_file(path)
            item['inode'] = inode
            #
            # if the inode is registered, skip it
            #
            if item['inode'] in registry:
                raise SkipInode()
            registry.add(item['inode'])
            #
            # request NETNSA_NSID
            #
            # may not work on older kernels ( <4.20 ?)
            #
            msg['attrs'] = [('NETNSA_FD', nsfd)]
            try:
                for info in self.nlm_request(msg, RTM_GETNSID, NLM_F_REQUEST):
                    # response to nlm_request() is a list or a generator,
                    # that's why loop
                    item['netnsid'] = info.get_attr('NETNSA_NSID')
                    break
            except Exception:
                pass
            item['attrs'] = [('NSINFO_PATH', path)]
        except OSError as e:
            raise SkipInode(e.errno)
        finally:
            if nsfd > 0:
                self.close_file(nsfd)
        item['header']['type'] = RTM_NEWNETNS
        item['header']['target'] = self.target
        item['event'] = 'RTM_NEWNETNS'
        return item

    def _dump_dir(self, path, registry):
        for name in os.listdir(path):
            # strictly speaking, there is no need to use os.sep,
            # since the code is not portable outside of Linux
            nspath = '%s%s%s' % (path, os.sep, name)
            try:
                yield self._dump_one_ns(nspath, registry)
            except SkipInode:
                pass

    def _dump_proc(self, registry):
        for name in os.listdir('/proc'):
            try:
                int(name)
            except ValueError:
                continue

            try:
                yield self._dump_one_ns('/proc/%s/ns/net' % name, registry)
            except SkipInode:
                pass

    def get_netnsid(self, nsid=None, pid=None, fd=None, target_nsid=None):
        '''Return a dict containing the result of a RTM_GETNSID query.
        This loosely corresponds to the "ip netns list-id" command.
        '''
        msg = nsidmsg()

        if nsid is not None:
            msg['attrs'].append(('NETNSA_NSID', nsid))

        if pid is not None:
            msg['attrs'].append(('NETNSA_PID', pid))

        if fd is not None:
            msg['attrs'].append(('NETNSA_FD', fd))

        if target_nsid is not None:
            msg['attrs'].append(('NETNSA_TARGET_NSID', target_nsid))

        response = self.nlm_request(msg, RTM_GETNSID, NLM_F_REQUEST)
        for r in response:
            return {
                'nsid': r.get_attr('NETNSA_NSID'),
                'current_nsid': r.get_attr('NETNSA_CURRENT_NSID'),
            }

        return None

    def get_netns_info(self, list_proc=False):
        '''
        A prototype method to list available netns and associated
        interfaces. A bit weird to have it here and not under
        `pyroute2.netns`, but it uses RTNL to get all the info.
        '''
        #
        # register all the ns inodes, not to repeat items in the output
        #
        registry = set()
        #
        # fetch veth peers
        #
        peers = {}
        for peer in self.get_links():
            netnsid = peer.get_attr('IFLA_LINK_NETNSID')
            if netnsid is not None:
                if netnsid not in peers:
                    peers[netnsid] = []
                peers[netnsid].append(peer.get_attr('IFLA_IFNAME'))
        #
        # chain iterators:
        #
        # * one iterator for every item in self.path
        # * one iterator for /proc/<pid>/ns/net
        #
        views = []
        for path in self.netns_path:
            views.append(self._dump_dir(path, registry))
        if list_proc:
            views.append(self._dump_proc(registry))
        #
        # iterate all the items
        #
        for view in views:
            try:
                for item in view:
                    #
                    # remove uninitialized 'value' field
                    #
                    del item['value']
                    #
                    # fetch peers for that ns
                    #
                    for peer in peers.get(item['netnsid'], []):
                        item['attrs'].append(('NSINFO_PEER', peer))
                    yield item
            except OSError:
                pass

    def set_netnsid(self, nsid=None, pid=None, fd=None):
        '''Assigns an id to a peer netns using RTM_NEWNSID query.
        The kernel chooses an unique id if nsid is omitted.
        This corresponds to the "ip netns set" command.
        '''
        msg = nsidmsg()

        if nsid is None or nsid < 0:
            # kernel auto select
            msg['attrs'].append(('NETNSA_NSID', 4294967295))
        else:
            msg['attrs'].append(('NETNSA_NSID', nsid))

        if pid is not None:
            msg['attrs'].append(('NETNSA_PID', pid))

        if fd is not None:
            msg['attrs'].append(('NETNSA_FD', fd))

        return self.nlm_request(msg, RTM_NEWNSID, NLM_F_REQUEST | NLM_F_ACK)

    # 8<---------------------------------------------------------------

    # 8<---------------------------------------------------------------
    #
    # Shortcuts
    #
    def get_default_routes(self, family=AF_UNSPEC, table=DEFAULT_TABLE):
        '''
        Get default routes
        '''
        msg = rtmsg()
        msg['family'] = family

        routes = self.nlm_request(
            msg,
            msg_type=RTM_GETROUTE,
            msg_flags=NLM_F_DUMP | NLM_F_REQUEST,
            parser=default_routes,
        )

        if table is None:
            return routes
        else:
            return self.filter_messages({'table': table}, routes)

    def link_lookup(self, match=None, **kwarg):
        '''
        Lookup interface index (indeces) by first level NLA
        value.

        Example::

            ip.link_lookup(address="52:54:00:9d:4e:3d")
            ip.link_lookup(ifname="lo")
            ip.link_lookup(operstate="UP")

        Please note, that link_lookup() returns list, not one
        value.
        '''
        if kwarg and set(kwarg) < {'index', 'ifname', 'altname'}:
            # shortcut for index and ifname
            try:
                for link in self.link('get', **kwarg):
                    return [link['index']]
            except NetlinkError:
                return []
        else:
            # otherwise fallback to the userspace filter
            return [
                link['index'] for link in self.get_links(match=match or kwarg)
            ]

    # 8<---------------------------------------------------------------

    # 8<---------------------------------------------------------------
    #
    # Shortcuts to flush RTNL objects
    #
    def flush_routes(self, *argv, **kwarg):
        '''
        Flush routes -- purge route records from a table.
        Arguments are the same as for `get_routes()`
        routine. Actually, this routine implements a pipe from
        `get_routes()` to `nlm_request()`.
        '''
        ret = []
        for route in self.get_routes(*argv, **kwarg):
            self.put(route, msg_type=RTM_DELROUTE, msg_flags=NLM_F_REQUEST)
            ret.append(route)
        return ret

    def flush_addr(self, *argv, **kwarg):
        '''
        Flush IP addresses.

        Examples::

            # flush all addresses on the interface with index 2:
            ipr.flush_addr(index=2)

            # flush all addresses with IFA_LABEL='eth0':
            ipr.flush_addr(label='eth0')
        '''
        flags = NLM_F_CREATE | NLM_F_REQUEST
        ret = []
        for addr in self.get_addr(*argv, **kwarg):
            self.put(addr, msg_type=RTM_DELADDR, msg_flags=flags)
            ret.append(addr)
        return ret

    def flush_rules(self, *argv, **kwarg):
        '''
        Flush rules. Please keep in mind, that by default the function
        operates on **all** rules of **all** families. To work only on
        IPv4 rules, one should explicitly specify `family=AF_INET`.

        Examples::

            # flush all IPv4 rule with priorities above 5 and below 32000
            ipr.flush_rules(family=AF_INET, priority=lambda x: 5 < x < 32000)

            # flush all IPv6 rules that point to table 250:
            ipr.flush_rules(family=socket.AF_INET6, table=250)
        '''
        flags = NLM_F_CREATE | NLM_F_REQUEST
        ret = []
        for rule in self.get_rules(*argv, **kwarg):
            self.put(rule, msg_type=RTM_DELRULE, msg_flags=flags)
            ret.append(rule)
        return ret

    # 8<---------------------------------------------------------------

    # 8<---------------------------------------------------------------
    #
    # Extensions to low-level functions
    #
    def brport(self, command, **kwarg):
        '''
        Set bridge port parameters. Example::

            idx = ip.link_lookup(ifname='eth0')
            ip.brport("set", index=idx, unicast_flood=0, cost=200)
            ip.brport("show", index=idx)

        Possible keywords are NLA names for the `protinfo_bridge` class,
        without the prefix and in lower letters.
        '''
        if command == 'set':
            linkkwarg = dict()
            linkkwarg['index'] = kwarg.pop('index', 0)
            linkkwarg['kind'] = 'bridge_slave'
            for key in kwarg:
                linkkwarg[key] = kwarg[key]
            return self.link(command, **linkkwarg)
        if (command in ('dump', 'show')) and ('match' not in kwarg):
            match = kwarg
        else:
            match = kwarg.pop('match', None)

        command_map = {
            'dump': (RTM_GETLINK, 'dump'),
            'show': (RTM_GETLINK, 'dump'),
        }
        (command, msg_flags) = self.make_request_type(command, command_map)

        msg = ifinfmsg()
        msg['index'] = kwarg.get('index', 0)
        msg['family'] = AF_BRIDGE
        protinfo = (
            RequestProcessor(context=match, prime=match)
            .apply_filter(BridgePortFieldFilter(command))
            .finalize()
        )
        msg['attrs'].append(
            ('IFLA_PROTINFO', {'attrs': protinfo['attrs']}, 0x8000)
        )
        ret = self.nlm_request(msg, msg_type=command, msg_flags=msg_flags)
        if match is not None:
            ret = self.filter_messages(match, ret)

        if self.nlm_generator and not msg_flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    def vlan_filter(self, command, **kwarg):
        '''
        Vlan filters is another approach to support vlans in Linux.
        Before vlan filters were introduced, there was only one way
        to bridge vlans: one had to create vlan interfaces and
        then add them as ports::

                    +------+      +----------+
            net --> | eth0 | <--> | eth0.500 | <---+
                    +------+      +----------+     |
                                                   v
                    +------+                    +-----+
            net --> | eth1 |                    | br0 |
                    +------+                    +-----+
                                                   ^
                    +------+      +----------+     |
            net --> | eth2 | <--> | eth2.500 | <---+
                    +------+      +----------+

        It means that one has to create as many bridges, as there were
        vlans. Vlan filters allow to bridge together underlying interfaces
        and create vlans already on the bridge::

            # v500 label shows which interfaces have vlan filter

                    +------+ v500
            net --> | eth0 | <-------+
                    +------+         |
                                     v
                    +------+      +-----+    +---------+
            net --> | eth1 | <--> | br0 |<-->| br0v500 |
                    +------+      +-----+    +---------+
                                     ^
                    +------+ v500    |
            net --> | eth2 | <-------+
                    +------+

        In this example vlan 500 will be allowed only on ports `eth0` and
        `eth2`, though all three eth nics are bridged.

        Some example code::

            # create bridge
            ip.link("add",
                    ifname="br0",
                    kind="bridge")

            # attach a port
            ip.link("set",
                    index=ip.link_lookup(ifname="eth0")[0],
                    master=ip.link_lookup(ifname="br0")[0])

            # set vlan filter
            ip.vlan_filter("add",
                           index=ip.link_lookup(ifname="eth0")[0],
                           vlan_info={"vid": 500})

            # create vlan interface on the bridge
            ip.link("add",
                    ifname="br0v500",
                    kind="vlan",
                    link=ip.link_lookup(ifname="br0")[0],
                    vlan_id=500)

            # set all UP
            ip.link("set",
                    index=ip.link_lookup(ifname="br0")[0],
                    state="up")
            ip.link("set",
                    index=ip.link_lookup(ifname="br0v500")[0],
                    state="up")
            ip.link("set",
                    index=ip.link_lookup(ifname="eth0")[0],
                    state="up")

            # set IP address
            ip.addr("add",
                    index=ip.link_lookup(ifname="br0v500")[0],
                    address="172.16.5.2",
                    mask=24)

            Now all the traffic to the network 172.16.5.2/24 will go
            to vlan 500 only via ports that have such vlan filter.

        Required arguments for `vlan_filter()`: `index` and `vlan_info`.

        Vlan info dict::

            ip.vlan_filter('add',
                            index=<ifindex>,
                            vlan_info =
                            {'vid': <single or range>,
                            'pvid': <bool>,
                            'flags': int or list}

        More details:
            * kernel:Documentation/networking/switchdev.txt
            * pyroute2.netlink.rtnl.ifinfmsg:... vlan_info

        Setting PVID or specifying a range will specify the approprate flags.

        One can specify `flags` as int or as a list of flag names:
            * `master` == 0x1
            * `pvid` == 0x2
            * `untagged` == 0x4
            * `range_begin` == 0x8
            * `range_end` == 0x10
            * `brentry` == 0x20

        E.g.::

            {'vid': 20, 'pvid': true }

            # is equal to
            {'vid': 20, 'flags': ['pvid', 'untagged']}

            # is equal to
            {'vid': 20, 'flags': 6}

            # range
            {'vid': '100-199'}

        Required arguments for `vlan_filter()`: `index` and `vlan_tunnel_info`.

        Vlan tunnel info dict::

            ip.vlan_filter('add',
                          index=<ifindex>,
                          vlan_tunnel_info =
                          {'vid': <single or range>,
                          'id': <single or range>}

        vlan_tunnel_info appears to only use the 'range_begin' and 'range_end'
        flags from vlan_info. Specifying a range will automatically send the
        needed flags.

        Example::

            {'vid': 20, 'id: 20}
            {'vid': '200-299', 'id': '200-299'}

        The above directives can be combined as in the example::

          ip.vlan_filter('add',
                        index=7,
                        vlan_info={'vid': 600},
                        vlan_tunnel_info={'vid': 600, 'id': 600})

        Commands:

        **add**

        Add vlan filter to a bridge port. Example::

          ip.vlan_filter("add", index=2, vlan_info={"vid": 200})

        **del**

        Remove vlan filter from a bridge port. Example::

          ip.vlan_filter("del", index=2, vlan_info={"vid": 200})

        '''
        command_map = {
            'add': (RTM_SETLINK, 'req'),
            'del': (RTM_DELLINK, 'req'),
        }

        kwarg['family'] = AF_BRIDGE
        kwarg['kwarg_filter'] = [
            BridgeFieldFilter(),
            BridgeIPRouteFilter(command),
        ]

        (command, flags) = self.make_request_type(command, command_map)
        return tuple(self.link((command, flags), **kwarg))

    def fdb(self, command, **kwarg):
        '''
        Bridge forwarding database management.

        More details:
            * kernel:Documentation/networking/switchdev.txt
            * pyroute2.netlink.rtnl.ndmsg

        **add**

        Add a new FDB record. Works in the same way as ARP cache
        management, but some additional NLAs can be used::

            # simple FDB record
            #
            ip.fdb('add',
                   ifindex=ip.link_lookup(ifname='br0')[0],
                   lladdr='00:11:22:33:44:55',
                   dst='10.0.0.1')

            # specify vlan
            # NB: vlan should exist on the device, use
            # `vlan_filter()`
            #
            ip.fdb('add',
                   ifindex=ip.link_lookup(ifname='br0')[0],
                   lladdr='00:11:22:33:44:55',
                   dst='10.0.0.1',
                   vlan=200)

            # specify vxlan id and port
            # NB: works only for vxlan devices, use
            # `link("add", kind="vxlan", ...)`
            #
            # if port is not specified, the default one is used
            # by the kernel.
            #
            # if vni (vxlan id) is equal to the device vni,
            # the kernel doesn't report it back
            #
            ip.fdb('add',
                   ifindex=ip.link_lookup(ifname='vx500')[0]
                   lladdr='00:11:22:33:44:55',
                   dst='10.0.0.1',
                   port=5678,
                   vni=600)

            # or specify src_vni for a vlan-aware vxlan device
            ip.fdb('add',
                   ifindex=ip.link_lookup(ifname='vx500')[0]
                   lladdr='00:11:22:33:44:55',
                   dst='10.0.0.1',
                   port=5678,
                   src_vni=600)

        **append**

        Append a new FDB record. The same syntax as for **add**.

        **del**

        Remove an existing FDB record. The same syntax as for **add**.

        **dump**

        Dump all the FDB records. If any `**kwarg` is provided,
        results will be filtered::

            # dump all the records
            ip.fdb('dump')

            # show only specific lladdr, dst, vlan etc.
            ip.fdb('dump', lladdr='00:11:22:33:44:55')
            ip.fdb('dump', dst='10.0.0.1')
            ip.fdb('dump', vlan=200)

        '''
        dump_filter = None
        if command == 'dump':
            dump_filter, kwarg = get_dump_filter(kwarg)

        kwarg['family'] = AF_BRIDGE
        # nud -> state
        if 'nud' in kwarg:
            kwarg['state'] = kwarg.pop('nud')
        if (command in ('add', 'del', 'append')) and not (
            kwarg.get('state', 0) & ndmsg.states['noarp']
        ):
            # state must contain noarp in add / del / append
            kwarg['state'] = kwarg.pop('state', 0) | ndmsg.states['noarp']
            # other assumptions
            if not kwarg.get('state', 0) & (
                ndmsg.states['permanent'] | ndmsg.states['reachable']
            ):
                # permanent (default) or reachable
                kwarg['state'] |= ndmsg.states['permanent']
            if not kwarg.get('flags', 0) & (
                ndmsg.flags['self'] | ndmsg.flags['master']
            ):
                # self (default) or master
                kwarg['flags'] = kwarg.get('flags', 0) | ndmsg.flags['self']
        #
        if dump_filter is not None:
            kwarg['match'] = dump_filter
        return self.neigh(command, **kwarg)

    # 8<---------------------------------------------------------------
    #
    # General low-level configuration methods
    #
    def neigh(self, command, **kwarg):
        '''
        Neighbours operations, same as `ip neigh` or `bridge fdb`

        **add**

        Add a neighbour record, e.g.::

            from pyroute2 import IPRoute
            from pyroute2.netlink.rtnl import ndmsg

            # add a permanent record on veth0
            idx = ip.link_lookup(ifname='veth0')[0]
            ip.neigh('add',
                     dst='172.16.45.1',
                     lladdr='00:11:22:33:44:55',
                     ifindex=idx,
                     state=ndmsg.states['permanent'])

        **set**

        Set an existing record or create a new one, if it doesn't exist.
        The same as above, but the command is "set"::

            ip.neigh('set',
                     dst='172.16.45.1',
                     lladdr='00:11:22:33:44:55',
                     ifindex=idx,
                     state=ndmsg.states['permanent'])


        **change**

        Change an existing record. If the record doesn't exist, fail.

        **del**

        Delete an existing record.

        **dump**

        Dump all the records in the NDB::

            ip.neigh('dump')

        **get**

        Get specific record (dst and ifindex are mandatory). Available
        only on recent kernel::

            ip.neigh('get',
                     dst='172.16.45.1',
                     ifindex=idx)
        '''
        command_map = {
            'add': (RTM_NEWNEIGH, 'create'),
            'set': (RTM_NEWNEIGH, 'replace'),
            'replace': (RTM_NEWNEIGH, 'replace'),
            'change': (RTM_NEWNEIGH, 'change'),
            'del': (RTM_DELNEIGH, 'req'),
            'remove': (RTM_DELNEIGH, 'req'),
            'delete': (RTM_DELNEIGH, 'req'),
            'dump': (RTM_GETNEIGH, 'dump'),
            'get': (RTM_GETNEIGH, 'get'),
            'append': (RTM_NEWNEIGH, 'append'),
        }
        dump_filter = None
        msg = ndmsg.ndmsg()
        if command == 'dump':
            dump_filter, kwarg = get_dump_filter(kwarg)

        request = (
            RequestProcessor(context=kwarg, prime=kwarg)
            .apply_filter(NeighbourFieldFilter())
            .apply_filter(NeighbourIPRouteFilter(command))
            .finalize()
        )
        msg_type, msg_flags = self.make_request_type(command, command_map)

        # fill the fields
        for field in msg.fields:
            if (
                command == "dump"
                and self.strict_check
                and field[0] == "ifindex"
            ):
                # is dump & strict_check, leave ifindex for NLA
                continue
            msg[field[0]] = request.pop(field[0], 0)

        for key, value in request.items():
            nla = ndmsg.ndmsg.name2nla(key)
            if msg.valid_nla(nla) and value is not None:
                msg['attrs'].append([nla, value])

        ret = self.nlm_request(msg, msg_type=msg_type, msg_flags=msg_flags)

        if command == 'dump' and dump_filter:
            ret = self.filter_messages(dump_filter, ret)

        if self.nlm_generator and not msg_flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    def link(self, command, **kwarg):
        '''
        Link operations.

        Keywords to set up ifinfmsg fields:
            * index -- interface index
            * family -- AF_BRIDGE for bridge operations, otherwise 0
            * flags -- device flags
            * change -- change mask

        All other keywords will be translated to NLA names, e.g.
        `mtu -> IFLA_MTU`, `af_spec -> IFLA_AF_SPEC` etc. You can
        provide a complete NLA structure or let filters do it for
        you. E.g., these pairs show equal statements::

            # set device MTU
            ip.link("set", index=x, mtu=1000)
            ip.link("set", index=x, IFLA_MTU=1000)

            # add vlan device
            ip.link("add", ifname="test", kind="dummy")
            ip.link("add", ifname="test",
                    IFLA_LINKINFO={'attrs': [['IFLA_INFO_KIND', 'dummy']]})

        Filters are implemented in the `pyroute2.iproute.req` module.
        You can contribute your own if you miss shortcuts.

        Commands:

        **add**

        To create an interface, one should specify the interface kind::

            ip.link("add",
                    ifname="test",
                    kind="dummy")

        The kind can be any of those supported by kernel. It can be
        `dummy`, `bridge`, `bond` etc. On modern kernels one can specify
        even interface index::

            ip.link("add",
                    ifname="br-test",
                    kind="bridge",
                    index=2345)

        Specific type notes:

        ► geneve

        Create GENEVE tunnel::

            ip.link("add",
                    ifname="genx",
                    kind="geneve",
                    geneve_id=42,
                    geneve_remote="172.16.0.101")

        Support for GENEVE over IPv6 is also included; use `geneve_remote6`
        to configure a remote IPv6 address.

        ► gre

        Create GRE tunnel::

            ip.link("add",
                    ifname="grex",
                    kind="gre",
                    gre_local="172.16.0.1",
                    gre_remote="172.16.0.101",
                    gre_ttl=16)

        The keyed GRE requires explicit iflags/oflags specification::

            ip.link("add",
                    ifname="grex",
                    kind="gre",
                    gre_local="172.16.0.1",
                    gre_remote="172.16.0.101",
                    gre_ttl=16,
                    gre_ikey=10,
                    gre_okey=10,
                    gre_iflags=32,
                    gre_oflags=32)

        Support for GRE over IPv6 is also included; use `kind=ip6gre` and
        `ip6gre_` as the prefix for its values.

        ► ipip

        Create ipip tunnel::

            ip.link("add",
                    ifname="tun1",
                    kind="ipip",
                    ipip_local="172.16.0.1",
                    ipip_remote="172.16.0.101",
                    ipip_ttl=16)

        Support for sit and ip6tnl is also included; use `kind=sit` and `sit_`
        as prefix for sit tunnels, and `kind=ip6tnl` and `ip6tnl_` prefix for
        ip6tnl tunnels.

        ► macvlan

        Macvlan interfaces act like VLANs within OS. The macvlan driver
        provides an ability to add several MAC addresses on one interface,
        where every MAC address is reflected with a virtual interface in
        the system.

        In some setups macvlan interfaces can replace bridge interfaces,
        providing more simple and at the same time high-performance
        solution::

            ip.link("add",
                    ifname="mvlan0",
                    kind="macvlan",
                    link=ip.link_lookup(ifname="em1")[0],
                    macvlan_mode="private").commit()

        Several macvlan modes are available: "private", "vepa", "bridge",
        "passthru". Ususally the default is "vepa".

        ► macvtap

        Almost the same as macvlan, but creates also a character tap device::

            ip.link("add",
                    ifname="mvtap0",
                    kind="macvtap",
                    link=ip.link_lookup(ifname="em1")[0],
                    macvtap_mode="vepa").commit()

        Will create a device file `"/dev/tap%s" % index`

        ► tuntap

        Possible `tuntap` keywords:

        * `mode` — "tun" or "tap"
        * `uid` — integer
        * `gid` — integer
        * `ifr` — dict of tuntap flags (see ifinfmsg:... tuntap_data)

        Create a tap interface::

            ip.link("add",
                    ifname="tap0",
                    kind="tuntap",
                    mode="tap")

        Tun/tap interfaces are created using `ioctl()`, but the library
        provides a transparent way to manage them using netlink API.

        ► veth

        To properly create `veth` interface, one should specify
        `peer` also, since `veth` interfaces are created in pairs::

            # simple call
            ip.link("add", ifname="v1p0", kind="veth", peer="v1p1")

            # set up specific veth peer attributes
            ip.link("add",
                    ifname="v1p0",
                    kind="veth",
                    peer={"ifname": "v1p1",
                          "net_ns_fd": "test_netns"})

        ► vlan

        VLAN interfaces require additional parameters, `vlan_id` and
        `link`, where `link` is a master interface to create VLAN on::

            ip.link("add",
                    ifname="v100",
                    kind="vlan",
                    link=ip.link_lookup(ifname="eth0")[0],
                    vlan_id=100)

        There is a possibility to create also 802.1ad interfaces::

            # create external vlan 802.1ad, s-tag
            ip.link("add",
                    ifname="v100s",
                    kind="vlan",
                    link=ip.link_lookup(ifname="eth0")[0],
                    vlan_id=100,
                    vlan_protocol=0x88a8)

            # create internal vlan 802.1q, c-tag
            ip.link("add",
                    ifname="v200c",
                    kind="vlan",
                    link=ip.link_lookup(ifname="v100s")[0],
                    vlan_id=200,
                    vlan_protocol=0x8100)


        ► vrf

        VRF interfaces (see linux/Documentation/networking/vrf.txt)::

            ip.link("add",
                    ifname="vrf-foo",
                    kind="vrf",
                    vrf_table=42)

        ► vxlan

        VXLAN interfaces are like VLAN ones, but require a bit more
        parameters::

            ip.link("add",
                    ifname="vx101",
                    kind="vxlan",
                    vxlan_link=ip.link_lookup(ifname="eth0")[0],
                    vxlan_id=101,
                    vxlan_group='239.1.1.1',
                    vxlan_ttl=16)

        All possible vxlan parameters are listed in the module
        `pyroute2.netlink.rtnl.ifinfmsg:... vxlan_data`.

        ► ipoib

        IPoIB driver provides an ability to create several ip interfaces
        on one interface.
        IPoIB interfaces requires the following parameter:

        `link` : The master interface to create IPoIB on.

        The following parameters can also be provided:

        * `pkey`- Inifiniband partition key the ip interface is associated with
        * `mode`- Underlying infiniband transport mode. One
          of:  ['datagram' ,'connected']
        * `umcast`- If set(1), multicast group membership for this interface is
          handled by user space.

        Example::

            ip.link("add",
                    ifname="ipoib1",
                    kind="ipoib",
                    link=ip.link_lookup(ifname="ib0")[0],
                    pkey=10)

        **set**

        Set interface attributes::

            # get interface index
            x = ip.link_lookup(ifname="eth0")[0]
            # put link down
            ip.link("set", index=x, state="down")
            # rename and set MAC addr
            ip.link("set", index=x, address="00:11:22:33:44:55", name="bala")
            # set MTU and TX queue length
            ip.link("set", index=x, mtu=1000, txqlen=2000)
            # bring link up
            ip.link("set", index=x, state="up")

        Seting bridge or tunnel attributes require `kind` to be
        specified in order to properly encode `IFLA_LINKINFO`::

            ip.link("set",
                    index=x,
                    kind="bridge",
                    br_forward_delay=2000)

            ip.link("set",
                    index=x,
                    kind="gre",
                    gre_local="10.0.0.1",
                    gre_remote="10.1.0.103")

        Keyword "state" is reserved. State can be "up" or "down",
        it is a shortcut::

            state="up":   flags=1, mask=1
            state="down": flags=0, mask=0

        SR-IOV virtual function setup::

            # get PF index
            x = ip.link_lookup(ifname="eth0")[0]
            # setup macaddr
            ip.link("set",
                    index=x,                          # PF index
                    vf={"vf": 0,                      # VF index
                        "mac": "00:11:22:33:44:55"})  # address
            # setup vlan
            ip.link("set",
                    index=x,           # PF index
                    vf={"vf": 0,       # VF index
                        "vlan": 100})  # the simplest case
            # setup QinQ
            ip.link("set",
                    index=x,                           # PF index
                    vf={"vf": 0,                       # VF index
                        "vlan": [{"vlan": 100,         # vlan id
                                  "proto": 0x88a8},    # 802.1ad
                                 {"vlan": 200,         # vlan id
                                  "proto": 0x8100}]})  # 802.1q

        **update**

        Almost the same as `set`, except it uses different flags
        and message type. Mostly does the same, but in some cases
        differs. If you're not sure what to use, use `set`.

        **del**

        Destroy the interface::

            ip.link("del", index=ip.link_lookup(ifname="dummy0")[0])

        **dump**

        Dump info for all interfaces

        **get**

        Get specific interface info::

            ip.link("get", index=ip.link_lookup(ifname="br0")[0])

        Get extended attributes like SR-IOV setup::

            ip.link("get", index=3, ext_mask=1)
        '''
        command_map = {
            'set': (RTM_NEWLINK, 'req'),
            'update': (RTM_SETLINK, 'create'),
            'add': (RTM_NEWLINK, 'create'),
            'del': (RTM_DELLINK, 'req'),
            'property_add': (RTM_NEWLINKPROP, 'append'),
            'property_del': (RTM_DELLINKPROP, 'req'),
            'remove': (RTM_DELLINK, 'req'),
            'delete': (RTM_DELLINK, 'req'),
            'dump': (RTM_GETLINK, 'dump'),
            'get': (RTM_GETLINK, 'get'),
        }
        dump_filter = None
        request = {}
        msg = ifinfmsg()

        if command == 'dump':
            dump_filter, kwarg = get_dump_filter(kwarg)

        if kwarg:
            if kwarg.get('kwarg_filter'):
                filters = kwarg['kwarg_filter']
            else:
                filters = [LinkFieldFilter(), LinkIPRouteFilter(command)]
            request = RequestProcessor(context=kwarg, prime=kwarg)
            for rfilter in filters:
                request.apply_filter(rfilter)
            request.finalize()

        msg_type, msg_flags = self.make_request_type(command, command_map)

        for field in msg.fields:
            msg[field[0]] = request.pop(field[0], 0)

        # attach NLA
        for key, value in request.items():
            nla = type(msg).name2nla(key)
            if msg.valid_nla(nla) and value is not None:
                msg['attrs'].append([nla, value])

        ret = self.nlm_request(msg, msg_type=msg_type, msg_flags=msg_flags)

        if command == 'dump' and dump_filter is not None:
            if isinstance(dump_filter, dict):
                dump_filter = (
                    RequestProcessor(context=dump_filter, prime=dump_filter)
                    .apply_filter(LinkFieldFilter())
                    .apply_filter(LinkIPRouteFilter('dump'))
                    .finalize()
                )
            ret = self.filter_messages(dump_filter, ret)

        if self.nlm_generator and not msg_flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    def addr(self, command, *argv, **kwarg):
        '''
        Address operations

        * command -- add, delete, replace, dump
        * index -- device index
        * address -- IPv4 or IPv6 address
        * mask -- address mask
        * family -- socket.AF_INET for IPv4 or socket.AF_INET6 for IPv6
        * scope -- the address scope, see /etc/iproute2/rt_scopes
        * kwarg -- dictionary, any ifaddrmsg field or NLA

        Later the method signature will be changed to::

            def addr(self, command, match=None, **kwarg):
                # the method body

        So only keyword arguments (except of the command) will be accepted.
        The reason for this change is an unification of API.

        Example::

            idx = 62
            ip.addr('add', index=idx, address='10.0.0.1', mask=24)
            ip.addr('add', index=idx, address='10.0.0.2', mask=24)

        With more NLAs::

            # explicitly set broadcast address
            ip.addr('add', index=idx,
                    address='10.0.0.3',
                    broadcast='10.0.0.255',
                    prefixlen=24)

            # make the secondary address visible to ifconfig: add label
            ip.addr('add', index=idx,
                    address='10.0.0.4',
                    broadcast='10.0.0.255',
                    prefixlen=24,
                    label='eth0:1')

        Configure p2p address on an interface::

            ip.addr('add', index=idx,
                    address='10.1.1.2',
                    mask=24,
                    local='10.1.1.1')
        '''
        if command in ('get', 'set'):
            return []
        ##
        # This block will be deprecated in a short term
        if argv:
            warnings.warn(
                'positional arguments for IPRoute.addr() are deprecated, '
                'use keyword arguments',
                DeprecationWarning,
            )
            converted_argv = zip(
                ('index', 'address', 'prefixlen', 'family', 'scope', 'match'),
                argv,
            )
            kwarg.update(converted_argv)
        if 'mask' in kwarg:
            warnings.warn(
                'usage of mask is deprecated, use prefixlen instead',
                DeprecationWarning,
            )
        command_map = {
            'add': (RTM_NEWADDR, 'create'),
            'del': (RTM_DELADDR, 'req'),
            'remove': (RTM_DELADDR, 'req'),
            'delete': (RTM_DELADDR, 'req'),
            'replace': (RTM_NEWADDR, 'replace'),
            'dump': (RTM_GETADDR, 'dump'),
        }
        dump_filter = None
        msg = ifaddrmsg()
        if command == 'dump':
            dump_filter, kwarg = get_dump_filter(kwarg)

        request = (
            RequestProcessor(context=kwarg, prime=kwarg)
            .apply_filter(AddressFieldFilter())
            .apply_filter(AddressIPRouteFilter(command))
            .finalize()
        )
        msg_type, msg_flags = self.make_request_type(command, command_map)

        for field in msg.fields:
            if field[0] != 'flags':  # Flags are supplied as NLA
                msg[field[0]] = request.pop(field[0], 0)

        # work on NLA
        for key, value in request.items():
            nla = ifaddrmsg.name2nla(key)
            if msg.valid_nla(nla) and value is not None:
                msg['attrs'].append([nla, value])

        ret = self.nlm_request(
            msg,
            msg_type=msg_type,
            msg_flags=msg_flags,
            terminate=lambda x: x['header']['type'] == NLMSG_ERROR,
        )
        if command == 'dump' and dump_filter is not None:
            ret = self.filter_messages(dump_filter, ret)

        if self.nlm_generator and not msg_flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    def tc(self, command, kind=None, index=0, handle=0, **kwarg):
        '''
        "Swiss knife" for traffic control. With the method you can
        add, delete or modify qdiscs, classes and filters.

        * command -- add or delete qdisc, class, filter.
        * kind -- a string identifier -- "sfq", "htb", "u32" and so on.
        * handle -- integer or string

        Command can be one of ("add", "del", "add-class", "del-class",
        "add-filter", "del-filter") (see `commands` dict in the code).

        Handle notice: traditional iproute2 notation, like "1:0", actually
        represents two parts in one four-bytes integer::

            1:0    ->    0x10000
            1:1    ->    0x10001
            ff:0   ->   0xff0000
            ffff:1 -> 0xffff0001

        Target notice: if your target is a class/qdisc that applies an
        algorithm that can only apply to upstream traffic profile, but your
        keys variable explicitly references a match that is only relevant for
        upstream traffic, the kernel will reject the filter.  Unless you're
        dealing with devices like IMQs

        For pyroute2 tc() you can use both forms: integer like 0xffff0000
        or string like 'ffff:0000'. By default, handle is 0, so you can add
        simple classless queues w/o need to specify handle. Ingress queue
        causes handle to be 0xffff0000.

        So, to set up sfq queue on interface 1, the function call
        will be like that::

            ip = IPRoute()
            ip.tc("add", "sfq", 1)

        Instead of string commands ("add", "del"...), you can use also
        module constants, `RTM_NEWQDISC`, `RTM_DELQDISC` and so on::

            ip = IPRoute()
            flags = NLM_F_REQUEST | NLM_F_ACK | NLM_F_CREATE | NLM_F_EXCL
            ip.tc((RTM_NEWQDISC, flags), "sfq", 1)

        It should be noted that "change", "change-class" and
        "change-filter" work like "replace", "replace-class" and
        "replace-filter", except they will fail if the node doesn't
        exist (while it would have been created by "replace"). This is
        not the same behaviour as with "tc" where "change" can be used
        to modify the value of some options while leaving the others
        unchanged. However, as not all entities support this
        operation, we believe the "change" commands as implemented
        here are more useful.


        Also available "modules" (returns tc plugins dict) and "help"
        commands::

            help(ip.tc("modules")["htb"])
            print(ip.tc("help", "htb"))
        '''
        if command == 'set':
            return

        if command == 'modules':
            return tc_plugins

        if command == 'help':
            p = tc_plugins.get(kind)
            if p is not None and hasattr(p, '__doc__'):
                return p.__doc__
            else:
                return 'No help available'

        command_map = {
            'add': (RTM_NEWQDISC, 'create'),
            'del': (RTM_DELQDISC, 'req'),
            'remove': (RTM_DELQDISC, 'req'),
            'delete': (RTM_DELQDISC, 'req'),
            'change': (RTM_NEWQDISC, 'change'),
            'replace': (RTM_NEWQDISC, 'replace'),
            'add-class': (RTM_NEWTCLASS, 'create'),
            'del-class': (RTM_DELTCLASS, 'req'),
            'change-class': (RTM_NEWTCLASS, 'change'),
            'replace-class': (RTM_NEWTCLASS, 'replace'),
            'add-filter': (RTM_NEWTFILTER, 'create'),
            'del-filter': (RTM_DELTFILTER, 'req'),
            'change-filter': (RTM_NEWTFILTER, 'change'),
            'replace-filter': (RTM_NEWTFILTER, 'replace'),
        }
        if command == 'del':
            if index == 0:
                index = [
                    x['index'] for x in self.get_links() if x['index'] != 1
                ]
            if isinstance(index, (list, tuple, set)):
                return list(chain(*(self.tc('del', index=x) for x in index)))
        command, flags = self.make_request_type(command, command_map)
        msg = tcmsg()
        # transform handle, parent and target, if needed:
        handle = transform_handle(handle)
        for item in ('parent', 'target', 'default'):
            if item in kwarg and kwarg[item] is not None:
                kwarg[item] = transform_handle(kwarg[item])
        msg['index'] = index
        msg['handle'] = handle
        if 'info' in kwarg:
            msg['info'] = kwarg['info']
        opts = kwarg.get('opts', None)
        ##
        #
        #
        if kind in tc_plugins:
            p = tc_plugins[kind]
            msg['parent'] = kwarg.pop('parent', getattr(p, 'parent', 0))
            if hasattr(p, 'fix_msg'):
                p.fix_msg(msg, kwarg)
            if kwarg:
                if command in (RTM_NEWTCLASS, RTM_DELTCLASS):
                    opts = p.get_class_parameters(kwarg)
                else:
                    opts = p.get_parameters(kwarg)
        else:
            msg['parent'] = kwarg.get('parent', TC_H_ROOT)

        if kind is not None:
            msg['attrs'].append(['TCA_KIND', kind])
        if opts is not None:
            msg['attrs'].append(['TCA_OPTIONS', opts])
        return tuple(self.nlm_request(msg, msg_type=command, msg_flags=flags))

    def route(self, command, **kwarg):
        '''
        Route operations.

        Keywords to set up rtmsg fields:

        * dst_len, src_len -- destination and source mask(see `dst` below)
        * tos -- type of service
        * table -- routing table
        * proto -- `redirect`, `boot`, `static` (see `rt_proto`)
        * scope -- routing realm
        * type -- `unicast`, `local`, etc. (see `rt_type`)

        `pyroute2/netlink/rtnl/rtmsg.py` rtmsg.nla_map:

        * table -- routing table to use (default: 254)
        * gateway -- via address
        * prefsrc -- preferred source IP address
        * dst -- the same as `prefix`
        * iif -- incoming traffic interface
        * oif -- outgoing traffic interface

        etc.

        One can specify mask not as `dst_len`, but as a part of `dst`,
        e.g.: `dst="10.0.0.0/24"`.

        Commands:

        **add**

        Example::

            ipr.route("add", dst="10.0.0.0/24", gateway="192.168.0.1")

        ...

        More `route()` examples. Blackhole route::

            ipr.route(
                "add",
                dst="10.0.0.0/24",
                type="blackhole",
            )

        Create a route with metrics::

            ipr.route(
                "add",
                dst="172.16.0.0/24",
                gateway="10.0.0.10",
                metrics={
                    "mtu": 1400,
                    "hoplimit": 16,
                },
            )

        Multipath route::

            ipr.route(
                "add",
                dst="10.0.0.0/24",
                multipath=[
                    {"gateway": "192.168.0.1", "hops": 2},
                    {"gateway": "192.168.0.2", "hops": 1},
                    {"gateway": "192.168.0.3"},
                ],
            )

        MPLS lwtunnel on eth0::

            ipr.route(
                "add",
                dst="10.0.0.0/24",
                oif=ip.link_lookup(ifname="eth0"),
                encap={
                    "type": "mpls",
                    "labels": "200/300",
                },
            )

        IPv6 next hop for IPv4 dst::

            ipr.route(
                "add",
                prefsrc="10.127.30.4",
                dst="172.16.0.0/24",
                via={"family": AF_INET6, "addr": "fe80::1337"},
                oif=ipr.link_lookup(ifname="eth0"),
                table=100,
            )

        Create MPLS route: push label::

            # $ sudo modprobe mpls_router
            # $ sudo sysctl net.mpls.platform_labels=1024
            ipr.route(
                "add",
                family=AF_MPLS,
                oif=ipr.link_lookup(ifname="eth0"),
                dst=0x200,
                newdst=[0x200, 0x300],
            )

        MPLS multipath::

            ipr.route(
                "add",
                dst="10.0.0.0/24",
                table=20,
                multipath=[
                    {
                        "gateway": "192.168.0.1",
                        "encap": {"type": "mpls", "labels": 200},
                    },
                    {
                        "ifindex": ipr.link_lookup(ifname="eth0"),
                        "encap": {"type": "mpls", "labels": 300},
                    },
                ],
            )

        MPLS target can be int, string, dict or list::

            "labels": 300    # simple label
            "labels": "300"  # the same
            "labels": (200, 300)  # stacked
            "labels": "200/300"   # the same

            # explicit label definition
            "labels": {
                "bos": 1,
                "label": 300,
                "tc": 0,
                "ttl": 16,
            }

        Create SEG6 tunnel encap mode (kernel >= 4.10)::

            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6",
                    "mode": "encap",
                    "segs": "2000::5,2000::6",
                },
            )

        Create SEG6 tunnel inline mode (kernel >= 4.10)::

            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6",
                    "mode": "inline",
                    "segs": ["2000::5", "2000::6"],
                },
            )

        Create SEG6 tunnel inline mode with hmac (kernel >= 4.10)::

            ipr.route(
                "add",
                dst="2001:0:0:22::2/128",
                oif=idx,
                encap={
                    "type": "seg6",
                    "mode": "inline",
                    "segs": "2000::5,2000::6,2000::7,2000::8",
                    "hmac": 0xf,
                },
            )

        Create SEG6 tunnel with ip4ip6 encapsulation (kernel >= 4.14)::

            ipr.route(
                "add",
                dst="172.16.0.0/24",
                oif=idx,
                encap={
                    "type": "seg6",
                    "mode": "encap",
                    "segs": "2000::5,2000::6",
                },
            )

        Create SEG6LOCAL tunnel End.DX4 action (kernel >= 4.14)::

            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6local",
                    "action": "End.DX4",
                    "nh4": "172.16.0.10",
                },
            )

        Create SEG6LOCAL tunnel End.DT6 action (kernel >= 4.14)::

            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6local",
                    "action": "End.DT6",
                    "table": "10",
                },
            )

        Create SEG6LOCAL tunnel End.DT4 action (kernel >= 5.11)::

            # $ sudo modprobe vrf
            # $ sudo sysctl -w net.vrf.strict_mode=1
            ipr.link(
                "add",
                ifname="vrf-foo",
                kind="vrf",
                vrf_table=10,
            )
            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6local",
                    "action": "End.DT4",
                    "vrf_table": 10,
                },
            )

        Create SEG6LOCAL tunnel End.DT46 action (kernel >= 5.14)::

            # $ sudo modprobe vrf
            # $ sudo sysctl -w net.vrf.strict_mode=1

            ip.link('add',
                    ifname='vrf-foo',
                    kind='vrf',
                    vrf_table=10)

            ip.route('add',
                     dst='2001:0:0:10::2/128',
                     oif=idx,
                     encap={'type': 'seg6local',
                            'action': 'End.DT46',
                            'vrf_table': 10})

        Create SEG6LOCAL tunnel End.B6 action (kernel >= 4.14)::

            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6local",
                    "action": "End.B6",
                    "srh": {"segs": "2000::5,2000::6"},
                },
            )

        Create SEG6LOCAL tunnel End.B6 action with hmac (kernel >= 4.14)::

            ipr.route(
                "add",
                dst="2001:0:0:10::2/128",
                oif=idx,
                encap={
                    "type": "seg6local",
                    "action": "End.B6",
                    "srh": {
                        "segs": "2000::5,2000::6",
                        "hmac": 0xf,
                    },
                },
            )

        **change**, **replace**, **append**

        Commands `change`, `replace` and `append` have the same meanings
        as in ip-route(8): `change` modifies only existing route, while
        `replace` creates a new one, if there is no such route yet.
        `append` allows to create an IPv6 multipath route.

        **del**

        Remove the route. The same syntax as for **add**.

        **get**

        Get route by spec.

        **dump**

        Dump all routes.
        '''
        # transform kwarg
        if command in ('add', 'set', 'replace', 'change', 'append'):
            kwarg['proto'] = kwarg.get('proto', 'static') or 'static'
            kwarg['type'] = kwarg.get('type', 'unicast') or 'unicast'
        if 'match' not in kwarg and command in ('dump', 'show'):
            match = kwarg
        else:
            match = kwarg.pop('match', None)
        callback = kwarg.pop('callback', None)
        request = (
            RequestProcessor(context=kwarg, prime=kwarg)
            .apply_filter(RouteFieldFilter())
            .apply_filter(RouteIPRouteFilter(command))
            .finalize()
        )
        kwarg = request

        command_map = {
            'add': (RTM_NEWROUTE, 'create'),
            'set': (RTM_NEWROUTE, 'replace'),
            'replace': (RTM_NEWROUTE, 'replace'),
            'change': (RTM_NEWROUTE, 'change'),
            'append': (RTM_NEWROUTE, 'append'),
            'del': (RTM_DELROUTE, 'req'),
            'remove': (RTM_DELROUTE, 'req'),
            'delete': (RTM_DELROUTE, 'req'),
            'get': (RTM_GETROUTE, 'get'),
            'show': (RTM_GETROUTE, 'dump'),
            'dump': (RTM_GETROUTE, 'dump'),
        }
        (command, flags) = self.make_request_type(command, command_map)
        msg = rtmsg()

        # table is mandatory without strict_check; by default == 254
        # if table is not defined in kwarg, save it there
        # also for nla_attr. Do not set it in strict_check, use
        # NLA instead
        if not self.strict_check:
            table = kwarg.get('table', 254)
            msg['table'] = table if table <= 255 else 252
        msg['family'] = kwarg.pop('family', AF_INET)
        msg['scope'] = kwarg.pop('scope', rt_scope['universe'])
        msg['dst_len'] = kwarg.pop('dst_len', None) or kwarg.pop('mask', 0)
        msg['src_len'] = kwarg.pop('src_len', 0)
        msg['tos'] = kwarg.pop('tos', 0)
        msg['flags'] = kwarg.pop('flags', 0)
        msg['type'] = kwarg.pop('type', rt_type['unspec'])
        msg['proto'] = kwarg.pop('proto', rt_proto['unspec'])
        msg['attrs'] = []

        if msg['family'] == AF_MPLS:
            for key in tuple(kwarg):
                if key not in ('dst', 'newdst', 'via', 'multipath', 'oif'):
                    kwarg.pop(key)

        for key in kwarg:
            nla = rtmsg.name2nla(key)
            if nla == 'RTA_DST' and not kwarg[key]:
                continue
            if kwarg[key] is not None:
                msg['attrs'].append([nla, kwarg[key]])
                # fix IP family, if needed
                if msg['family'] in (AF_UNSPEC, 255):
                    if key == 'multipath' and len(kwarg[key]) > 0:
                        hop = kwarg[key][0]
                        attrs = hop.get('attrs', [])
                        for attr in attrs:
                            if attr[0] == 'RTA_GATEWAY':
                                msg['family'] = (
                                    AF_INET6
                                    if attr[1].find(':') >= 0
                                    else AF_INET
                                )
                                break

        ret = self.nlm_request(
            msg, msg_type=command, msg_flags=flags, callback=callback
        )
        if match:
            if isinstance(match, dict):
                match = (
                    RequestProcessor(context=match, prime=match)
                    .apply_filter(RouteFieldFilter(add_defaults=False))
                    .apply_filter(RouteIPRouteFilter('dump'))
                    .finalize()
                )
            ret = self.filter_messages(match, ret)

        if self.nlm_generator and not flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    def rule(self, command, **kwarg):
        '''
        Rule operations

            - command — add, delete
            - table — 0 < table id < 253
            - priority — 0 < rule's priority < 32766
            - action — type of rule, default 'FR_ACT_NOP' (see fibmsg.py)
            - rtscope — routing scope, default RT_SCOPE_UNIVERSE
                `(RT_SCOPE_UNIVERSE|RT_SCOPE_SITE|\
                RT_SCOPE_LINK|RT_SCOPE_HOST|RT_SCOPE_NOWHERE)`
            - family — rule's family (socket.AF_INET (default) or
                socket.AF_INET6)
            - src — IP source for Source Based (Policy Based) routing's rule
            - dst — IP for Destination Based (Policy Based) routing's rule
            - src_len — Mask for Source Based (Policy Based) routing's rule
            - dst_len — Mask for Destination Based (Policy Based) routing's
                rule
            - iifname — Input interface for Interface Based (Policy Based)
                routing's rule
            - oifname — Output interface for Interface Based (Policy Based)
                routing's rule
            - uid_range — Range of user identifiers, a string like "1000:1234"
            - dport_range — Range of destination ports, a string like "80-120"
            - sport_range — Range of source ports, as a string like "80-120"

        All packets route via table 10::

            # 32000: from all lookup 10
            # ...
            ip.rule('add', table=10, priority=32000)

        Default action::

            # 32001: from all lookup 11 unreachable
            # ...
            iproute.rule('add',
                         table=11,
                         priority=32001,
                         action='FR_ACT_UNREACHABLE')

        Use source address to choose a routing table::

            # 32004: from 10.64.75.141 lookup 14
            # ...
            iproute.rule('add',
                         table=14,
                         priority=32004,
                         src='10.64.75.141')

        Use dst address to choose a routing table::

            # 32005: from 10.64.75.141/24 lookup 15
            # ...
            iproute.rule('add',
                         table=15,
                         priority=32005,
                         dst='10.64.75.141',
                         dst_len=24)

        Match fwmark::

            # 32006: from 10.64.75.141 fwmark 0xa lookup 15
            # ...
            iproute.rule('add',
                         table=15,
                         priority=32006,
                         dst='10.64.75.141',
                         fwmark=10)
        '''
        if command == 'set':
            return

        if 'match' not in kwarg and command == 'dump':
            match = kwarg
        else:
            match = kwarg.pop('match', None)
        request = (
            RequestProcessor(context=kwarg, prime=kwarg)
            .apply_filter(RuleFieldFilter())
            .apply_filter(RuleIPRouteFilter(command))
            .finalize()
        )

        command_map = {
            'add': (RTM_NEWRULE, 'create'),
            'del': (RTM_DELRULE, 'req'),
            'remove': (RTM_DELRULE, 'req'),
            'delete': (RTM_DELRULE, 'req'),
            'dump': (RTM_GETRULE, 'dump'),
        }
        command, flags = self.make_request_type(command, command_map)

        msg = fibmsg()
        table = request.get('table', 0)
        msg['table'] = table if table <= 255 else 252
        for key in ('family', 'src_len', 'dst_len', 'action', 'tos', 'flags'):
            msg[key] = request.pop(key, 0)
        msg['attrs'] = []

        for key in request:
            if command == RTM_GETRULE and self.strict_check:
                if key in ("match", "priority"):
                    continue
            nla = fibmsg.name2nla(key)
            if request[key] is not None:
                msg['attrs'].append([nla, request[key]])

        ret = self.nlm_request(msg, msg_type=command, msg_flags=flags)

        if match:
            if isinstance(match, dict):
                match = (
                    RequestProcessor(context=match, prime=match)
                    .apply_filter(RuleFieldFilter())
                    .apply_filter(RuleIPRouteFilter('dump'))
                    .finalize()
                )
            ret = self.filter_messages(match, ret)

        if self.nlm_generator and not flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    def stats(self, command, **kwarg):
        '''
        Stats prototype.
        '''
        if (command == 'dump') and ('match' not in kwarg):
            match = kwarg
        else:
            match = kwarg.pop('match', None)

        command_map = {
            'dump': (RTM_GETSTATS, 'dump'),
            'get': (RTM_GETSTATS, 'get'),
        }
        command, flags = self.make_request_type(command, command_map)

        msg = ifstatsmsg()
        msg['filter_mask'] = kwarg.get('filter_mask', 31)
        msg['ifindex'] = kwarg.get('ifindex', 0)

        ret = self.nlm_request(msg, msg_type=command, msg_flags=flags)
        if match is not None:
            ret = self.filter_messages(match, ret)

        if self.nlm_generator and not flags & NLM_F_DUMP == NLM_F_DUMP:
            ret = tuple(ret)

        return ret

    # 8<---------------------------------------------------------------


class IPBatch(RTNL_API, IPBatchSocket):
    '''
    Netlink requests compiler. Does not send any requests, but
    instead stores them in the internal binary buffer. The
    contents of the buffer can be used to send batch requests,
    to test custom netlink parsers and so on.

    Uses `RTNL_API` and provides all the same API as normal
    `IPRoute` objects::

        # create the batch compiler
        ipb = IPBatch()
        # compile requests into the internal buffer
        ipb.link("add", index=550, ifname="test", kind="dummy")
        ipb.link("set", index=550, state="up")
        ipb.addr("add", index=550, address="10.0.0.2", mask=24)
        # save the buffer
        data = ipb.batch
        # reset the buffer
        ipb.reset()
        ...
        # send the buffer
        IPRoute().sendto(data, (0, 0))

    '''

    pass


class IPRoute(LAB_API, RTNL_API, IPRSocket):
    '''
    Regular ordinary utility class, see RTNL API for the list of methods.
    '''

    pass


class RawIPRoute(RTNL_API, RawIPRSocket):
    '''
    The same as `IPRoute`, but does not use the netlink proxy.
    Thus it can not manage e.g. tun/tap interfaces.
    '''

    pass


class ChaoticIPRoute(RTNL_API, ChaoticIPRSocket):
    '''
    IPRoute interface for chaotic tests - raising exceptions randomly.
    '''

    pass
