#!/usr/bin/env python
""" sockios_h.py: definitions for INET interface module

/*
 * INET	An implementation of the TCP/IP protocol suite for the LINUX
 *		operating system.  INET is implemented using the  BSD Socket
 *		interface as the means of communication with the user level.
 *
 *		Global definitions for the INET interface module.
 *
 * Version:	@(#)if.h	1.0.2	04/18/93
 *
 * Authors:	Original taken from Berkeley UNIX 4.3, (c) UCB 1982-1988
 *		Ross Biro
 *		Fred N. van Kempen, <waltje@uWalt.NL.Mugnet.ORG>
 *
 *		This program is free software; you can redistribute it and/or
 *		modify it under the terms of the GNU General Public License
 *		as published by the Free Software Foundation; either version
 *		2 of the License, or (at your option) any later version.
 */

Copyright (C) 2016  Dale V. Patterson (wraith.wireless@yandex.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Redistribution and use in source and binary forms, with or without modifications,
are permitted provided that the following conditions are met:
 o Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
 o Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 o Neither the name of the orginal author Dale V. Patterson nor the names of any
   contributors may be used to endorse or promote products derived from this
   software without specific prior written permission.

A port of if.h, with some definitions from iw_param, wireless.h and sockaddr
from socket.h to python

 Additionally
  1) imports definitions from wireless_h to check if a nic is wireless and get
     the tx-power
  2) defines the sockaddr struct from netint/in.h

"""

__name__ = 'if_h'
__license__ = 'GPLv3'
__version__ = '0.0.3'
__date__ = 'February 2016'
__author__ = 'Dale Patterson'
__maintainer__ = 'Dale Patterson'
__email__ = 'wraith.wireless@yandex.com'
__status__ = 'Production'

import struct
import pyric.net.sockios_h as sioch
import sys
_PY3_ = sys.version_info.major == 3

IFNAMSIZ = 16
IFALIASZ = 256

# Standard interface flags (netdevice->flags).
IFF_UP          = 0x1	  # interface is up
IFF_BROADCAST	= 0x2	  # broadcast address valid
IFF_DEBUG       = 0x4	  # turn on debugging
IFF_LOOPBACK	= 0x8	  # is a loopback net
IFF_POINTOPOINT	= 0x10	  # interface is has p-p link
IFF_NOTRAILERS	= 0x20	  # avoid use of trailers
IFF_RUNNING     = 0x40	  # interface RFC2863 OPER_UP
IFF_NOARP       = 0x80	  # no ARP protocol
IFF_PROMISC     = 0x100	  # receive all packets
IFF_ALLMULTI	= 0x200	  # receive all multicast packets
IFF_MASTER      = 0x400	  # master of a load balancer
IFF_SLAVE       = 0x800	  # slave of a load balancer
IFF_MULTICAST	= 0x1000  # Supports multicast
IFF_PORTSEL     = 0x2000  # can set media type
IFF_AUTOMEDIA	= 0x4000  # auto media select active
IFF_DYNAMIC     = 0x8000  # dialup device with changing addresses
IFF_LOWER_UP	= 0x10000 # driver signals L1 up
IFF_DORMANT     = 0x20000 # driver signals dormant
IFF_ECHO        = 0x40000 # echo sent packets

IFF_VOLATILE = IFF_LOOPBACK | IFF_POINTOPOINT | IFF_BROADCAST | IFF_ECHO | \
               IFF_MASTER | IFF_SLAVE | IFF_RUNNING | IFF_LOWER_UP | IFF_DORMANT

# Private (from user) interface flags (netdevice->priv_flags).
IFF_802_1Q_VLAN      = 0x1   # 802.1Q VLAN device.
IFF_EBRIDGE          = 0x2   # Ethernet bridging device.
IFF_SLAVE_INACTIVE   = 0x4   # bonding slave not the curr. active
IFF_MASTER_8023AD    = 0x8   # bonding master, 802.3ad.
IFF_MASTER_ALB	     = 0x10  # bonding master, balance-alb.
IFF_BONDING          = 0x20  # bonding master or slave
IFF_SLAVE_NEEDARP    = 0x40  # need ARPs for validation
IFF_ISATAP           = 0x80  # ISATAP interface (RFC4214)
IFF_MASTER_ARPMON    = 0x100 # bonding master, ARP mon in use
IFF_WAN_HDLC	     = 0x200 # WAN HDLC device
IFF_XMIT_DST_RELEASE = 0x400 # dev_hard_start_xmit() is allowed to release skb->dst

