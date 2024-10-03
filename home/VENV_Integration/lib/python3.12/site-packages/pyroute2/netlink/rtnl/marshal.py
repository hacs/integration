from pyroute2.netlink import rtnl
from pyroute2.netlink.nlsocket import Marshal
from pyroute2.netlink.rtnl.fibmsg import fibmsg
from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg
from pyroute2.netlink.rtnl.ifstatsmsg import ifstatsmsg
from pyroute2.netlink.rtnl.ndmsg import ndmsg
from pyroute2.netlink.rtnl.ndtmsg import ndtmsg
from pyroute2.netlink.rtnl.nsidmsg import nsidmsg
from pyroute2.netlink.rtnl.rtmsg import rtmsg
from pyroute2.netlink.rtnl.tcmsg import tcmsg


class MarshalRtnl(Marshal):
    msg_map = {
        rtnl.RTM_NEWLINK: ifinfmsg,
        rtnl.RTM_DELLINK: ifinfmsg,
        rtnl.RTM_GETLINK: ifinfmsg,
        rtnl.RTM_SETLINK: ifinfmsg,
        rtnl.RTM_NEWADDR: ifaddrmsg,
        rtnl.RTM_DELADDR: ifaddrmsg,
        rtnl.RTM_GETADDR: ifaddrmsg,
        rtnl.RTM_NEWROUTE: rtmsg,
        rtnl.RTM_DELROUTE: rtmsg,
        rtnl.RTM_GETROUTE: rtmsg,
        rtnl.RTM_NEWRULE: fibmsg,
        rtnl.RTM_DELRULE: fibmsg,
        rtnl.RTM_GETRULE: fibmsg,
        rtnl.RTM_NEWNEIGH: ndmsg,
        rtnl.RTM_DELNEIGH: ndmsg,
        rtnl.RTM_GETNEIGH: ndmsg,
        rtnl.RTM_NEWQDISC: tcmsg,
        rtnl.RTM_DELQDISC: tcmsg,
        rtnl.RTM_GETQDISC: tcmsg,
        rtnl.RTM_NEWTCLASS: tcmsg,
        rtnl.RTM_DELTCLASS: tcmsg,
        rtnl.RTM_GETTCLASS: tcmsg,
        rtnl.RTM_NEWTFILTER: tcmsg,
        rtnl.RTM_DELTFILTER: tcmsg,
        rtnl.RTM_GETTFILTER: tcmsg,
        rtnl.RTM_NEWNEIGHTBL: ndtmsg,
        rtnl.RTM_GETNEIGHTBL: ndtmsg,
        rtnl.RTM_SETNEIGHTBL: ndtmsg,
        rtnl.RTM_NEWNSID: nsidmsg,
        rtnl.RTM_DELNSID: nsidmsg,
        rtnl.RTM_GETNSID: nsidmsg,
        rtnl.RTM_NEWSTATS: ifstatsmsg,
        rtnl.RTM_GETSTATS: ifstatsmsg,
        rtnl.RTM_NEWLINKPROP: ifinfmsg,
        rtnl.RTM_DELLINKPROP: ifinfmsg,
    }

    def fix_message(self, msg):
        # FIXME: pls do something with it
        try:
            msg['event'] = rtnl.RTM_VALUES[msg['header']['type']]
        except:
            pass
