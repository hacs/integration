from .report import RecordSet


class Query(object):
    def __init__(self, schema, fmt='raw'):
        self._schema = schema
        self._fmt = fmt

    def _formatter(self, cursor, fmt=None, header=None, transform=None):
        fmt = fmt or self._fmt

        if fmt == 'csv':
            if header:
                yield ','.join(header)
            for record in cursor:
                if transform:
                    record = transform(record)
                if isinstance(record, (list, tuple)):
                    yield ','.join([str(x) for x in record])
                else:
                    yield record
        elif fmt == 'raw':
            if header:
                yield header
            for record in cursor:
                if transform:
                    record = transform(record)
                yield record
        else:
            raise TypeError('format not supported')

    def nodes(self, fmt=None):
        '''
        List all the nodes within the cluster.
        '''
        header = ('nodename',)
        return RecordSet(
            self._formatter(
                self._schema.fetch(
                    '''
            SELECT DISTINCT f_target
            FROM interfaces
        '''
                ),
                fmt,
                header,
            )
        )

    def p2p_edges(self, fmt=None):
        '''
        List point to point edges within the cluster, like
        GRE or PPP interfaces.
        '''
        header = ('left_node', 'right_node')
        return RecordSet(
            self._formatter(
                self._schema.fetch(
                    '''
            SELECT DISTINCT
                l.f_target, r.f_target
            FROM p2p AS l
            INNER JOIN p2p AS r
            ON
                l.f_p2p_local = r.f_p2p_remote
                AND l.f_target != r.f_target
        '''
                ),
                fmt,
                header,
            )
        )

    def l2_edges(self, fmt=None):
        '''
        List l2 links within the cluster, reconstructed
        from the ARP caches on the nodes. Works as follows:

        1. for every node take the ARP cache
        2. for every record in the cache reconstruct two triplets:

        * the interface index -> the local interface name
        * the neighbour lladdr -> the remote node and interface name

        Issues: does not filter out fake lladdr, so CARP interfaces
        produce fake l2 edges within the cluster.
        '''
        header = (
            'left_node',
            'left_ifname',
            'left_lladdr',
            'right_node',
            'right_ifname',
            'right_lladdr',
        )
        return RecordSet(
            self._formatter(
                self._schema.fetch(
                    '''
        SELECT DISTINCT
            j.f_target, j.f_IFLA_IFNAME, j.f_IFLA_ADDRESS,
            d.f_target, d.f_IFLA_IFNAME, j.f_NDA_LLADDR
        FROM
            (SELECT
                n.f_target, i.f_IFLA_IFNAME,
                i.f_IFLA_ADDRESS, n.f_NDA_LLADDR
             FROM
                neighbours AS n
             INNER JOIN
                interfaces AS i
             ON
                n.f_target = i.f_target
                AND i.f_IFLA_ADDRESS != '00:00:00:00:00:00'
                AND n.f_ifindex = i.f_index) AS j
        INNER JOIN
            interfaces AS d
        ON
            j.f_NDA_LLADDR = d.f_IFLA_ADDRESS
            AND j.f_target != d.f_target
        '''
                ),
                fmt,
                header,
            )
        )

    def l3_edges(self, fmt=None):
        '''
        List l3 edges. For every address on every node look
        if it is used as a gateway on remote nodes. Such cases
        are reported as l3 edges.

        Issues: does not report routes (edges) via point to point
        connections like GRE where local addresses are used as
        gateways. To be fixed.
        '''
        header = (
            'source_node',
            'gateway_node',
            'gateway_address',
            'dst',
            'dst_len',
        )
        return RecordSet(
            self._formatter(
                self._schema.fetch(
                    '''
            SELECT DISTINCT
                r.f_target, a.f_target, a.f_IFA_ADDRESS,
                r.f_RTA_DST, r.f_dst_len
            FROM
                addresses AS a
            INNER JOIN
                routes AS r
            ON
                r.f_target != a.f_target
                AND r.f_RTA_GATEWAY = a.f_IFA_ADDRESS
                AND r.f_RTA_GATEWAY NOT IN
            (SELECT
                f_IFA_ADDRESS
             FROM
                addresses
             WHERE
                f_target = r.f_target)
        '''
                ),
                fmt,
                header,
            )
        )
