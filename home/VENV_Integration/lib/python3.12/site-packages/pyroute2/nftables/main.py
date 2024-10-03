'''
'''

from pyroute2.netlink.nfnetlink import nfgen_msg
from pyroute2.netlink.nfnetlink.nftsocket import (
    DATA_TYPE_ID_TO_NAME,
    DATA_TYPE_NAME_TO_INFO,
    NFT_MSG_DELCHAIN,
    NFT_MSG_DELRULE,
    NFT_MSG_DELSET,
    NFT_MSG_DELSETELEM,
    NFT_MSG_DELTABLE,
    NFT_MSG_GETCHAIN,
    NFT_MSG_GETRULE,
    NFT_MSG_GETSET,
    NFT_MSG_GETSETELEM,
    NFT_MSG_GETTABLE,
    NFT_MSG_NEWCHAIN,
    NFT_MSG_NEWRULE,
    NFT_MSG_NEWSET,
    NFT_MSG_NEWSETELEM,
    NFT_MSG_NEWTABLE,
    NFTSocket,
    nft_chain_msg,
    nft_rule_msg,
    nft_set_elem_list_msg,
    nft_set_msg,
    nft_table_msg,
)


class NFTSet:
    __slots__ = ('table', 'name', 'key_type', 'timeout', 'counter', 'comment')

    def __init__(self, table, name, **kwargs):
        self.table = table
        self.name = name

        for attrname in self.__slots__:
            if attrname in kwargs:
                setattr(self, attrname, kwargs[attrname])
            elif attrname not in ("table", "name"):
                setattr(self, attrname, None)

    def as_netlink(self):
        attrs = {"NFTA_SET_TABLE": self.table, "NFTA_SET_NAME": self.name}
        set_flags = set()

        if self.key_type is not None:
            key_type, key_len, _ = DATA_TYPE_NAME_TO_INFO.get(self.key_type)
            attrs["NFTA_SET_KEY_TYPE"] = key_type
            attrs["NFTA_SET_KEY_LEN"] = key_len

        if self.timeout is not None:
            set_flags.add("NFT_SET_TIMEOUT")
            attrs["NFTA_SET_TIMEOUT"] = self.timeout

        if self.counter is True:
            attrs["NFTA_SET_EXPR"] = {'attrs': [('NFTA_EXPR_NAME', 'counter')]}

        if self.comment is not None:
            attrs["NFTA_SET_USERDATA"] = [
                ("NFTNL_UDATA_SET_COMMENT", self.comment)
            ]

        # ID is used for bulk create, but not implemented
        attrs['NFTA_SET_ID'] = 1
        attrs["NFTA_SET_FLAGS"] = set_flags
        return attrs

    @classmethod
    def from_netlink(cls, msg):
        data_type_name = DATA_TYPE_ID_TO_NAME.get(
            msg.get_attr("NFTA_SET_KEY_TYPE"),
            msg.get_attr("NFTA_SET_KEY_TYPE"),  # fallback to raw value
        )

        counter = False
        expr = msg.get_attr('NFTA_SET_EXPR')
        if expr:
            expr = expr.get_attrs('NFTA_EXPR_NAME')
            if expr and "counter" in expr:
                counter = True

        comment = None
        udata = msg.get_attr("NFTA_SET_USERDATA")
        if udata:
            for key, value in udata:
                if key == "NFTNL_UDATA_SET_COMMENT":
                    comment = value
                    break

        return cls(
            table=msg.get_attr('NFTA_SET_TABLE'),
            name=msg.get_attr('NFTA_SET_NAME'),
            key_type=data_type_name,
            timeout=msg.get_attr('NFTA_SET_TIMEOUT'),
            counter=counter,
            comment=comment,
        )

    @classmethod
    def from_dict(cls, d):
        return cls(
            **{
                name: value
                for name, value in d.items()
                if name in cls.__slots__
            }
        )

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__}

    def __repr__(self):
        return str(self.as_dict())


