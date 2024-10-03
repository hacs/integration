from pyroute2.protocols import msg


class icmpmsg(msg):
    fields = [('type', 'uint8'), ('code', 'uint8'), ('csum', 'be32')]


class icmp_router_adv(icmpmsg):
    fields = icmpmsg.fields + [
        ('addrs_num', 'uint8'),
        ('alen', 'uint8'),
        ('lifetime', 'be32'),
        ('addrs', 'routers'),
    ]
