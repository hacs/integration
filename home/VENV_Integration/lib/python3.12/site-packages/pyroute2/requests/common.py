import ipaddress
import json
from collections import OrderedDict
from socket import AF_INET, AF_INET6

from pyroute2.common import AF_MPLS, dqn2int, get_address_family


class MPLSTarget(OrderedDict):
    def __init__(self, prime=None):
        super(MPLSTarget, self).__init__()
        if prime is None:
            prime = {}
        elif isinstance(prime, str):
            prime = {'label': int(prime)}
        elif isinstance(prime, int):
            prime = {'label': prime}
        elif isinstance(prime, dict):
            pass
        else:
            raise TypeError()
        self['label'] = prime.get('label', 16)
        self['tc'] = prime.get('tc', 0)
        self['bos'] = prime.get('bos', 1)
        self['ttl'] = prime.get('ttl', 0)

    def __eq__(self, right):
        return (
            isinstance(right, (dict, MPLSTarget))
            and self['label'] == right.get('label', 16)
            and self['tc'] == right.get('tc', 0)
            and self['bos'] == right.get('bos', 1)
            and self['ttl'] == right.get('ttl', 0)
        )

    def __repr__(self):
        return repr(dict(self))


class IPTargets:
    add_defaults = True

    def parse_target(self, key, context, value):
        ret = {key: value}
        set_full_mask = False
        if isinstance(value, int):
            return {'family': AF_MPLS, key: MPLSTarget(value)}
        if isinstance(value, (list, tuple)):
            targets = []
            target = None
            for spec in value:
                target = MPLSTarget(spec)
                target['bos'] = 0
                targets.append(target)
            if target:
                target['bos'] = 1
                return {'family': AF_MPLS, key: targets}
            else:
                return {}
        if isinstance(value, dict):
            if value.get('label'):
                return {'family': AF_MPLS, key: MPLSTarget(value)}
            # do not overwrite message family for IP VIA
            return {key: value}
        try:
            return self.parse_target(key, context, json.loads(value))
        except (json.JSONDecodeError, TypeError):
            pass
        if isinstance(value, str):
            if value == '':
                return {}
            labels = value.split('/')
            if len(labels) > 1:
                # MPLS label stack simple syntax? e.g.: 16/24, 200/300 etc.
                try:
                    return self.parse_target(key, context, labels)
                except ValueError:
                    pass
                # only simple IP targets are left
                value, prefixlen = labels
                ret[key] = value
                if self.add_defaults:
                    if prefixlen.find('.') > 0:
                        ret[f'{key}_len'] = dqn2int(prefixlen, AF_INET)
                    elif prefixlen.find(':') >= 0:
                        ret[f'{key}_len'] = dqn2int(prefixlen, AF_INET6)
                    else:
                        ret[f'{key}_len'] = int(prefixlen)
            else:
                if (
                    self.add_defaults
                    and key in ('dst', 'src')
                    and f'{key}_len' not in context
                ):
                    set_full_mask = True

            if self.add_defaults:
                ret['family'] = get_address_family(value)
                if ret['family'] == AF_INET6:
                    ret[key] = ipaddress.ip_address(value).compressed
                if set_full_mask:
                    if ret['family'] == AF_INET6:
                        ret[f'{key}_len'] = 128
                    elif ret['family'] == AF_INET:
                        ret[f'{key}_len'] = 32
        return ret

    def set_dst(self, context, value):
        if value in ('', 'default'):
            return {'dst': ''}
        elif value in ('0', '0.0.0.0'):
            return {'dst': '', 'family': AF_INET}
        elif value in ('::', '::/0'):
            return {'dst': '', 'family': AF_INET6}
        return self.parse_target('dst', context, value)

    def set_src(self, context, value):
        return self.parse_target('src', context, value)

    def set_via(self, context, value):
        return self.parse_target('via', context, value)

    def set_newdst(self, context, value):
        return self.parse_target('newdst', context, value)

    def set_gateway(self, context, value):
        return self.parse_target('gateway', context, value)


class Index:
    def set_index(self, context, value):
        if isinstance(value, (list, tuple)):
            value = value[0]
        return {'index': value}


class IPRouteFilter:
    def __init__(self, command):
        self.command = command

    def policy(self, key):
        if self.command == 'add' and key in ('tso_max_segs', 'tso_max_size'):
            return False
        return True


class NLAKeyTransform:
    _nla_prefix = ''

    def _key_transform(self, key):
        if isinstance(key, str) and key.startswith(self._nla_prefix):
            key = key[len(self._nla_prefix) :].lower()
        return key