class NFTSetElem:
    __slots__ = (
        'value',
        'timeout',
        'expiration',
        'counter_bytes',
        'counter_packets',
        'comment',
    )

    def __init__(self, value, **kwargs):
        self.value = value
        for name in self.__slots__:
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif name != "value":
                setattr(self, name, None)

    @classmethod
    def from_netlink(cls, msg, modifier):
        value = msg.get_attr('NFTA_SET_ELEM_KEY').get_attr("NFTA_DATA_VALUE")
        if modifier is not None:
            # Need to find a better way
            modifier.data = value
            modifier.length = 4 + len(modifier.data)
            modifier.decode()
            value = modifier.value

        kwarg = {
            "expiration": msg.get_attr('NFTA_SET_ELEM_EXPIRATION'),
            "timeout": msg.get_attr('NFTA_SET_ELEM_TIMEOUT'),
        }

        elem_expr = msg.get_attr('NFTA_SET_ELEM_EXPR')
        if elem_expr:
            if elem_expr.get_attr('NFTA_EXPR_NAME') == "counter":
                elem_expr = elem_expr.get_attr("NFTA_EXPR_DATA")
                kwarg.update(
                    {
                        "counter_bytes": elem_expr.get_attr(
                            "NFTA_COUNTER_BYTES"
                        ),
                        "counter_packets": elem_expr.get_attr(
                            "NFTA_COUNTER_PACKETS"
                        ),
                    }
                )

        udata = msg.get_attr('NFTA_SET_ELEM_USERDATA')
        if udata:
            for type_name, data in udata:
                if type_name == "NFTNL_UDATA_SET_ELEM_COMMENT":
                    kwarg["comment"] = data

        return cls(value=value, **kwarg)

    def as_netlink(self, modifier):
        if modifier is not None:
            modifier.value = self.value
            modifier.encode()
            value = modifier["value"]
        else:
            value = self.value

        attrs = [
            ['NFTA_SET_ELEM_KEY', {'attrs': [('NFTA_DATA_VALUE', value)]}]
        ]

        if self.timeout is not None:
            attrs.append(['NFTA_SET_ELEM_TIMEOUT', self.timeout])

        if self.expiration is not None:
            attrs.append(['NFTA_SET_ELEM_EXPIRATION', self.expiration])

        if self.comment is not None:
            attrs.append(
                [
                    'NFTA_SET_ELEM_USERDATA',
                    [("NFTNL_UDATA_SET_ELEM_COMMENT", self.comment)],
                ]
            )

        return {'attrs': attrs}

    @classmethod
    def from_dict(cls, d):
        return cls(
            **{
                name: value
                for name, value in d.items()
                if name in cls.__slots__
            }
        )

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__}

    def __repr__(self):
        return str(self.as_dict())


