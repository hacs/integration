from pyroute2.netlink import nla
from pyroute2.netlink.rtnl import TC_H_ROOT
from pyroute2.netlink.rtnl.tcmsg.common import get_rate, percent2u32, time2tick

parent = TC_H_ROOT


def get_parameters(kwarg):
    delay = time2tick(kwarg.get('delay', 0))  # in microsecond
    limit = kwarg.get('limit', 1000)  # fifo limit (packets) see netem.c:230
    loss = percent2u32(kwarg.get('loss', 0))  # int percentage
    gap = kwarg.get('gap', 0)
    duplicate = percent2u32(kwarg.get('duplicate', 0))  # int percentage
    jitter = time2tick(kwarg.get('jitter', 0))  # in microsecond

    opts = {
        'delay': delay,
        'limit': limit,
        'loss': loss,
        'gap': gap,
        'duplicate': duplicate,
        'jitter': jitter,
        'attrs': [],
    }

    # correlation (delay, loss, duplicate)
    delay_corr = percent2u32(kwarg.get('delay_corr', 0))
    loss_corr = percent2u32(kwarg.get('loss_corr', 0))
    dup_corr = percent2u32(kwarg.get('dup_corr', 0))
    if delay_corr or loss_corr or dup_corr:
        # delay_corr requires that both jitter and delay are != 0
        if delay_corr and not (delay and jitter):
            raise Exception(
                'delay correlation requires delay' ' and jitter to be set'
            )
        # loss correlation and loss
        if loss_corr and not loss:
            raise Exception('loss correlation requires loss to be set')
        # duplicate correlation and duplicate
        if dup_corr and not duplicate:
            raise Exception(
                'duplicate correlation requires ' 'duplicate to be set'
            )

        opts['attrs'].append(
            [
                'TCA_NETEM_CORR',
                {
                    'delay_corr': delay_corr,
                    'loss_corr': loss_corr,
                    'dup_corr': dup_corr,
                },
            ]
        )

    # reorder (probability, correlation)
    prob_reorder = percent2u32(kwarg.get('prob_reorder', 0))
    corr_reorder = percent2u32(kwarg.get('corr_reorder', 0))
    if prob_reorder != 0:
        # gap defaults to 1 if equal to 0
        if gap == 0:
            opts['gap'] = gap = 1
        opts['attrs'].append(
            [
                'TCA_NETEM_REORDER',
                {'prob_reorder': prob_reorder, 'corr_reorder': corr_reorder},
            ]
        )
    else:
        if gap != 0:
            raise Exception('gap can only be set when prob_reorder is set')
        elif corr_reorder != 0:
            raise Exception(
                'corr_reorder can only be set when ' 'prob_reorder is set'
            )

    # corrupt (probability, correlation)
    prob_corrupt = percent2u32(kwarg.get('prob_corrupt', 0))
    corr_corrupt = percent2u32(kwarg.get('corr_corrupt', 0))
    if prob_corrupt:
        opts['attrs'].append(
            [
                'TCA_NETEM_CORRUPT',
                {'prob_corrupt': prob_corrupt, 'corr_corrupt': corr_corrupt},
            ]
        )
    elif corr_corrupt != 0:
        raise Exception(
            'corr_corrupt can only be set when ' 'prob_corrupt is set'
        )

    # rate (rate, packet_overhead, cell_size, cell_overhead)
    rate = get_rate(kwarg.get('rate', None))
    packet_overhead = kwarg.get('packet_overhead', 0)
    cell_size = kwarg.get('cell_size', 0)
    cell_overhead = kwarg.get('cell_overhead', 0)
    if rate is not None:
        opts['attrs'].append(
            [
                'TCA_NETEM_RATE',
                {
                    'rate': rate,
                    'packet_overhead': packet_overhead,
                    'cell_size': cell_size,
                    'cell_overhead': cell_overhead,
                },
            ]
        )
    elif packet_overhead != 0 or cell_size != 0 or cell_overhead != 0:
        raise Exception(
            'packet_overhead, cell_size and cell_overhead'
            'can only be set when rate is set'
        )

    # TODO
    # delay distribution (dist_size, dist_data)
    return opts


class options(nla):
    nla_map = (
        ('TCA_NETEM_UNSPEC', 'none'),
        ('TCA_NETEM_CORR', 'netem_corr'),
        ('TCA_NETEM_DELAY_DIST', 'none'),
        ('TCA_NETEM_REORDER', 'netem_reorder'),
        ('TCA_NETEM_CORRUPT', 'netem_corrupt'),
        ('TCA_NETEM_LOSS', 'none'),
        ('TCA_NETEM_RATE', 'netem_rate'),
    )

    fields = (
        ('delay', 'I'),
        ('limit', 'I'),
        ('loss', 'I'),
        ('gap', 'I'),
        ('duplicate', 'I'),
        ('jitter', 'I'),
    )

    class netem_corr(nla):
        '''correlation'''

        fields = (('delay_corr', 'I'), ('loss_corr', 'I'), ('dup_corr', 'I'))

    class netem_reorder(nla):
        '''reorder has probability and correlation'''

        fields = (('prob_reorder', 'I'), ('corr_reorder', 'I'))

    class netem_corrupt(nla):
        '''corruption has probability and correlation'''

        fields = (('prob_corrupt', 'I'), ('corr_corrupt', 'I'))

    class netem_rate(nla):
        '''rate'''

        fields = (
            ('rate', 'I'),
            ('packet_overhead', 'i'),
            ('cell_size', 'I'),
            ('cell_overhead', 'i'),
        )
