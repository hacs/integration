'''
ipset support.

This module is tested with hash:ip, hash:net, list:set and several
other ipset structures (like hash:net,iface). There is no guarantee
that this module is working with all available ipset modules.

It supports almost all kernel commands (create, destroy, flush,
rename, swap, test...)
'''

import errno
import socket

from pyroute2.common import basestring
from pyroute2.netlink import (
    NETLINK_NETFILTER,
    NLM_F_ACK,
    NLM_F_DUMP,
    NLM_F_EXCL,
    NLM_F_REQUEST,
    NLMSG_ERROR,
)
from pyroute2.netlink.exceptions import IPSetError, NetlinkError
from pyroute2.netlink.nfnetlink import NFNL_SUBSYS_IPSET
from pyroute2.netlink.nfnetlink.ipset import (
    IPSET_CMD_ADD,
    IPSET_CMD_CREATE,
    IPSET_CMD_DEL,
    IPSET_CMD_DESTROY,
    IPSET_CMD_FLUSH,
    IPSET_CMD_GET_BYINDEX,
    IPSET_CMD_GET_BYNAME,
    IPSET_CMD_HEADER,
    IPSET_CMD_LIST,
    IPSET_CMD_PROTOCOL,
    IPSET_CMD_RENAME,
    IPSET_CMD_SWAP,
    IPSET_CMD_TEST,
    IPSET_CMD_TYPE,
    IPSET_ERR_BUSY,
    IPSET_ERR_COMMENT,
    IPSET_ERR_COUNTER,
    IPSET_ERR_EXIST,
    IPSET_ERR_EXIST_SETNAME2,
    IPSET_ERR_FIND_TYPE,
    IPSET_ERR_INVALID_CIDR,
    IPSET_ERR_INVALID_FAMILY,
    IPSET_ERR_INVALID_MARKMASK,
    IPSET_ERR_INVALID_NETMASK,
    IPSET_ERR_IPADDR_IPV4,
    IPSET_ERR_IPADDR_IPV6,
    IPSET_ERR_MAX_SETS,
    IPSET_ERR_PROTOCOL,
    IPSET_ERR_REFERENCED,
    IPSET_ERR_SKBINFO,
    IPSET_ERR_TIMEOUT,
    IPSET_ERR_TYPE_MISMATCH,
    IPSET_FLAG_IFACE_WILDCARD,
    IPSET_FLAG_PHYSDEV,
    IPSET_FLAG_WITH_COMMENT,
    IPSET_FLAG_WITH_COUNTERS,
    IPSET_FLAG_WITH_FORCEADD,
    IPSET_FLAG_WITH_SKBINFO,
    ipset_msg,
)
from pyroute2.netlink.nlsocket import NetlinkSocket


def _nlmsg_error(msg):
    return msg['header']['type'] == NLMSG_ERROR


class PortRange(object):
    """A simple container for port range with optional protocol

    Note that optional protocol parameter is not supported by all
    kernel ipset modules using ports. On the other hand, it's sometimes
    mandatory to set it (like for hash:net,port ipsets)

    Example::

        udp_proto = socket.getprotobyname("udp")
        port_range = PortRange(1000, 2000, protocol=udp_proto)
        ipset.create("foo", stype="hash:net,port")
        ipset.add("foo", ("192.0.2.0/24", port_range), etype="net,port")
        ipset.test("foo", ("192.0.2.0/24", port_range), etype="net,port")
    """

    def __init__(self, begin, end, protocol=None):
        self.begin = begin
        self.end = end
        self.protocol = protocol


class PortEntry(object):
    """A simple container for port entry with optional protocol"""

    def __init__(self, port, protocol=None):
        self.port = port
        self.protocol = protocol