class NFTables(NFTSocket):
    # TODO: documentation
    # TODO: tests
    # TODO: dump()/load() with support for json and xml

    def get_tables(self):
        return self.request_get(nfgen_msg(), NFT_MSG_GETTABLE)

    def get_chains(self):
        return self.request_get(nfgen_msg(), NFT_MSG_GETCHAIN)

    def get_rules(self):
        return self.request_get(nfgen_msg(), NFT_MSG_GETRULE)

    def get_sets(self):
        return self.request_get(nfgen_msg(), NFT_MSG_GETSET)

    #
    # The nft API is in the prototype stage and may be
    # changed until the release. The planned release for
    # the API is 0.5.2
    #

    def table(self, cmd, **kwarg):
        '''
        Example::

            nft.table('add', name='test0')
        '''
        commands = {
            'add': NFT_MSG_NEWTABLE,
            'create': NFT_MSG_NEWTABLE,
            'del': NFT_MSG_DELTABLE,
            'get': NFT_MSG_GETTABLE,
        }
        return self._command(nft_table_msg, commands, cmd, kwarg)

    def chain(self, cmd, **kwarg):
        '''
        Example::

            #
            # default policy 'drop' for input
            #
            nft.chain('add',
                      table='test0',
                      name='test_chain0',
                      hook='input',
                      type='filter',
                      policy=0)
        '''
        commands = {
            'add': NFT_MSG_NEWCHAIN,
            'create': NFT_MSG_NEWCHAIN,
            'del': NFT_MSG_DELCHAIN,
            'get': NFT_MSG_GETCHAIN,
        }
        # TODO: What about 'ingress' (netdev family)?
        hooks = {
            'prerouting': 0,
            'input': 1,
            'forward': 2,
            'output': 3,
            'postrouting': 4,
        }
        if 'hook' in kwarg:
            kwarg['hook'] = {
                'attrs': [
                    ['NFTA_HOOK_HOOKNUM', hooks[kwarg['hook']]],
                    ['NFTA_HOOK_PRIORITY', kwarg.pop('priority', 0)],
                ]
            }
        if 'type' not in kwarg:
            kwarg['type'] = 'filter'
        return self._command(nft_chain_msg, commands, cmd, kwarg)

    def rule(self, cmd, **kwarg):
        '''
        Example::

            from pyroute2.nftables.expressions import ipv4addr, verdict
            #
            # allow all traffic from 192.168.0.0/24
            #
            nft.rule('add',
                     table='test0',
                     chain='test_chain0',
                     expressions=(ipv4addr(src='192.168.0.0/24'),
                                  verdict(code=1)))
        '''
        commands = {
            'add': NFT_MSG_NEWRULE,
            'create': NFT_MSG_NEWRULE,
            'insert': NFT_MSG_NEWRULE,
            'replace': NFT_MSG_NEWRULE,
            'del': NFT_MSG_DELRULE,
            'get': NFT_MSG_GETRULE,
        }

        if 'expressions' in kwarg:
            expressions = []
            for exp in kwarg['expressions']:
                expressions.extend(exp)
            kwarg['expressions'] = expressions
        return self._command(nft_rule_msg, commands, cmd, kwarg)

    def sets(self, cmd, **kwarg):
        '''
        Example::
            nft.sets("add", table="filter", name="test0", key_type="ipv4_addr",
                     timeout=10000, counter=True,
                     comment="my comment max 252 bytes")
            nft.sets("get", table="filter", name="test0")
            nft.sets("del", table="filter", name="test0")
            my_set = nft.sets("add", set=NFTSet(table="filter", name="test1",
                              key_type="ipv4_addr")
            nft.sets("del", set=my_set)
        '''
        commands = {
            'add': NFT_MSG_NEWSET,
            'get': NFT_MSG_GETSET,
            'del': NFT_MSG_DELSET,
        }

        if "set" in kwarg:
            nft_set = kwarg.pop("set")
        else:
            nft_set = NFTSet(**kwarg)
        kwarg = nft_set.as_netlink()
        msg = self._command(nft_set_msg, commands, cmd, kwarg)
        if cmd == "get":
            return NFTSet.from_netlink(msg)
        return nft_set

    def set_elems(self, cmd, **kwarg):
        '''
        Example::
            nft.set_elems("add", table="filter", set="test0",
                          elements={"10.2.3.4", "10.4.3.2"})
            nft.set_elems("add", set=NFTSet(table="filter", name="test0"),
                          elements=[{"value": "10.2.3.4", "timeout": 10000}])
            nft.set_elems("add", table="filter", set="test0",
                          elements=[NFTSetElem(value="10.2.3.4",
                                               timeout=10000,
                                               comment="hello world")])
            nft.set_elems("get", table="filter", set="test0")
            nft.set_elems("del", table="filter", set="test0",
                          elements=["10.2.3.4"])
        '''
        commands = {
            'add': NFT_MSG_NEWSETELEM,
            'get': NFT_MSG_GETSETELEM,
            'del': NFT_MSG_DELSETELEM,
        }
        if isinstance(kwarg["set"], NFTSet):
            nft_set = kwarg.pop("set")
            kwarg["table"] = nft_set.table
            kwarg["set"] = nft_set.name
        else:
            nft_set = self.sets("get", table=kwarg["table"], name=kwarg["set"])

        found = DATA_TYPE_NAME_TO_INFO.get(nft_set.key_type)
        if found:
            _, _, modifier = found
            modifier = modifier()
            modifier.header = None
        else:
            modifier = None

        if cmd == "get":
            msg = nft_set_elem_list_msg()
            msg['attrs'] = [
                ["NFTA_SET_ELEM_LIST_TABLE", kwarg["table"]],
                ["NFTA_SET_ELEM_LIST_SET", kwarg["set"]],
            ]
            msg = self.request_get(msg, NFT_MSG_GETSETELEM)[0]
            elements = set()
            for elem in msg.get_attr('NFTA_SET_ELEM_LIST_ELEMENTS'):
                elements.add(NFTSetElem.from_netlink(elem, modifier))
            return elements

        elements = []
        for elem in kwarg.pop("elements"):
            if isinstance(elem, dict):
                elem = NFTSetElem.from_dict(elem)
            elif not isinstance(elem, NFTSetElem):
                elem = NFTSetElem(value=elem)
            elements.append(elem.as_netlink(modifier))
        kwarg["elements"] = elements
        return self._command(nft_set_elem_list_msg, commands, cmd, kwarg)
