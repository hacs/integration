'''
High level ipset support.

When :doc:`ipset` is providing a direct netlink socket with low level
functions, a :class:`WiSet` object is built to map ipset objects from kernel.
It helps to add/remove entries, list content, etc.

For example, adding an entry with :class:`pyroute2.ipset.IPSet` object
implies to set a various number of parameters:

.. doctest::
    :skipif: True

    >>> ipset = IPSet()
    >>> ipset.add("foo", "1.2.3.4/24", etype="net")
    >>> ipset.close()

When they are discovered by a :class:`WiSet`:

.. doctest::
    :skipif: True

    >>> wiset = load_ipset("foo")
    >>> wiset.add("1.2.3.4/24")

Listing entries is also easier using :class:`WiSet`, since it parses for you
netlink messages:

.. doctest::
    :skipif: True

    >>> wiset.content
    {'1.2.3.0/24': IPStats(packets=None, bytes=None, comment=None,
                           timeout=None, skbmark=None, physdev=False)}
'''

import errno
import uuid
from collections import namedtuple
from inspect import getcallargs
from socket import AF_INET

from pyroute2.common import basestring
from pyroute2.ipset import IPSet
from pyroute2.netlink.exceptions import IPSetError
from pyroute2.netlink.nfnetlink.ipset import (
    IPSET_FLAG_IFACE_WILDCARD,
    IPSET_FLAG_PHYSDEV,
    IPSET_FLAG_WITH_COMMENT,
    IPSET_FLAG_WITH_COUNTERS,
    IPSET_FLAG_WITH_SKBINFO,
)
from pyroute2.netlink.nfnetlink.nfctsocket import IP_PROTOCOLS

# Debug variable to detect netlink socket leaks
COUNT = {"count": 0}


def need_ipset_socket(fun):
    """Decorator to create netlink socket if needed.

    In many of our helpers, we need to open a netlink socket. This can
    be expensive for someone using many times the functions: instead to have
    only one socket and use several requests, we will open it again and again.

    This helper allow our functions to be flexible: the caller can pass an
    optional socket, or do nothing. In this last case, this decorator
    will open a socket for the caller (and close it after call)

    It also help to mix helpers. One helper can call another one: the socket
    will be opened only once. We just have to pass the ipset variable.

    Note that all functions using this helper *must* use ipset as variable
    name for the socket.
    """

    def wrap(*args, **kwargs):
        callargs = getcallargs(fun, *args, **kwargs)
        if callargs["sock"] is None:
            # This variable is used only to debug leak in tests
            COUNT['count'] += 1
            with IPSet() as sock:
                callargs["sock"] = sock
                # We must pop kwargs here, else the function will receive
                # a dict of dict
                if "kwargs" in callargs:
                    callargs.update(callargs.pop("kwargs"))
                return fun(**callargs)  # pylint:disable=star-args

        return fun(*args, **kwargs)

    return wrap


class IPStats(
    namedtuple(
        "IPStats",
        [
            "packets",
            "bytes",
            "comment",
            "timeout",
            "skbmark",
            "physdev",
            "wildcard",
        ],
    )
):
    __slots__ = ()

    def __new__(
        cls,
        packets,
        bytes,
        comment,
        timeout,
        skbmark,
        physdev=False,
        wildcard=False,
    ):
        return super(IPStats, cls).__new__(
            cls,
            packets,
            bytes,
            comment,
            timeout,
            skbmark,
            physdev=physdev,
            wildcard=wildcard,
        )