class IPSet(NetlinkSocket):
    '''
    NFNetlink socket (family=NETLINK_NETFILTER).

    Implements API to the ipset functionality.
    '''

    policy = {
        IPSET_CMD_PROTOCOL: ipset_msg,
        IPSET_CMD_LIST: ipset_msg,
        IPSET_CMD_TYPE: ipset_msg,
        IPSET_CMD_HEADER: ipset_msg,
        IPSET_CMD_GET_BYNAME: ipset_msg,
        IPSET_CMD_GET_BYINDEX: ipset_msg,
    }

    attr_map = {
        'iface': 'IPSET_ATTR_IFACE',
        'mark': 'IPSET_ATTR_MARK',
        'set': 'IPSET_ATTR_NAME',
        'mac': 'IPSET_ATTR_ETHER',
        'port': 'IPSET_ATTR_PORT',
        ('ip_from', 1): 'IPSET_ATTR_IP_FROM',
        ('ip_from', 2): 'IPSET_ATTR_IP2',
        ('cidr', 1): 'IPSET_ATTR_CIDR',
        ('cidr', 2): 'IPSET_ATTR_CIDR2',
        ('ip_to', 1): 'IPSET_ATTR_IP_TO',
        ('ip_to', 2): 'IPSET_ATTR_IP2_TO',
    }

    def __init__(self, version=None, attr_revision=None, nfgen_family=2):
        super(IPSet, self).__init__(family=NETLINK_NETFILTER)
        policy = dict(
            [
                (x | (NFNL_SUBSYS_IPSET << 8), y)
                for (x, y) in self.policy.items()
            ]
        )
        self.register_policy(policy)
        self._nfgen_family = nfgen_family
        if version is None:
            msg = self.get_proto_version()
            version = msg[0].get_attr('IPSET_ATTR_PROTOCOL')
        self._proto_version = version
        self._attr_revision = attr_revision

    def request(
        self,
        msg,
        msg_type,
        msg_flags=NLM_F_REQUEST | NLM_F_DUMP,
        terminate=None,
    ):
        msg['nfgen_family'] = self._nfgen_family
        try:
            return tuple(
                self.nlm_request(
                    msg,
                    msg_type | (NFNL_SUBSYS_IPSET << 8),
                    msg_flags,
                    terminate=terminate,
                )
            )
        except NetlinkError as err:
            raise _IPSetError(err.code, cmd=msg_type)

    def headers(self, name, **kwargs):
        '''
        Get headers of the named ipset. It can be used to test if one ipset
        exists, since it returns a no such file or directory.
        '''
        return self._list_or_headers(IPSET_CMD_HEADER, name=name, **kwargs)

    def get_proto_version(self, version=6):
        '''
        Get supported protocol version by kernel.

        version parameter allow to set mandatory (but unused?)
        IPSET_ATTR_PROTOCOL netlink attribute in the request.
        '''
        msg = ipset_msg()
        msg['attrs'] = [['IPSET_ATTR_PROTOCOL', version]]
        return self.request(msg, IPSET_CMD_PROTOCOL)

    def list(self, *argv, **kwargs):
        '''
        List installed ipsets. If `name` is provided, list
        the named ipset or return an empty list.

        Be warned: netlink does not return an error if given name does not
        exit, you will receive an empty list.
        '''
        if argv:
            kwargs['name'] = argv[0]
        return self._list_or_headers(IPSET_CMD_LIST, **kwargs)

    def _list_or_headers(self, cmd, name=None, flags=None):
        msg = ipset_msg()
        msg['attrs'] = [['IPSET_ATTR_PROTOCOL', self._proto_version]]
        if name is not None:
            msg['attrs'].append(['IPSET_ATTR_SETNAME', name])
        if flags is not None:
            msg['attrs'].append(['IPSET_ATTR_FLAGS', flags])
        return self.request(msg, cmd)

    def destroy(self, name=None):
        '''
        Destroy one (when name is set) or all ipset (when name is None)
        '''
        msg = ipset_msg()
        msg['attrs'] = [['IPSET_ATTR_PROTOCOL', self._proto_version]]
        if name is not None:
            msg['attrs'].append(['IPSET_ATTR_SETNAME', name])
        return self.request(
            msg,
            IPSET_CMD_DESTROY,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK | NLM_F_EXCL,
            terminate=_nlmsg_error,
        )

    def create(
        self,
        name,
        stype='hash:ip',
        family=socket.AF_INET,
        exclusive=True,
        counters=False,
        comment=False,
        maxelem=None,
        forceadd=False,
        hashsize=None,
        timeout=None,
        bitmap_ports_range=None,
        size=None,
        skbinfo=False,
    ):
        '''
        Create an ipset `name` of type `stype`, by default
        `hash:ip`.

        Common ipset options are supported:

        * exclusive -- if set, raise an error if the ipset exists
        * counters -- enable data/packets counters
        * comment -- enable comments capability
        * maxelem -- max size of the ipset
        * forceadd -- you should refer to the ipset manpage
        * hashsize -- size of the hashtable (if any)
        * timeout -- enable and set a default value for entries (if not None)
        * bitmap_ports_range -- set the specified inclusive portrange for
                                the bitmap ipset structure (0, 65536)
        * size -- Size of the list:set, the default is 8
        * skbinfo -- enable skbinfo capability
        '''
        excl_flag = NLM_F_EXCL if exclusive else 0
        msg = ipset_msg()
        cadt_flags = 0
        if counters:
            cadt_flags |= IPSET_FLAG_WITH_COUNTERS
        if comment:
            cadt_flags |= IPSET_FLAG_WITH_COMMENT
        if forceadd:
            cadt_flags |= IPSET_FLAG_WITH_FORCEADD
        if skbinfo:
            cadt_flags |= IPSET_FLAG_WITH_SKBINFO

        if stype == 'bitmap:port' and bitmap_ports_range is None:
            raise ValueError('Missing value bitmap_ports_range')

        data = {'attrs': []}
        if cadt_flags:
            data['attrs'] += [['IPSET_ATTR_CADT_FLAGS', cadt_flags]]
        if maxelem is not None:
            data['attrs'] += [['IPSET_ATTR_MAXELEM', maxelem]]
        if hashsize is not None:
            data['attrs'] += [["IPSET_ATTR_HASHSIZE", hashsize]]
        elif size is not None and stype == 'list:set':
            data['attrs'] += [['IPSET_ATTR_SIZE', size]]
        if timeout is not None:
            data['attrs'] += [["IPSET_ATTR_TIMEOUT", timeout]]
        if bitmap_ports_range is not None and stype == 'bitmap:port':
            # Set the bitmap range A bitmap type of set
            # can store up to 65536 entries
            if isinstance(bitmap_ports_range, PortRange):
                data['attrs'] += [
                    ['IPSET_ATTR_PORT_FROM', bitmap_ports_range.begin]
                ]
                data['attrs'] += [
                    ['IPSET_ATTR_PORT_TO', bitmap_ports_range.end]
                ]
            else:
                data['attrs'] += [
                    ['IPSET_ATTR_PORT_FROM', bitmap_ports_range[0]]
                ]
                data['attrs'] += [
                    ['IPSET_ATTR_PORT_TO', bitmap_ports_range[1]]
                ]

        if self._attr_revision is None:
            # Get the last revision supported by kernel
            revision = self.get_supported_revisions(stype)[1]
        else:
            revision = self._attr_revision
        msg['attrs'] = [
            ['IPSET_ATTR_PROTOCOL', self._proto_version],
            ['IPSET_ATTR_SETNAME', name],
            ['IPSET_ATTR_TYPENAME', stype],
            ['IPSET_ATTR_FAMILY', family],
            ['IPSET_ATTR_REVISION', revision],
            ["IPSET_ATTR_DATA", data],
        ]

        return self.request(
            msg,
            IPSET_CMD_CREATE,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK | excl_flag,
            terminate=_nlmsg_error,
        )

    @staticmethod
    def _family_to_version(family):
        if family is not None:
            if family == socket.AF_INET:
                return 'IPSET_ATTR_IPADDR_IPV4'
            elif family == socket.AF_INET6:
                return 'IPSET_ATTR_IPADDR_IPV6'
            elif family == socket.AF_UNSPEC:
                return None
            raise TypeError('unknown family')

    def _entry_to_data_attrs(self, entry, etype, ip_version):
        attrs = []
        ip_count = 0

        if etype == 'set':
            attrs += [['IPSET_ATTR_NAME', entry]]
            return attrs

        # We support string (for one element, and for users calling this
        # function like a command line), and tuple/list
        if isinstance(entry, basestring):
            entry = entry.split(',')
        if isinstance(entry, (int, PortRange, PortEntry)):
            entry = [entry]

        for e, t in zip(entry, etype.split(',')):
            if t in ('ip', 'net'):
                ip_count += 1
                if t == 'net':
                    if '/' in e:
                        e, cidr = e.split('/')
                        attrs += [
                            [self.attr_map[('cidr', ip_count)], int(cidr)]
                        ]
                    elif '-' in e:
                        e, to = e.split('-')
                        attrs += [
                            [
                                self.attr_map[('ip_to', ip_count)],
                                {'attrs': [[ip_version, to]]},
                            ]
                        ]
                attrs += [
                    [
                        self.attr_map[('ip_from', ip_count)],
                        {'attrs': [[ip_version, e]]},
                    ]
                ]
            elif t == "port":
                if isinstance(e, PortRange):
                    attrs += [['IPSET_ATTR_PORT_FROM', e.begin]]
                    attrs += [['IPSET_ATTR_PORT_TO', e.end]]
                    if e.protocol is not None:
                        attrs += [['IPSET_ATTR_PROTO', e.protocol]]
                elif isinstance(e, PortEntry):
                    attrs += [['IPSET_ATTR_PORT', e.port]]
                    if e.protocol is not None:
                        attrs += [['IPSET_ATTR_PROTO', e.protocol]]
                else:
                    attrs += [[self.attr_map[t], e]]
            else:
                attrs += [[self.attr_map[t], e]]

        return attrs

    def _add_delete_test(
        self,
        name,
        entry,
        family,
        cmd,
        exclusive,
        comment=None,
        timeout=None,
        etype="ip",
        packets=None,
        bytes=None,
        skbmark=None,
        skbprio=None,
        skbqueue=None,
        wildcard=False,
        physdev=False,
    ):
        excl_flag = NLM_F_EXCL if exclusive else 0
        adt_flags = 0
        if wildcard:
            adt_flags |= IPSET_FLAG_IFACE_WILDCARD
        if physdev:
            adt_flags |= IPSET_FLAG_PHYSDEV

        ip_version = self._family_to_version(family)
        data_attrs = self._entry_to_data_attrs(entry, etype, ip_version)
        if comment is not None:
            data_attrs += [
                ["IPSET_ATTR_COMMENT", comment],
                ["IPSET_ATTR_CADT_LINENO", 0],
            ]
        if timeout is not None:
            data_attrs += [["IPSET_ATTR_TIMEOUT", timeout]]
        if bytes is not None:
            data_attrs += [["IPSET_ATTR_BYTES", bytes]]
        if packets is not None:
            data_attrs += [["IPSET_ATTR_PACKETS", packets]]
        if skbmark is not None:
            data_attrs += [["IPSET_ATTR_SKBMARK", skbmark]]
        if skbprio is not None:
            data_attrs += [["IPSET_ATTR_SKBPRIO", skbprio]]
        if skbqueue is not None:
            data_attrs += [["IPSET_ATTR_SKBQUEUE", skbqueue]]
        if adt_flags:
            data_attrs += [["IPSET_ATTR_CADT_FLAGS", adt_flags]]
        msg = ipset_msg()
        msg['attrs'] = [
            ['IPSET_ATTR_PROTOCOL', self._proto_version],
            ['IPSET_ATTR_SETNAME', name],
            ['IPSET_ATTR_DATA', {'attrs': data_attrs}],
        ]

        return self.request(
            msg,
            cmd,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK | excl_flag,
            terminate=_nlmsg_error,
        )

    def add(
        self,
        name,
        entry,
        family=socket.AF_INET,
        exclusive=True,
        comment=None,
        timeout=None,
        etype="ip",
        skbmark=None,
        skbprio=None,
        skbqueue=None,
        wildcard=False,
        **kwargs
    ):
        '''
        Add a member to the ipset.

        etype is the entry type that you add to the ipset. It's related to
        the ipset type. For example, use "ip" for one hash:ip or bitmap:ip
        ipset.

        When your ipset store a tuple, like "hash:net,iface", you must use a
        comma a separator (etype="net,iface")

        entry is a string for "ip" and "net" objects. For ipset with several
        dimensions, you must use a tuple (or a list) of objects.

        "port" type is specific, since you can use integer of specialized
        containers like :class:`PortEntry` and :class:`PortRange`

        Examples::

            ipset = IPSet()
            ipset.create("foo", stype="hash:ip")
            ipset.add("foo", "198.51.100.1", etype="ip")

            ipset = IPSet()
            ipset.create("bar", stype="bitmap:port",
                         bitmap_ports_range=(1000, 2000))
            ipset.add("bar", 1001, etype="port")
            ipset.add("bar", PortRange(1500, 2000), etype="port")

            ipset = IPSet()
            import socket
            protocol = socket.getprotobyname("tcp")
            ipset.create("foobar", stype="hash:net,port")
            port_entry = PortEntry(80, protocol=protocol)
            ipset.add("foobar", ("198.51.100.0/24", port_entry),
                      etype="net,port")

        wildcard option enable kernel wildcard matching on interface
        name for net,iface entries.
        '''
        return self._add_delete_test(
            name,
            entry,
            family,
            IPSET_CMD_ADD,
            exclusive,
            comment=comment,
            timeout=timeout,
            etype=etype,
            skbmark=skbmark,
            skbprio=skbprio,
            skbqueue=skbqueue,
            wildcard=wildcard,
            **kwargs
        )

    def delete(
        self, name, entry, family=socket.AF_INET, exclusive=True, etype="ip"
    ):
        '''
        Delete a member from the ipset.

        See :func:`add` method for more information on etype.
        '''
        return self._add_delete_test(
            name, entry, family, IPSET_CMD_DEL, exclusive, etype=etype
        )

    def test(self, name, entry, family=socket.AF_INET, etype="ip"):
        '''
        Test if entry is part of an ipset

        See :func:`add` method for more information on etype.
        '''
        try:
            self._add_delete_test(
                name, entry, family, IPSET_CMD_TEST, False, etype=etype
            )
            return True
        except IPSetError as e:
            if e.code == IPSET_ERR_EXIST:
                return False
            raise e

    def swap(self, set_a, set_b):
        '''
        Swap two ipsets. They must have compatible content type.
        '''
        msg = ipset_msg()
        msg['attrs'] = [
            ['IPSET_ATTR_PROTOCOL', self._proto_version],
            ['IPSET_ATTR_SETNAME', set_a],
            ['IPSET_ATTR_TYPENAME', set_b],
        ]
        return self.request(
            msg,
            IPSET_CMD_SWAP,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK,
            terminate=_nlmsg_error,
        )

    def flush(self, name=None):
        '''
        Flush all ipsets. When name is set, flush only this ipset.
        '''
        msg = ipset_msg()
        msg['attrs'] = [['IPSET_ATTR_PROTOCOL', self._proto_version]]
        if name is not None:
            msg['attrs'].append(['IPSET_ATTR_SETNAME', name])
        return self.request(
            msg,
            IPSET_CMD_FLUSH,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK,
            terminate=_nlmsg_error,
        )

    def rename(self, name_src, name_dst):
        '''
        Rename the ipset.
        '''
        msg = ipset_msg()
        msg['attrs'] = [
            ['IPSET_ATTR_PROTOCOL', self._proto_version],
            ['IPSET_ATTR_SETNAME', name_src],
            ['IPSET_ATTR_TYPENAME', name_dst],
        ]
        return self.request(
            msg,
            IPSET_CMD_RENAME,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK,
            terminate=_nlmsg_error,
        )

    def _get_set_by(self, cmd, value):
        # Check that IPSet version is supported
        if self._proto_version < 7:
            raise NotImplementedError()

        msg = ipset_msg()
        if cmd == IPSET_CMD_GET_BYNAME:
            msg['attrs'] = [
                ['IPSET_ATTR_PROTOCOL', self._proto_version],
                ['IPSET_ATTR_SETNAME', value],
            ]

        if cmd == IPSET_CMD_GET_BYINDEX:
            msg['attrs'] = [
                ['IPSET_ATTR_PROTOCOL', self._proto_version],
                ['IPSET_ATTR_INDEX', value],
            ]
        return self.request(msg, cmd)

    def get_set_byname(self, name):
        '''
        Get a set by its name
        '''

        return self._get_set_by(IPSET_CMD_GET_BYNAME, name)

    def get_set_byindex(self, index):
        '''
        Get a set by its index
        '''

        return self._get_set_by(IPSET_CMD_GET_BYINDEX, index)

    def get_supported_revisions(self, stype, family=socket.AF_INET):
        '''
        Return minimum and maximum of revisions supported by the kernel.

        Each ipset module (like hash:net, hash:ip, etc) has several
        revisions. Newer revisions often have more features or more
        performances. Thanks to this call, you can ask the kernel
        the list of supported revisions.

        You can manually set/force revisions used in IPSet constructor.

        Example::

            ipset = IPSet()
            ipset.get_supported_revisions("hash:net")

            ipset.get_supported_revisions("hash:net,port,net")
        '''
        msg = ipset_msg()
        msg['attrs'] = [
            ['IPSET_ATTR_PROTOCOL', self._proto_version],
            ['IPSET_ATTR_TYPENAME', stype],
            ['IPSET_ATTR_FAMILY', family],
        ]
        response = self.request(
            msg,
            IPSET_CMD_TYPE,
            msg_flags=NLM_F_REQUEST | NLM_F_ACK,
            terminate=_nlmsg_error,
        )

        min_revision = response[0].get_attr("IPSET_ATTR_PROTOCOL_MIN")
        max_revision = response[0].get_attr("IPSET_ATTR_REVISION")
        return min_revision, max_revision