IFF_DONT_BRIDGE      = 0x800	# disallow bridging this ether dev
IFF_DISABLE_NETPOLL  = 0x1000   # disable netpoll at run-time
IFF_MACVLAN_PORT     = 0x2000   # device used as macvlan port
IFF_BRIDGE_PORT	     = 0x4000	# device used as bridge port
IFF_OVS_DATAPATH     = 0x8000   # device used as Open vSwitch datapath port
IFF_TX_SKB_SHARING   = 0x10000  # The interface supports sharing skbs on transmit
IFF_UNICAST_FLT	     = 0x20000	# Supports unicast filtering
IFF_TEAM_PORT	     = 0x40000	# device used as team port
IFF_SUPP_NOFCS	     = 0x80000	# device supports sending custom FCS
IFF_LIVE_ADDR_CHANGE = 0x100000	# device supports hardware address change when it's running
IFF_MACVLAN          = 0x200000	# Macvlan device

IF_GET_IFACE = 0x0001 # for querying only
IF_GET_PROTO = 0x0002

# For definitions see hdlc.h
IF_IFACE_V35	     = 0x1000 # V.35 serial interface
IF_IFACE_V24	     = 0x1001 # V.24 serial interface
IF_IFACE_X21	     = 0x1002 # X.21 serial interface
IF_IFACE_T1          = 0x1003 # T1 telco serial interface
IF_IFACE_E1          = 0x1004 # E1 telco serial interface
IF_IFACE_SYNC_SERIAL = 0x1005 # can't be set by software
IF_IFACE_X21D        = 0x1006 # X.21 Dual Clocking (FarSite)

# For definitions see hdlc.h
IF_PROTO_HDLC	        = 0x2000 # raw HDLC protocol
IF_PROTO_PPP	        = 0x2001 # PPP protocol
IF_PROTO_CISCO	        = 0x2002 # Cisco HDLC protocol
IF_PROTO_FR             = 0x2003 # Frame Relay protocol
IF_PROTO_FR_ADD_PVC     = 0x2004 # Create FR PVC
IF_PROTO_FR_DEL_PVC     = 0x2005 # Delete FR PVC
IF_PROTO_X25	        = 0x2006 # X.25
IF_PROTO_HDLC_ETH       = 0x2007 # raw HDLC, Ethernet emulation
IF_PROTO_FR_ADD_ETH_PVC = 0x2008 # Create FR Ethernet-bridged PVC
IF_PROTO_FR_DEL_ETH_PVC = 0x2009 # Delete FR Ethernet-bridged PVC
IF_PROTO_FR_PVC	        = 0x200A # for reading PVC status
IF_PROTO_FR_ETH_PVC     = 0x200B
IF_PROTO_RAW            = 0x200C # RAW Socket

# RFC 2863 operational status
IF_OPER_UNKNOWN         = 0
IF_OPER_NOTPRESENT      = 1
IF_OPER_DOWN            = 2
IF_OPER_LOWERLAYERDOWN  = 3
IF_OPER_TESTING         = 4
IF_OPER_DORMANT         = 5
IF_OPER_UP              = 6

# link modes
IF_LINK_MODE_DEFAULT = 0
IF_LINK_MODE_DORMANT = 1 # limit upward transition to dormant

"""
struct sockaddr {
    sa_family_t     sa_family;      /* address family, AF_xxx       */
    char            sa_data[14];    /* 14 bytes of protocol address */
};
 NOTE:
  1) for our purposes, we use only 6 characters, 6 octets for a hw addr and 4
     octets for an ip4 addr.
  2) For whatever reason, all ioctl calls accept and return ip4 addresses
     prefixed by two null bytes
"""
AF_UNSPEC                 = 0   # from socket.h sa_family unspecified
ARPHRD_ETHER              = 1   # from net/if_arp.h sa_family ethernet a.k.a AF_LOCAL
ARPHRD_IEEE80211          = 801 # net/if_arp.h sa_family IEEE 802.11
ARPHRD_IEEE80211_PRISM    = 802 # net/if_arp.h sa_family Prism2 header
ARPHRD_IEEE80211_RADIOTAP = 803 # net/if_arp.h sa_family radiotap header
AF_INET      = 2  # from socket.h ip address (ip4)
sa_addr = 'H6B'
def sockaddr(sa_family,sa_data=None):
    """
     create a sockaddr
     :param sa_family: address family
     :param sa_data: protocal address (up to 14 bytes)
     :returns: packed sockaddr
    """
    # the address must be "prepended" with sa_family IOT follow the sockaddr struct
    vs = [sa_family]
    if sa_data is None: vs.extend([0] * 6) # send empty bytes for ioctl to fill in
    else:
        if sa_family == ARPHRD_ETHER:
            vs.extend([int(x,16) for x in sa_data.split(':')])
        elif sa_family == AF_INET:
            # we need 6 octets - so prepend two 0's to the ip addr
            vs.extend([int(x) for x in ('0.0.'+sa_data).split('.')])
        else:
            raise AttributeError("sa_family {0} not supported".format(sa_family))
    return struct.pack(sa_addr,*vs)