# pylint: disable=too-many-instance-attributes
class WiSet(object):
    """Main high level ipset manipulation class.

    Every high level ipset operation should be possible with this class,
    you probably don't need other helpers of this module, except tools
    to load data from kernel (:func:`load_all_ipsets` and :func:`load_ipset`)

    For example, you can create and an entry in a ipset just with:

    .. doctest::
        :skipif: True

        >>> with WiSet(name="mysuperipset") as myset:
        >>>    myset.create()             # add the ipset in the kernel
        >>>    myset.add("198.51.100.1")  # add one IP to the set

    Netlink sockets are opened by __enter__ and __exit__ function, so you don't
    have to manage it manually if you use the "with" keyword.

    If you want to manage it manually (for example for long operation in
    a daemon), you can do the following:

    .. doctest::
        :skipif: True

        >>> myset = WiSet(name="mysuperipset")
        >>> myset.open_netlink()
        >>> # do stuff
        >>> myset.close_netlink()

    You can also don't initiate at all any netlink socket, this code will work:

    .. doctest::
        :skipif: True

        >>> myset = WiSet(name="mysuperipset")
        >>> myset.create()
        >>> myset.destroy()

    But do it very carefully. In that case, a netlink socket will be opened
    in background for any operation. No socket will be leaked, but that
    can consume resources.

    You can also instantiate WiSet objects with :func:`load_all_ipsets` and
    :func:`load_ipset`:

    .. doctest::
        :skipif: True

        >>> all_sets_dict = load_all_ipsets()
        >>> one_set = load_ipset(name="myset")

    Have a look on content variable if you need list of entries in the Set.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        name=None,
        attr_type='hash:ip',
        family=AF_INET,
        sock=None,
        timeout=None,
        counters=False,
        comment=False,
        hashsize=None,
        revision=None,
        skbinfo=False,
    ):
        self.name = name
        self.hashsize = hashsize
        self._attr_type = None
        self.entry_type = None
        self.attr_type = attr_type
        self.family = family
        self._content = None
        self.sock = sock
        self.timeout = timeout
        self.counters = counters
        self.comment = comment
        self.revision = revision
        self.index = None
        self.skbinfo = skbinfo

    def open_netlink(self):
        """
        Open manually a netlink socket.

        You can use "with WiSet()" statement instead.
        """
        if self.sock is None:
            self.sock = IPSet()

    def close_netlink(self):
        """Clone any opened netlink socket"""
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    @property
    def attr_type(self):
        return self._attr_type

    @attr_type.setter
    def attr_type(self, value):
        self._attr_type = value
        self.entry_type = value.split(":", 1)[1]

    def __enter__(self):
        self.open_netlink()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_netlink()

    @classmethod
    def from_netlink(cls, ndmsg, content=False):
        """Create a ipset objects based on a parsed netlink message

        :param ndmsg: the netlink message to parse
        :param content: should we fill (and parse) entries info (can be slow
                        on very large set)
        :type content: bool
        """
        self = cls()
        self.attr_type = ndmsg.get_attr("IPSET_ATTR_TYPENAME")
        self.name = ndmsg.get_attr("IPSET_ATTR_SETNAME")
        self.hashsize = ndmsg.get_attr("IPSET_ATTR_HASHSIZE")
        self.family = ndmsg.get_attr("IPSET_ATTR_FAMILY")
        self.revision = ndmsg.get_attr("IPSET_ATTR_REVISION")
        self.index = ndmsg.get_attr("IPSET_ATTR_INDEX")
        data = ndmsg.get_attr("IPSET_ATTR_DATA")
        self.timeout = data.get_attr("IPSET_ATTR_TIMEOUT")
        flags = data.get_attr("IPSET_ATTR_CADT_FLAGS")
        if flags is not None:
            self.counters = bool(flags & IPSET_FLAG_WITH_COUNTERS)
            self.comment = bool(flags & IPSET_FLAG_WITH_COMMENT)
            self.skbinfo = bool(flags & IPSET_FLAG_WITH_SKBINFO)

        if content:
            self.update_dict_content(ndmsg)

        return self

    def update_dict_content(self, ndmsg):
        """Update a dictionary statistics with values sent in netlink message

        :param ndmsg: the netlink message
        :type ndmsg: netlink message

        """
        family = "IPSET_ATTR_IPADDR_IPV4"
        ip_attr = "IPSET_ATTR_IP_FROM"
        if self._content is None:
            self._content = {}

        timeout = None
        entries = ndmsg.get_attr("IPSET_ATTR_ADT").get_attrs("IPSET_ATTR_DATA")
        for entry in entries:
            key = ""
            for parse_type in self.entry_type.split(","):
                if parse_type == "ip":
                    ip = entry.get_attr(ip_attr).get_attr(family)
                    key += ip
                elif parse_type == "net":
                    ip = entry.get_attr(ip_attr).get_attr(family)
                    key += ip
                    cidr = entry.get_attr("IPSET_ATTR_CIDR")
                    if cidr is not None:
                        key += "/{0}".format(cidr)
                elif parse_type == "iface":
                    key += entry.get_attr("IPSET_ATTR_IFACE")
                elif parse_type == "set":
                    key += entry.get_attr("IPSET_ATTR_NAME")
                elif parse_type == "mark":
                    key += str(hex(entry.get_attr("IPSET_ATTR_MARK")))
                elif parse_type == "port":
                    proto = entry.get_attr('IPSET_ATTR_PROTO')
                    if proto is not None:
                        proto = IP_PROTOCOLS.get(proto, str(proto)).lower()
                        key += '{proto}:'.format(proto=proto)
                    key += str(entry.get_attr("IPSET_ATTR_PORT_FROM"))
                elif parse_type == "mac":
                    key += entry.get_attr("IPSET_ATTR_ETHER")
                key += ","

            key = key.strip(",")

            if self.timeout is not None:
                timeout = entry.get_attr("IPSET_ATTR_TIMEOUT")
            skbmark = entry.get_attr("IPSET_ATTR_SKBMARK")
            if skbmark is not None:
                # Convert integer to hex for mark/mask
                # Only display mask if != 0xffffffff
                if skbmark[1] != (2**32 - 1):
                    skbmark = "/".join([str(hex(mark)) for mark in skbmark])
                else:
                    skbmark = str(hex(skbmark[0]))
            entry_flag_parsed = {"physdev": False}
            flags = entry.get_attr("IPSET_ATTR_CADT_FLAGS")
            if flags is not None:
                entry_flag_parsed["physdev"] = bool(flags & IPSET_FLAG_PHYSDEV)
                entry_flag_parsed["wildcard"] = bool(
                    flags & IPSET_FLAG_IFACE_WILDCARD
                )

            value = IPStats(
                packets=entry.get_attr("IPSET_ATTR_PACKETS"),
                bytes=entry.get_attr("IPSET_ATTR_BYTES"),
                comment=entry.get_attr("IPSET_ATTR_COMMENT"),
                skbmark=skbmark,
                timeout=timeout,
                **entry_flag_parsed
            )
            self._content[key] = value

    def create(self, **kwargs):
        """Insert this Set in the kernel

        Many options are set with python object attributes (like comments,
        counters, etc). For non-supported type, kwargs are provided. See
        :doc:`ipset` documentation for more information.
        """
        create_ipset(
            self.name,
            stype=self.attr_type,
            family=self.family,
            sock=self.sock,
            timeout=self.timeout,
            comment=self.comment,
            counters=self.counters,
            hashsize=self.hashsize,
            skbinfo=self.skbinfo,
            **kwargs
        )

    def destroy(self):
        """Destroy this ipset in the kernel list.

        It does not delete this python object (any content or other stored
        values are keep in memory). This function will fail if the ipset is
        still referenced (by example in iptables rules), you have been warned.
        """
        destroy_ipset(self.name, sock=self.sock)

    def add(self, entry, **kwargs):
        """Add an entry in this ipset.

        If counters are enabled on the set, reset by default the value when
        we add the element. Without this reset, kernel sometimes store old
        values and can add very strange behavior on counters.
        """
        if isinstance(entry, dict):
            kwargs.update(entry)
            entry = kwargs.pop("entry")
        if self.counters:
            kwargs["packets"] = kwargs.pop("packets", 0)
            kwargs["bytes"] = kwargs.pop("bytes", 0)
        skbmark = kwargs.get("skbmark")
        if isinstance(skbmark, basestring):
            skbmark = skbmark.split('/')
            mark = int(skbmark[0], 16)
            try:
                mask = int(skbmark[1], 16)
            except IndexError:
                mask = int("0xffffffff", 16)
            kwargs["skbmark"] = (mark, mask)
        add_ipset_entry(
            self.name, entry, etype=self.entry_type, sock=self.sock, **kwargs
        )

    def delete(self, entry, **kwargs):
        """Delete/remove an entry in this ipset"""
        delete_ipset_entry(
            self.name, entry, etype=self.entry_type, sock=self.sock, **kwargs
        )

    def test(self, entry, **kwargs):
        """Test if an entry is in this ipset"""
        return test_ipset_entry(
            self.name, entry, etype=self.entry_type, sock=self.sock, **kwargs
        )

    def test_list(self, entries, **kwargs):
        """Test if a list of a set of entries is in this ipset

        Return a set of entries found in the IPSet
        """
        return test_ipset_entries(
            self.name, entries, etype=self.entry_type, sock=self.sock, **kwargs
        )

    def update_content(self):
        """Update the content dictionary with values from kernel"""
        self._content = {}
        update_wiset_content(self, sock=self.sock)

    def flush(self):
        """Flush entries of the ipset"""
        flush_ipset(self.name, sock=self.sock)

    @property
    def content(self):
        """Dictionary of entries in the set.

        Keys are IP addresses (as string), values are IPStats tuples.
        """
        if self._content is None:
            self.update_content()

        return self._content

    def insert_list(self, entries):
        """Just a small helper to reduce the number of loops in main code."""
        for entry in entries:
            self.add(entry)

    def replace_entries(self, new_list):
        """Replace the content of an ipset with a new list of entries.

        This operation is like a flush() and adding all entries one by one. But
        this call is atomic: it creates a temporary ipset and swap the content.

        :param new_list: list of entries to add
        :type new_list: list or :py:class:`set` of basestring or of
            keyword arguments dict
        """
        temp_name = str(uuid.uuid4())[0:8]
        # Get a copy of ourself
        temp = load_ipset(self.name, sock=self.sock)
        temp.name = temp_name
        temp.sock = self.sock
        temp.create()
        temp.insert_list(new_list)
        swap_ipsets(self.name, temp_name, sock=self.sock)
        temp.destroy()


@need_ipset_socket
def create_ipset(
    name, stype=None, family=AF_INET, exclusive=False, sock=None, **kwargs
):
    """Create an ipset."""
    sock.create(
        name, stype=stype, family=family, exclusive=exclusive, **kwargs
    )


@need_ipset_socket
def load_all_ipsets(content=False, sock=None, inherit_sock=False, prefix=None):
    """List all ipset as WiSet objects.

    Get full ipset data from kernel and parse it in WiSet objects. Result is
    a dictionary with ipset names as keys, and WiSet objects as values.

    :param content: parse the list of entries and fill it in WiSet content
                    dictionary
    :type content: bool
    :param inherit_sock: use the netlink sock passed in ipset arg to
                         fill WiSets sock
    :type inherit_sock: bool
    :param prefix: filter out all ipset with a name not beginning by this
                   prefix
    :type prefix: str or None
    """
    res = {}
    for myset in sock.list():
        # on large sets, we can receive data in several messages
        name = myset.get_attr("IPSET_ATTR_SETNAME")
        if prefix is not None and not name.startswith(prefix):
            continue
        if name not in res:
            wiset = WiSet.from_netlink(myset, content=content)
            if inherit_sock:
                wiset.sock = sock
            res[wiset.name] = wiset
        elif content:
            res[wiset.name].update_dict_content(myset)
    return res


@need_ipset_socket
def load_ipset(name, content=False, sock=None, inherit_sock=False):
    """Get one ipset as WiSet object

    Helper to get current WiSet object. More efficient that
    :func:`load_all_ipsets` since the kernel does the filtering itself.

    Return None if the ipset does not exist

    :param name: name of the ipset
    :type name: str
    :param content: parse or not content and statistics on entries
    :type content: bool
    :param inherit_sock: use the netlink sock passed in ipset arg to
                         fill WiSet sock
    :type inherit_sock: bool
    """
    res = None
    try:
        messages = sock.list(name=name)
    except IPSetError as e:
        if e.code == errno.ENOENT:
            return res
        raise
    for msg in messages:
        if res is None:
            res = WiSet.from_netlink(msg, content=content)
            if inherit_sock:
                res.sock = sock
        elif content:
            res.update_dict_content(msg)
    return res


@need_ipset_socket
def update_wiset_content(wiset, sock=None):
    """Update content/statistics of a wiset.

    You should never call yourself this function. It is only a helper to use
    the :func:`need_ipset_socket` decorator out of WiSet object.
    """
    for msg in sock.list(name=wiset.name):
        wiset.update_dict_content(msg)


@need_ipset_socket
def destroy_ipset(name, sock=None):
    """Remove an ipset in the kernel."""
    sock.destroy(name)


@need_ipset_socket
def add_ipset_entry(name, entry, sock=None, **kwargs):
    """Add an entry"""
    sock.add(name, entry, **kwargs)


@need_ipset_socket
def delete_ipset_entry(name, entry, sock=None, **kwargs):
    """Remove one entry"""
    sock.delete(name, entry, **kwargs)


@need_ipset_socket
def test_ipset_exist(name, sock=None):
    """Test if the given ipset exist"""
    try:
        sock.headers(name)
        return True
    except IPSetError as e:
        if e.code == errno.ENOENT:
            return False
        raise


@need_ipset_socket
def test_ipset_entry(name, entry, sock=None, **kwargs):
    """Test if an entry is in one ipset"""
    return sock.test(name, entry, **kwargs)


@need_ipset_socket
def test_ipset_entries(name, entries, sock=None, **kwargs):
    """Test a list (or a set) of entries."""
    res = set()
    for entry in entries:
        if sock.test(name, entry, **kwargs):
            res.add(entry)
    return res


@need_ipset_socket
def flush_ipset(name, sock=None):
    """Flush all ipset content"""
    sock.flush(name)


@need_ipset_socket
def swap_ipsets(name_a, name_b, sock=None):
    """Swap the content of ipset a and b.

    ipsets must have compatible content.
    """
    sock.swap(name_a, name_b)


def get_ipset_socket(**kwargs):
    """Get a socket that one can pass to several WiSet objects"""
    return IPSet(**kwargs)
