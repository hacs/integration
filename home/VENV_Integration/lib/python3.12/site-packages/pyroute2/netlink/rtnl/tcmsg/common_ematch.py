from pyroute2.netlink.rtnl.tcmsg import em_cmp, em_ipset, em_meta

plugins = {
    # 0: em_container,
    1: em_cmp,
    # 2: em_nbyte,
    # 3: em_u32,
    4: em_meta,
    # 5: em_text,
    # 6: em_vlan,
    # 7: em_canid,
    8: em_ipset,
    # 9: em_ipt,
}

plugins_translate = {
    'container': 0,
    'cmp': 1,
    'nbyte': 2,
    'u32': 3,
    'meta': 4,
    'text': 5,
    'vlan': 6,
    'canid': 7,
    'ipset': 8,
    'ipt': 9,
}

TCF_EM_REL_END = 0
TCF_EM_REL_AND = 1
TCF_EM_REL_OR = 2
TCF_EM_INVERSE_MASK = 4

RELATIONS_DICT = {
    'and': TCF_EM_REL_AND,
    'AND': TCF_EM_REL_AND,
    '&&': TCF_EM_REL_AND,
    'or': TCF_EM_REL_OR,
    'OR': TCF_EM_REL_OR,
    '||': TCF_EM_REL_OR,
}


class nla_plus_tcf_ematch_opt(object):
    @staticmethod
    def parse_ematch_options(self, *argv, **kwarg):
        if 'kind' not in self:
            raise ValueError('ematch requires "kind" parameter')

        kind = self['kind']
        if kind in plugins:
            ret = plugins[kind].data(data=argv[0])
            ret.decode()
            return ret
        return self.hex


def get_ematch_parms(kwarg):
    if 'kind' not in kwarg:
        raise ValueError('ematch requires "kind" parameter')

    if kwarg['kind'] in plugins:
        return plugins[kwarg['kind']].get_parameters(kwarg)
    else:
        return []


def get_tcf_ematches(kwarg):
    ret = {'attrs': []}
    matches = []
    header = {'nmatches': 0, 'progid': 0}

    # Get the number of expressions
    expr_count = len(kwarg['match'])
    header['nmatches'] = expr_count

    # Load plugin and transfer data
    for i in range(0, expr_count):
        match = {'matchid': 0, 'kind': None, 'flags': 0, 'pad': 0, 'opt': None}

        cur_match = kwarg['match'][i]

        # Translate string kind into numeric kind
        kind = plugins_translate[cur_match['kind']]
        match['kind'] = kind
        data = plugins[kind].data()
        data.setvalue(cur_match)
        data.encode()

        # Add ematch encoded data
        match['opt'] = data.data

        # Safety check
        if i == expr_count - 1 and 'relation' in cur_match:
            raise ValueError('Could not set a relation to the last expression')

        if i < expr_count - 1 and 'relation' not in cur_match:
            raise ValueError(
                'You must specify a relation for every expression'
                ' except the last one'
            )

        # Set relation to flags
        if 'relation' in cur_match:
            relation = cur_match['relation']
            if relation in RELATIONS_DICT:
                match['flags'] |= RELATIONS_DICT.get(relation)
            else:
                raise ValueError('Unknown relation {0}'.format(relation))
        else:
            match['flags'] = TCF_EM_REL_END

        # Handle inverse flag
        if 'inverse' in cur_match:
            if cur_match['inverse']:
                match['flags'] |= TCF_EM_INVERSE_MASK

        # Append new match to list of matches
        matches.append(match)

    ret['attrs'].append(['TCA_EMATCH_TREE_HDR', header])
    ret['attrs'].append(['TCA_EMATCH_TREE_LIST', matches])

    return ret
