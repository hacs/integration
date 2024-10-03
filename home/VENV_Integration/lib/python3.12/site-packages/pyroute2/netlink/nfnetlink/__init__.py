'''
Nfnetlink
=========

The support of nfnetlink families is now at the
very beginning. So there is no public exports
yet, but you can review the code. Work is in
progress, stay tuned.

nf-queue
++++++++

Netfilter protocol for NFQUEUE iptables target.
'''

from pyroute2.netlink import nlmsg

NFNL_SUBSYS_NONE = 0
NFNL_SUBSYS_CTNETLINK = 1
NFNL_SUBSYS_CTNETLINK_EXP = 2
NFNL_SUBSYS_QUEUE = 3
NFNL_SUBSYS_ULOG = 4
NFNL_SUBSYS_OSF = 5
NFNL_SUBSYS_IPSET = 6
NFNL_SUBSYS_ACCT = 7
NFNL_SUBSYS_CTNETLINK_TIMEOUT = 8
NFNL_SUBSYS_CTHELPER = 9
NFNL_SUBSYS_NFTABLES = 10
NFNL_SUBSYS_NFT_COMPAT = 11
NFNL_SUBSYS_COUNT = 12

# multicast group ids (for use with {add,drop}_membership)
NFNLGRP_NONE = 0
NFNLGRP_CONNTRACK_NEW = 1
NFNLGRP_CONNTRACK_UPDATE = 2
NFNLGRP_CONNTRACK_DESTROY = 3
NFNLGRP_CONNTRACK_EXP_NEW = 4
NFNLGRP_CONNTRACK_EXP_UPDATE = 5
NFNLGRP_CONNTRACK_EXP_DESTROY = 6
NFNLGRP_NFTABLES = 7
NFNLGRP_ACCT_QUOTA = 8
NFNLGRP_NFTRACE = 9


class nfgen_msg(nlmsg):
    fields = (('nfgen_family', 'B'), ('version', 'B'), ('res_id', '!H'))
