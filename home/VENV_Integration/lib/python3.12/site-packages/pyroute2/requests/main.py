'''
General request and RTNL object data filters.
'''

import weakref
from collections import ChainMap


class RequestProcessor(dict):
    def __init__(self, field_filter=None, context=None, prime=None):
        self.field_filter = field_filter
        self.context = (
            context if isinstance(context, (dict, weakref.ProxyType)) else {}
        )
        self.combined = ChainMap(self, self.context)
        if isinstance(prime, dict):
            self.update(prime)

    def __setitem__(self, key, value):
        if value is None:
            return
        if key in self:
            del self[key]
        for nkey, nvalue in self.filter(key, value).items():
            super(RequestProcessor, self).__setitem__(nkey, nvalue)

    def filter(self, key, value):
        if hasattr(self.field_filter, '_key_transform'):
            key = self.field_filter._key_transform(key)
        if (
            hasattr(self.field_filter, '_allowed')
            and key not in self.field_filter._allowed
        ):
            return {}
        if hasattr(
            self.field_filter, 'policy'
        ) and not self.field_filter.policy(key):
            return {}
        return getattr(
            self.field_filter, f'set_{key}', lambda *argv: {key: value}
        )(self.combined, value)

    def update(self, prime):
        for key, value in tuple(prime.items()):
            self[key] = value

    def set_filter(self, field_filter):
        self.field_filter = field_filter
        return self

    def apply_filter(self, field_filter):
        self.field_filter = field_filter
        self.update(self)
        return self

    def finalize(self, cmd_context=None):
        if hasattr(self.field_filter, 'finalize_for_iproute'):
            # old interface
            self.field_filter.finalize_for_iproute(self.combined, cmd_context)
        if hasattr(self.field_filter, 'finalize'):
            # new interface
            self.field_filter.finalize(self.combined)
        return self
