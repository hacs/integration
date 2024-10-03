from pyroute2.common import map_namespace
from pyroute2.netlink import nla, nlmsg

FR_ACT_UNSPEC = 0
FR_ACT_TO_TBL = 1
FR_ACT_GOTO = 2
FR_ACT_NOP = 3
FR_ACT_BLACKHOLE = 6
FR_ACT_UNREACHABLE = 7
FR_ACT_PROHIBIT = 8
(FR_ACT_NAMES, FR_ACT_VALUES) = map_namespace('FR_ACT', globals())


class fibmsg(nlmsg):
    '''
    IP rule message

    C structure::

        struct fib_rule_hdr {
            __u8        family;
            __u8        dst_len;
            __u8        src_len;
            __u8        tos;
            __u8        table;
            __u8        res1;   /* reserved */
            __u8        res2;   /* reserved */
            __u8        action;
            __u32       flags;
        };
    '''

    prefix = 'FRA_'

    fields = (
        ('family', 'B'),
        ('dst_len', 'B'),
        ('src_len', 'B'),
        ('tos', 'B'),
        ('table', 'B'),
        ('res1', 'B'),
        ('res2', 'B'),
        ('action', 'B'),
        ('flags', 'I'),
    )

    # fibmsg NLA numbers are not sequential, so
    # give them here explicitly
    nla_map = (
        (0, 'FRA_UNSPEC', 'none'),
        (1, 'FRA_DST', 'ipaddr'),
        (2, 'FRA_SRC', 'ipaddr'),
        (3, 'FRA_IIFNAME', 'asciiz'),
        (4, 'FRA_GOTO', 'uint32'),
        (6, 'FRA_PRIORITY', 'uint32'),
        (10, 'FRA_FWMARK', 'uint32'),
        (11, 'FRA_FLOW', 'uint32'),
        (12, 'FRA_TUN_ID', 'be64'),
        (13, 'FRA_SUPPRESS_IFGROUP', 'uint32'),
        (14, 'FRA_SUPPRESS_PREFIXLEN', 'uint32'),
        (15, 'FRA_TABLE', 'uint32'),
        (16, 'FRA_FWMASK', 'uint32'),
        (17, 'FRA_OIFNAME', 'asciiz'),
        (18, 'FRA_PAD', 'hex'),
        (19, 'FRA_L3MDEV', 'uint8'),
        (20, 'FRA_UID_RANGE', 'uid_range'),
        (21, 'FRA_PROTOCOL', 'uint8'),
        (22, 'FRA_IP_PROTO', 'uint8'),
        (23, 'FRA_SPORT_RANGE', 'port_range'),
        (24, 'FRA_DPORT_RANGE', 'port_range'),
    )

    class fra_range(nla):
        __slots__ = ()
        sql_type = 'TEXT'

        def encode(self):
            self['start'], self['end'] = [
                int(x) for x in self.value.split(':')
            ]
            nla.encode(self)

        def decode(self):
            nla.decode(self)
            self.value = '%s:%s' % (self['start'], self['end'])

    class uid_range(fra_range):
        fields = (('start', 'I'), ('end', 'I'))

    class port_range(fra_range):
        fields = (('start', 'H'), ('end', 'H'))
