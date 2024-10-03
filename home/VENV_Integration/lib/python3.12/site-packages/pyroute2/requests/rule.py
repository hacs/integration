import socket

from pyroute2.netlink.rtnl.fibmsg import FR_ACT_NAMES, fibmsg

from .common import Index, IPRouteFilter, IPTargets, NLAKeyTransform

DEFAULT_FRA_PRIORITY = 32000


class RuleFieldFilter(IPTargets, Index, NLAKeyTransform):
    _nla_prefix = fibmsg.prefix


class RuleIPRouteFilter(IPRouteFilter):
    def set_action(self, context, value):
        if isinstance(value, str):
            return {
                'action': FR_ACT_NAMES.get(
                    value, FR_ACT_NAMES.get('FR_ACT_' + value.upper(), value)
                )
            }
        return {'action': value}

    def finalize(self, context):
        if self.command != 'dump':
            if 'family' not in context:
                context['family'] = socket.AF_INET
            if 'priority' not in context:
                context['priority'] = DEFAULT_FRA_PRIORITY
            if 'table' in context and 'action' not in context:
                context['action'] = 'to_tbl'
            for key in ('src_len', 'dst_len'):
                if context.get(key, None) is None and key[:3] in context:
                    context[key] = {socket.AF_INET6: 128, socket.AF_INET: 32}[
                        context['family']
                    ]
