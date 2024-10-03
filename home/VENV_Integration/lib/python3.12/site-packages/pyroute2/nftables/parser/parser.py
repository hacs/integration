from collections import namedtuple

conv_map_tuple = namedtuple(
    'conv_map_tuple', 'has_attr has_netlink has_dict parser_cls'
)


class nfta_nla_parser(object):
    conv_maps = ()

    def __init__(self, **kwargs):
        for c in self.conv_maps:
            setattr(self, c.has_attr, kwargs[c.has_attr])

    def __repr__(self):
        s = ''
        for c in self.conv_maps:
            s += 'c={0}, VALUE={1}\n'.format(c, getattr(self, c.has_attr))
        return s

    @classmethod
    def from_netlink(cls, ndmsg):
        kwargs = {}
        for c in cls.conv_maps:
            if c.has_netlink is None:
                continue
            p = getattr(cls, 'cparser_' + c.parser_cls)
            nl_val = ndmsg.get_attr(c.has_netlink)
            if nl_val is None:
                kwargs[c.has_attr] = None
            else:
                kwargs[c.has_attr] = p.from_netlink(
                    ndmsg.get_attr(c.has_netlink)
                )
        return cls(**kwargs)

    def to_netlink(self):
        nla = {'attrs': []}
        for c in self.conv_maps:
            val = getattr(self, c.has_attr)
            if val is None:
                continue
            nla['attrs'].append(
                (
                    c.has_netlink,
                    getattr(self, 'cparser_' + c.parser_cls).to_netlink(val),
                )
            )
        return nla

    @classmethod
    def from_dict(cls, d):
        kwargs = {}
        for c in cls.conv_maps:
            if c.has_dict in d:
                kwargs[c.has_attr] = getattr(
                    cls, 'cparser_' + c.parser_cls
                ).from_dict(d[c.has_dict])
            else:
                kwargs[c.has_attr] = None
        return cls(**kwargs)

    def to_dict(self):
        d = {}
        for c in self.conv_maps:
            val = getattr(self, c.has_attr)
            if val is not None:
                val = getattr(self, 'cparser_' + c.parser_cls).to_dict(val)
                if val is not None:
                    d[c.has_dict] = val
        return d

    class cparser_raw(object):
        @staticmethod
        def from_netlink(val):
            return val

        @staticmethod
        def to_netlink(val):
            return val

        @staticmethod
        def from_dict(val):
            return val

        @staticmethod
        def to_dict(val):
            return val
