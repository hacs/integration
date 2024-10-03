from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT

parent = TC_H_ROOT
actions = {
    'TCQ_PLUG_BUFFER': 0,
    'TCQ_PLUG_RELEASE_ONE': 1,
    'TCQ_PLUG_RELEASE_INDEFINITE': 2,
    'TCQ_PLUG_LIMIT': 3,
}


def get_parameters(kwarg):
    return {
        'action': actions.get(kwarg.get('action', 0), 0),
        'limit': kwarg.get('limit', 0),
    }


class options(nla):
    fields = (('action', 'i'), ('limit', 'I'))
