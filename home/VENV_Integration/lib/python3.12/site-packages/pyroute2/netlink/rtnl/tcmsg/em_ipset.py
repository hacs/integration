from pyroute2.netlink import nlmsg_base, nlmsg_encoder_generic

# see em_ipset.c
IPSET_DIM = {
    'IPSET_DIM_ZERO': 0,
    'IPSET_DIM_ONE': 1,
    'IPSET_DIM_TWO': 2,
    'IPSET_DIM_THREE': 3,
    'IPSET_DIM_MAX': 6,
}

TCF_IPSET_MODE_DST = 0
TCF_IPSET_MODE_SRC = 2


def get_parameters(kwarg):
    ret = {'attrs': []}
    attrs_map = (
        ('matchid', 'TCF_EM_MATCHID'),
        ('kind', 'TCF_EM_KIND'),
        ('flags', 'TCF_EM_FLAGS'),
        ('pad', 'TCF_EM_PAD'),
    )

    for k, v in attrs_map:
        r = kwarg.get(k, None)
        if r is not None:
            ret['attrs'].append([v, r])

    return ret


class data(nlmsg_base, nlmsg_encoder_generic):
    fields = (
        ('ip_set_index', 'H'),
        ('ip_set_dim', 'B'),
        ('ip_set_flags', 'B'),
    )

    def encode(self):
        flags, dim = self._get_ip_set_parms()

        self['ip_set_index'] = self['index']
        self['ip_set_dim'] = dim
        self['ip_set_flags'] = flags
        nlmsg_base.encode(self)

    def _get_ip_set_parms(self):
        flags = 0
        dim = 0
        mode = self['mode']

        # Split to get dimension
        modes = mode.split(',')
        dim = len(modes)
        if dim > IPSET_DIM['IPSET_DIM_MAX']:
            raise ValueError(
                'IPSet dimension could not be greater than {0}'.format(
                    IPSET_DIM['IPSET_DIM_MAX']
                )
            )

        for i in range(0, dim):
            if modes[i] == 'dst':
                flags |= TCF_IPSET_MODE_DST << i
            elif modes[i] == 'src':
                flags |= TCF_IPSET_MODE_SRC << i
            else:
                raise ValueError('Unknown IP set mode "{0}"'.format(modes[i]))

        return (flags, dim)