"""
 Interface request structure used for socket ioctl's. All interface ioctl's must
 have parameter definitions which begin with ifr_name. The remainder may be
 interface specific.

struct ifreq {

	union
	{
		char	ifrn_name[IFNAMSIZ];		# if name, e.g. "en0"
	} ifr_ifrn;

	union {
		struct	sockaddr ifru_addr;
		struct	sockaddr ifru_dstaddr;
		struct	sockaddr ifru_broadaddr;
		struct	sockaddr ifru_netmask;
		struct  sockaddr ifru_hwaddr;
		short	ifru_flags;
		int	ifru_ivalue;
		int	ifru_mtu;
		struct  ifmap ifru_map;
		char	ifru_slave[IFNAMSIZ];	# Just fits the size
		char	ifru_newname[IFNAMSIZ];
		void *	ifru_data;
		struct	if_settings ifru_settings;
	} ifr_ifru;
};

 from wireless.h we build
struct	iw_param
{
  __s32	value;		/* The value of the parameter itself */
  __u8		fixed;		/* Hardware should not use auto select */
  __u8		disabled;	/* Disable the feature */
  __u16	flags;		/* Various specifc flags (if any) */
 to get the txpower and verify the presense of wireless extensions
};
"""
ifr_name = '{0}s'.format(IFNAMSIZ)        # formats for ifreq struct
ifr_flags = 'h'
ifr_ifindex = 'i'
ifr_iwname = '{0}s'.format(256-IFNAMSIZ)  # dirty hack to get an unknown string back
ifr_iwtxpwr = 'iBBH'
IFNAMELEN = struct.calcsize(ifr_name)     # lengths
IFADDRLEN = struct.calcsize(sa_addr)      # length of both ip4 and mac
IFFLAGLEN = struct.calcsize(ifr_flags)
IFIFINDEXLEN = struct.calcsize(ifr_ifindex)
IWNAMELEN = struct.calcsize(ifr_iwname)
IWTXPWRLEN = struct.calcsize(ifr_iwtxpwr)

# noinspection PyArgumentList
def ifreq(ifrn,ifru=None,param=None):
    """
     creates a 'packed' struct cooresponding loosely to the ifreq struct. Padded
     bytes are added on all 'gets' otherwise the ioctl will only return the
     number of bytes sent
     :param ifrn: name of interface/nic
     :param ifru: from SOCKIOS_H, defines what type of ifreq struct to pack
     :param param: list of params If None, pad byes are added having the size of
      the appropriate param. If a hwaddr, must be a sockaddr family & string of
      form "XX:XX:XX:XX:XX:XX" and if an ipaddr must be a sockaddr family & string
      form "XXX.XXX.XXX.XXX", if flags must be an integer (c short) or (int)
      respectively
     :returns: packed ifreq
     NOTE: ifreq will return AttributeError for any caught exception
    """
    # pack the nic
    if _PY3_: ifrn = bytes(ifrn,'ascii')
    try:
        # NOTE: don't need to keep the name to 16 chars as struct does it for us
        ifr = struct.pack(ifr_name,ifrn)
    except struct.error:
        raise AttributeError("ifr_ifrn (dev name) {0} is invalid".format(ifrn))

    try:
        if not ifru: pass # only pass the device name
        elif ifru == sioch.SIOCGIFHWADDR: # get hwaddr
            ifr += sockaddr(ARPHRD_ETHER,None)
        elif ifru == sioch.SIOCSIFHWADDR: # set hwaddr
            ifr += sockaddr(ARPHRD_ETHER,param[0])
        elif ifru == sioch.SIOCGIFADDR or \
             ifru == sioch.SIOCGIFNETMASK or \
             ifru == sioch.SIOCGIFBRDADDR: # get ip4, netmask or broadcast address
            ifr += sockaddr(AF_INET,None)
        elif ifru == sioch.SIOCSIFADDR or \
             ifru == sioch.SIOCSIFNETMASK or \
             ifru == sioch.SIOCSIFBRDADDR:  # set ip4, netmask or broadcast address
            ifr += sockaddr(AF_INET,param[0])
        elif ifru == sioch.SIOCGIFFLAGS: # get flags
            ifr += struct.pack('{0}x'.format(IFFLAGLEN))
        elif ifru == sioch.SIOCSIFFLAGS: # set flags
            ifr += struct.pack(ifr_flags,param[0])
        elif ifru == sioch.SIOCGIFINDEX: # get if index
            ifr += struct.pack('{0}x'.format(IFIFINDEXLEN))
        elif ifru == sioch.SIOCGIWNAME: # get iw name
            ifr += struct.pack('{0}x'.format(IWNAMELEN))
        elif ifru == sioch.SIOCGIWTXPOW: # get tx pwr
            ifr += struct.pack('{0}x'.format(IWTXPWRLEN))
        else:
            raise AttributeError("ifru {0} not supported".format(ifru))
    except (TypeError,IndexError):
        raise AttributeError("parameters are invalid")

    return ifr