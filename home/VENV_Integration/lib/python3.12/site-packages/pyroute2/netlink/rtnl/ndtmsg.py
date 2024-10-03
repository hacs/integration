from pyroute2.netlink import nla, nlmsg


class ndtmsg(nlmsg):
    '''
    Neighbour table message
    '''

    __slots__ = ()

    fields = (('family', 'B'), ('__pad', '3x'))

    nla_map = (
        ('NDTA_UNSPEC', 'none'),
        ('NDTA_NAME', 'asciiz'),
        ('NDTA_THRESH1', 'uint32'),
        ('NDTA_THRESH2', 'uint32'),
        ('NDTA_THRESH3', 'uint32'),
        ('NDTA_CONFIG', 'config'),
        ('NDTA_PARMS', 'parms'),
        ('NDTA_STATS', 'stats'),
        ('NDTA_GC_INTERVAL', 'uint64'),
    )

    class config(nla):
        __slots__ = ()

        fields = (
            ('key_len', 'H'),
            ('entry_size', 'H'),
            ('entries', 'I'),
            ('last_flush', 'I'),  # delta to now in msecs
            ('last_rand', 'I'),  # delta to now in msecs
            ('hash_rnd', 'I'),
            ('hash_mask', 'I'),
            ('hash_chain_gc', 'I'),
            ('proxy_qlen', 'I'),
        )

    class stats(nla):
        __slots__ = ()

        fields = (
            ('allocs', 'Q'),
            ('destroys', 'Q'),
            ('hash_grows', 'Q'),
            ('res_failed', 'Q'),
            ('lookups', 'Q'),
            ('hits', 'Q'),
            ('rcv_probes_mcast', 'Q'),
            ('rcv_probes_ucast', 'Q'),
            ('periodic_gc_runs', 'Q'),
            ('forced_gc_runs', 'Q'),
        )

    class parms(nla):
        __slots__ = ()

        nla_map = (
            ('NDTPA_UNSPEC', 'none'),
            ('NDTPA_IFINDEX', 'uint32'),
            ('NDTPA_REFCNT', 'uint32'),
            ('NDTPA_REACHABLE_TIME', 'uint64'),
            ('NDTPA_BASE_REACHABLE_TIME', 'uint64'),
            ('NDTPA_RETRANS_TIME', 'uint64'),
            ('NDTPA_GC_STALETIME', 'uint64'),
            ('NDTPA_DELAY_PROBE_TIME', 'uint64'),
            ('NDTPA_QUEUE_LEN', 'uint32'),
            ('NDTPA_APP_PROBES', 'uint32'),
            ('NDTPA_UCAST_PROBES', 'uint32'),
            ('NDTPA_MCAST_PROBES', 'uint32'),
            ('NDTPA_ANYCAST_DELAY', 'uint64'),
            ('NDTPA_PROXY_DELAY', 'uint64'),
            ('NDTPA_PROXY_QLEN', 'uint32'),
            ('NDTPA_LOCKTIME', 'uint64'),
            ('NDTPA_QUEUE_LENBYTES', 'uint32'),
        )
