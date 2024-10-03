from socket import AF_INET

from pyroute2.common import get_address_family
from pyroute2.netlink.rtnl import ndmsg

from .common import Index, IPRouteFilter


class NeighbourFieldFilter(Index):
    def set_index(self, context, value):
        return {
            'ifindex': super(NeighbourFieldFilter, self).set_index(
                context, value
            )['index']
        }

    def set_ifindex(self, context, value):
        return self.set_index(context, value)

    def _state(self, value):
        if isinstance(value, str):
            value = ndmsg.states_a2n(value)
        return {'state': value}

    def set_nud(self, context, value):
        return self._state(value)

    def set_state(self, context, value):
        return self._state(value)

    def set_dst(self, context, value):
        if value:
            return {'dst': value}
        else:
            return {}


class NeighbourIPRouteFilter(IPRouteFilter):
    def set_dst(self, context, value):
        ret = {'dst': value}
        if 'family' not in context:
            ret['family'] = get_address_family(value)
        return ret

    def finalize(self, context):
        if self.command not in ('dump', 'get'):
            if 'state' not in context:
                context['state'] = ndmsg.NUD_PERMANENT
        if 'family' not in context:
            context['family'] = AF_INET