class _IPSetError(IPSetError):
    '''
    Proxy class to not import all specifics ipset code in exceptions.py

    Out of the ipset module, a caller should use parent class instead
    '''

    def __init__(self, code, msg=None, cmd=None):
        if code in self.base_map:
            msg = self.base_map[code]
        elif cmd in self.cmd_map:
            error_map = self.cmd_map[cmd]
            if code in error_map:
                msg = error_map[code]
        super(_IPSetError, self).__init__(code, msg)

    base_map = {
        IPSET_ERR_PROTOCOL: "Kernel error received:" " ipset protocol error",
        IPSET_ERR_INVALID_CIDR: "The value of the CIDR parameter of"
        " the IP address is invalid",
        IPSET_ERR_TIMEOUT: "Timeout cannot be used: set was created"
        " without timeout support",
        IPSET_ERR_IPADDR_IPV4: "An IPv4 address is expected, but"
        " not received",
        IPSET_ERR_IPADDR_IPV6: "An IPv6 address is expected, but"
        " not received",
        IPSET_ERR_COUNTER: "Packet/byte counters cannot be used:"
        " set was created without counter support",
        IPSET_ERR_COMMENT: "Comment string is too long!",
        IPSET_ERR_SKBINFO: "Skbinfo mapping cannot be used: "
        " set was created without skbinfo support",
    }

    c_map = {
        errno.EEXIST: "Set cannot be created: set with the same"
        " name already exists",
        IPSET_ERR_FIND_TYPE: "Kernel error received: "
        "set type not supported",
        IPSET_ERR_MAX_SETS: "Kernel error received: maximal number of"
        " sets reached, cannot create more.",
        IPSET_ERR_INVALID_NETMASK: "The value of the netmask parameter"
        " is invalid",
        IPSET_ERR_INVALID_MARKMASK: "The value of the markmask parameter"
        " is invalid",
        IPSET_ERR_INVALID_FAMILY: "Protocol family not supported by the"
        " set type",
    }

    destroy_map = {
        IPSET_ERR_BUSY: "Set cannot be destroyed: it is in use"
        " by a kernel component"
    }

    r_map = {
        IPSET_ERR_EXIST_SETNAME2: "Set cannot be renamed: a set with the"
        " new name already exists",
        IPSET_ERR_REFERENCED: "Set cannot be renamed: it is in use by"
        " another system",
    }

    s_map = {
        IPSET_ERR_EXIST_SETNAME2: "Sets cannot be swapped: the second set"
        " does not exist",
        IPSET_ERR_TYPE_MISMATCH: "The sets cannot be swapped: their type"
        " does not match",
    }

    a_map = {
        IPSET_ERR_EXIST: "Element cannot be added to the set: it's"
        " already added"
    }

    del_map = {
        IPSET_ERR_EXIST: "Element cannot be deleted from the set:"
        " it's not added"
    }

    cmd_map = {
        IPSET_CMD_CREATE: c_map,
        IPSET_CMD_DESTROY: destroy_map,
        IPSET_CMD_RENAME: r_map,
        IPSET_CMD_SWAP: s_map,
        IPSET_CMD_ADD: a_map,
        IPSET_CMD_DEL: del_map,
    }
