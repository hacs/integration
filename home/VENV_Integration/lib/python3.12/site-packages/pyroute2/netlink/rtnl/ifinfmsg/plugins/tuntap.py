from pyroute2.netlink import nla


class tuntap(nla):
    '''
    Fake data type
    '''

    prefix = 'IFTUN_'
    nla_map = (
        ('IFTUN_UNSPEC', 'none'),
        ('IFTUN_MODE', 'asciiz'),
        ('IFTUN_UID', 'uint32'),
        ('IFTUN_GID', 'uint32'),
        ('IFTUN_IFR', 'flags'),
    )

    class flags(nla):
        fields = (
            ('no_pi', 'B'),
            ('one_queue', 'B'),
            ('vnet_hdr', 'B'),
            ('tun_excl', 'B'),
            ('multi_queue', 'B'),
            ('persist', 'B'),
            ('nofilter', 'B'),
        )
