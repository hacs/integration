import socket

from pyroute2.common import map_namespace
from pyroute2.netlink import nla, nlmsg

# address attributes
#
# Important comment:
# For IPv4, IFA_ADDRESS is a prefix address, not a local interface
# address. It makes no difference for normal interfaces, but
# for point-to-point ones IFA_ADDRESS means DESTINATION address,
# and the local address is supplied in IFA_LOCAL attribute.
#

IFA_F_SECONDARY = 0x01
# IFA_F_TEMPORARY IFA_F_SECONDARY
IFA_F_NODAD = 0x02
IFA_F_OPTIMISTIC = 0x04
IFA_F_DADFAILED = 0x08
IFA_F_HOMEADDRESS = 0x10
IFA_F_DEPRECATED = 0x20
IFA_F_TENTATIVE = 0x40
IFA_F_PERMANENT = 0x80
IFA_F_MANAGETEMPADDR = 0x100
IFA_F_NOPREFIXROUTE = 0x200
IFA_F_MCAUTOJOIN = 0x400
IFA_F_STABLE_PRIVACY = 0x800

(IFA_F_NAMES, IFA_F_VALUES) = map_namespace('IFA_F', globals())
# 8<----------------------------------------------
IFA_F_TEMPORARY = IFA_F_SECONDARY
IFA_F_NAMES['IFA_F_TEMPORARY'] = IFA_F_TEMPORARY
IFA_F_VALUES6 = IFA_F_VALUES
IFA_F_VALUES6[IFA_F_TEMPORARY] = 'IFA_F_TEMPORARY'
# 8<----------------------------------------------


class ifaddrmsg(nlmsg):
    '''
    IP address information

    C structure::

        struct ifaddrmsg {
           unsigned char ifa_family;    /* Address type */
           unsigned char ifa_prefixlen; /* Prefixlength of address */
           unsigned char ifa_flags;     /* Address flags */
           unsigned char ifa_scope;     /* Address scope */
           int           ifa_index;     /* Interface index */
        };

    '''

    prefix = 'IFA_'

    sql_constraints = {'IFA_LOCAL': "NOT NULL DEFAULT ''"}

    fields = (
        ('family', 'B'),
        ('prefixlen', 'B'),
        ('flags', 'B'),
        ('scope', 'B'),
        ('index', 'I'),
    )

    nla_map = (
        ('IFA_UNSPEC', 'hex'),
        ('IFA_ADDRESS', 'ipaddr'),
        ('IFA_LOCAL', 'ipaddr'),
        ('IFA_LABEL', 'asciiz'),
        ('IFA_BROADCAST', 'ipaddr'),
        ('IFA_ANYCAST', 'ipaddr'),
        ('IFA_CACHEINFO', 'cacheinfo'),
        ('IFA_MULTICAST', 'ipaddr'),
        ('IFA_FLAGS', 'uint32'),
    )

    class cacheinfo(nla):
        fields = (
            ('ifa_preferred', 'I'),
            ('ifa_valid', 'I'),
            ('cstamp', 'I'),
            ('tstamp', 'I'),
        )

    @staticmethod
    def flags2names(flags, family=socket.AF_INET):
        if family == socket.AF_INET6:
            ifa_f_values = IFA_F_VALUES6
        else:
            ifa_f_values = IFA_F_VALUES
        ret = []
        for f in ifa_f_values:
            if f & flags:
                ret.append(ifa_f_values[f])
        return ret

    @staticmethod
    def names2flags(flags):
        ret = 0
        for f in flags:
            if f[0] == '!':
                f = f[1:]
            else:
                ret |= IFA_F_NAMES[f]
        return ret
