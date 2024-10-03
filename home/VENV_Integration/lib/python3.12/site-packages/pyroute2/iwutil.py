# -*- coding: utf-8 -*-
'''
IW module
=========

Experimental wireless module — nl80211 support.

Disclaimer
----------

Unlike IPRoute, which is mostly usable, though is far from
complete yet, the IW module is in the very initial state.
Neither the module itself, nor the message class cover the
nl80211 functionality reasonably enough. So if you're
going to use it, brace yourself — debug is coming.

Messages
--------

nl80211 messages are defined here::

    pyroute2/netlink/nl80211/__init__.py

Pls notice NLAs of type `hex`. On the early development stage
`hex` allows to inspect incoming data as a hex dump and,
occasionally, even make requests with such NLAs. But it's
not a production way.

The type `hex` in the NLA definitions means that this
particular NLA is not handled yet properly. If you want to
use some NLA which is defined as `hex` yet, pls find out a
specific type, patch the message class and submit your pull
request on github.

If you're not familiar with NLA types, take a look at RTNL
definitions::

    pyroute2/netlink/rtnl/ndmsg.py

and so on.

Communication with the kernel
-----------------------------

There are several methods of the communication with the kernel.

    * `sendto()` — lowest possible, send a raw binary data
    * `put()` — send a netlink message
    * `nlm_request()` — send a message, return the response
    * `get()` — get a netlink message
    * `recv()` — get a raw binary data from the kernel

There are no errors on `put()` usually. Any `permission denied`,
any `invalid value` errors are returned from the kernel with
netlink also. So if you do `put()`, but don't do `get()`, be
prepared to miss errors.

The preferred method for the communication is `nlm_request()`.
It tracks the message ID, returns the corresponding response.
In the case of errors `nlm_request()` raises an exception.
To get the response on any operation with nl80211, use flag
`NLM_F_ACK`.

Reverse it
----------

If you're too lazy to read the kernel sources, but still need
something not implemented here, you can use reverse engineering
on a reference implementation. E.g.::

    # strace -e trace=network -f -x -s 4096 \\
            iw phy phy0 interface add test type monitor

Will dump all the netlink traffic between the program `iw` and
the kernel. Three first packets are the generic netlink protocol
discovery, you can ignore them. All that follows, is the
nl80211 traffic::

    sendmsg(3, {msg_name(12)={sa_family=AF_NETLINK, ... },
        msg_iov(1)=[{"\\x30\\x00\\x00\\x00\\x1b\\x00\\x05 ...", 48}],
        msg_controllen=0, msg_flags=0}, 0) = 48
    recvmsg(3, {msg_name(12)={sa_family=AF_NETLINK, ... },
        msg_iov(1)=[{"\\x58\\x00\\x00\\x00\\x1b\\x00\\x00 ...", 16384}],
        msg_controllen=0, msg_flags=0}, 0) = 88
    ...

With `-s 4096` you will get the full dump. Then copy the strings
from `msg_iov` to a file, let's say `data`, and run the decoder::

    $ pwd
    /home/user/Projects/pyroute2
    $ export PYTHONPATH=`pwd`
    $ python scripts/decoder.py pyroute2.netlink.nl80211.nl80211cmd data

You will get the session decoded::

    {'attrs': [['NL80211_ATTR_WIPHY', 0],
               ['NL80211_ATTR_IFNAME', 'test'],
               ['NL80211_ATTR_IFTYPE', 6]],
     'cmd': 7,
     'header': {'flags': 5,
                'length': 48,
                'pid': 3292542647,
                'sequence_number': 1430426434,
                'type': 27},
     'reserved': 0,
     'version': 0}
    {'attrs': [['NL80211_ATTR_IFINDEX', 23811],
               ['NL80211_ATTR_IFNAME', 'test'],
               ['NL80211_ATTR_WIPHY', 0],
               ['NL80211_ATTR_IFTYPE', 6],
               ['NL80211_ATTR_WDEV', 4],
               ['NL80211_ATTR_MAC', 'a4:4e:31:43:1c:7c'],
               ['NL80211_ATTR_GENERATION', '02:00:00:00']],
     'cmd': 7,
     'header': {'flags': 0,
                'length': 88,
                'pid': 3292542647,
                'sequence_number': 1430426434,
                'type': 27},
     'reserved': 0,
     'version': 1}

Now you know, how to do a request and what you will get as a
response. Sample collected data is in the `scripts` directory.

Submit changes
--------------

Please do not hesitate to submit the changes on github. Without
your patches this module will not evolve.
'''
import logging

from pyroute2.netlink import NLM_F_ACK, NLM_F_DUMP, NLM_F_REQUEST
from pyroute2.netlink.nl80211 import (
    BSS_STATUS_NAMES,
    CHAN_WIDTH,
    IFTYPE_NAMES,
    NL80211,
    NL80211_NAMES,
    SCAN_FLAGS_NAMES,
    nl80211cmd,
)

log = logging.getLogger(__name__)


class IW(NL80211):
    def __init__(self, *argv, **kwarg):
        # get specific groups kwarg
        if 'groups' in kwarg:
            groups = kwarg['groups']
            del kwarg['groups']
        else:
            groups = None

        # get specific async kwarg
        if 'async' in kwarg:
            # FIXME
            # raise deprecation error after 0.5.3
            #
            log.warning(
                'use "async_cache" instead of "async", '
                '"async" is a keyword from Python 3.7'
            )
            kwarg['async_cache'] = kwarg.pop('async')

        if 'async_cache' in kwarg:
            async_cache = kwarg.pop('async_cache')
        else:
            async_cache = False

        # align groups with async_cache
        if groups is None:
            groups = ~0 if async_cache else 0

        # continue with init
        super(IW, self).__init__(*argv, **kwarg)

        # do automatic bind
        # FIXME: unfortunately we can not omit it here
        self.bind(groups, async_cache=async_cache)

    def del_interface(self, dev):
        '''
        Delete a virtual interface

            - dev — device index
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_DEL_INTERFACE']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', dev]]
        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def add_interface(self, ifname, iftype, dev=None, phy=0):
        '''
        Create a virtual interface

            - ifname — name of the interface to create
            - iftype — interface type to create
            - dev — device index
            - phy — phy index

        One should specify `dev` (device index) or `phy`
        (phy index). If no one specified, phy == 0.

        `iftype` can be integer or string:

        1. adhoc
        2. station
        3. ap
        4. ap_vlan
        5. wds
        6. monitor
        7. mesh_point
        8. p2p_client
        9. p2p_go
        10. p2p_device
        11. ocb
        '''
        # lookup the interface type
        iftype = IFTYPE_NAMES.get(iftype, iftype)
        if not isinstance(iftype, int):
            raise TypeError('iftype must be int')

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_NEW_INTERFACE']
        msg['attrs'] = [
            ['NL80211_ATTR_IFNAME', ifname],
            ['NL80211_ATTR_IFTYPE', iftype],
        ]
        if dev is not None:
            msg['attrs'].append(['NL80211_ATTR_IFINDEX', dev])
        elif phy is not None:
            msg['attrs'].append(['NL80211_ATTR_WIPHY', phy])
        else:
            raise TypeError('no device specified')
        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def list_dev(self):
        '''
        Get list of all wifi network interfaces
        '''
        return self.get_interfaces_dump()

    def list_wiphy(self):
        '''
        Get list of all phy devices
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_WIPHY']
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def _get_phy_name(self, attr):
        return 'phy%i' % attr.get_attr('NL80211_ATTR_WIPHY')

    def _get_frequency(self, attr):
        return attr.get_attr('NL80211_ATTR_WIPHY_FREQ') or 0

    def get_interfaces_dict(self):
        '''
        Get interfaces dictionary
        '''
        ret = {}
        for wif in self.get_interfaces_dump():
            chan_width = wif.get_attr('NL80211_ATTR_CHANNEL_WIDTH')
            freq = self._get_frequency(wif) if chan_width is not None else 0
            wifname = wif.get_attr('NL80211_ATTR_IFNAME')
            ret[wifname] = [
                wif.get_attr('NL80211_ATTR_IFINDEX'),
                self._get_phy_name(wif),
                wif.get_attr('NL80211_ATTR_MAC'),
                freq,
                chan_width,
            ]
        return ret

    def get_interfaces_dump(self):
        '''
        Get interfaces dump
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_INTERFACE']
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def get_interface_by_phy(self, attr):
        '''
        Get interface by phy ( use x.get_attr('NL80211_ATTR_WIPHY') )
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_INTERFACE']
        msg['attrs'] = [['NL80211_ATTR_WIPHY', attr]]
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def get_interface_by_ifindex(self, ifindex):
        '''
        Get interface by ifindex ( use x.get_attr('NL80211_ATTR_IFINDEX')
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_INTERFACE']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST
        )

    def get_stations(self, ifindex):
        '''
        Get stations by ifindex
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_STATION']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def join_ibss(
        self,
        ifindex,
        ssid,
        freq,
        bssid=None,
        channel_fixed=False,
        width=None,
        center=None,
        center2=None,
    ):
        '''
        Connect to network by ssid
            - ifindex - IFINDEX of the interface to perform the connection
            - ssid - Service set identification
            - freq - Frequency in MHz
            - bssid - The MAC address of target interface
            - channel_fixed: Boolean flag
            - width - Channel width
            - center - Central frequency of the 40/80/160 MHz channel
            - center2 - Center frequency of second segment if 80P80

        If the flag of channel_fixed is True, one should specify both the width
        and center of the channel

        `width` can be integer of string:

        0. 20_noht
        1. 20
        2. 40
        3. 80
        4. 80p80
        5. 160
        6. 5
        7. 10
        '''

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_JOIN_IBSS']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_SSID', ssid],
            ['NL80211_ATTR_WIPHY_FREQ', freq],
        ]

        if channel_fixed:
            msg['attrs'].append(['NL80211_ATTR_FREQ_FIXED', None])
            width = CHAN_WIDTH.get(width, width)
            if not isinstance(width, int):
                raise TypeError('width must be int')
            if width in [2, 3, 5] and center:
                msg['attrs'].append(['NL80211_ATTR_CHANNEL_WIDTH', width])
                msg['attrs'].append(['NL80211_ATTR_CENTER_FREQ1', center])
            elif width == 4 and center and center2:
                msg['attrs'].append(['NL80211_ATTR_CHANNEL_WIDTH', width])
                msg['attrs'].append(['NL80211_ATTR_CENTER_FREQ1', center])
                msg['attrs'].append(['NL80211_ATTR_CENTER_FREQ2', center2])
            elif width in [0, 1, 6, 7]:
                msg['attrs'].append(['NL80211_ATTR_CHANNEL_WIDTH', width])
            else:
                raise TypeError('No channel specified')

        if bssid is not None:
            msg['attrs'].append(['NL80211_ATTR_MAC', bssid])

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def leave_ibss(self, ifindex):
        '''
        Leave the IBSS -- the IBSS is determined by the network interface
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_LEAVE_IBSS']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def authenticate(self, ifindex, bssid, ssid, freq, auth_type=0):
        '''
        Send an Authentication management frame.
        '''

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_AUTHENTICATE']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_MAC', bssid],
            ['NL80211_ATTR_SSID', ssid],
            ['NL80211_ATTR_WIPHY_FREQ', freq],
            ['NL80211_ATTR_AUTH_TYPE', auth_type],
        ]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def deauthenticate(self, ifindex, bssid, reason_code=0x01):
        '''
        Send a Deauthentication management frame.
        '''

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_DEAUTHENTICATE']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_MAC', bssid],
            ['NL80211_ATTR_REASON_CODE', reason_code],
        ]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def associate(self, ifindex, bssid, ssid, freq, info_elements=None):
        '''
        Send an Association request frame.
        '''

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_ASSOCIATE']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_MAC', bssid],
            ['NL80211_ATTR_SSID', ssid],
            ['NL80211_ATTR_WIPHY_FREQ', freq],
        ]

        if info_elements is not None:
            msg['attrs'].append(['NL80211_ATTR_IE', info_elements])

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def disassociate(self, ifindex, bssid, reason_code=0x03):
        '''
        Send a Disassociation management frame.
        '''

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_DISASSOCIATE']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_MAC', bssid],
            ['NL80211_ATTR_REASON_CODE', reason_code],
        ]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def connect(self, ifindex, ssid, bssid=None):
        '''
        Connect to the ap with ssid and bssid
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_CONNECT']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_SSID', ssid],
        ]
        if bssid is not None:
            msg['attrs'].append(['NL80211_ATTR_MAC', bssid])

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def disconnect(self, ifindex):
        '''
        Disconnect the device
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_DISCONNECT']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]
        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def survey(self, ifindex):
        '''
        Return the survey info.
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_SURVEY']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]
        return self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def scan(self, ifindex, ssids=None, flush_cache=False):
        '''
        Trigger scan and get results.

        Triggering scan usually requires root, and can take a
        couple of seconds.
        '''
        # Prepare a second netlink socket to get the scan results.
        # The issue is that the kernel can send the results notification
        # before we get answer for the NL80211_CMD_TRIGGER_SCAN
        nsock = NL80211()
        nsock.bind()
        nsock.add_membership('scan')

        # send scan request
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_TRIGGER_SCAN']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]

        # If a list of SSIDs is provided, active scanning should be performed
        if ssids is not None:
            if isinstance(ssids, list):
                msg['attrs'].append(['NL80211_ATTR_SCAN_SSIDS', ssids])

        scan_flags = 0
        if flush_cache:
            # Flush the cache before scanning
            scan_flags |= SCAN_FLAGS_NAMES['NL80211_SCAN_FLAG_FLUSH']
            msg['attrs'].append(['NL80211_ATTR_SCAN_FLAGS', scan_flags])

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

        # monitor the results notification on the secondary socket
        scanResultNotFound = True
        while scanResultNotFound:
            listMsg = nsock.get()
            for msg in listMsg:
                if msg["event"] == "NL80211_CMD_NEW_SCAN_RESULTS":
                    scanResultNotFound = False
                    break
        # close the secondary socket
        nsock.close()

        # request the results
        msg2 = nl80211cmd()
        msg2['cmd'] = NL80211_NAMES['NL80211_CMD_GET_SCAN']
        msg2['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]
        return self.nlm_request(
            msg2, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

    def get_associated_bss(self, ifindex):
        '''
        Returns the same info like scan() does, but only about the
        currently associated BSS.

        Unlike scan(), it returns immediately and doesn't require root.
        '''
        # When getting scan results without triggering scan first,
        # you'll always get the information about currently associated BSS
        #
        # However, it may return other BSS, if last scan wasn't very
        # long time go

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_SCAN']
        msg['attrs'] = [['NL80211_ATTR_IFINDEX', ifindex]]

        res = self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
        )

        for x in res:
            attr_bss = x.get_attr('NL80211_ATTR_BSS')
            if attr_bss is not None:
                status = attr_bss.get_attr('NL80211_BSS_STATUS')
                if status in (
                    BSS_STATUS_NAMES['associated'],
                    BSS_STATUS_NAMES['ibss_joined'],
                ):
                    return x

        return None

    def get_regulatory_domain(self, attr=None):
        '''
        Get regulatory domain information. If attr specified, get regulatory
        domain information for this device
        ( use x.get_attr('NL80211_ATTR_WIPHY') ).
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_GET_REG']
        flags = NLM_F_REQUEST
        if attr is None:
            flags |= NLM_F_DUMP
        else:
            msg['attrs'] = [['NL80211_ATTR_WIPHY', attr]]

        return self.nlm_request(msg, msg_type=self.prid, msg_flags=flags)

    def set_regulatory_domain(self, alpha2):
        '''
        Set regulatory domain.
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_REQ_SET_REG']
        msg['attrs'] = [['NL80211_ATTR_REG_ALPHA2', alpha2]]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def set_tx_power(self, dev, mode, mbm=None):
        '''
        Set TX power of interface.

            - dev — device index
            - mode — TX power setting (0 - auto, 1 - limit, 2 - fixed)
            - mbm — TX power in mBm (dBm * 100)
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_SET_WIPHY']
        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', dev],
            ['NL80211_ATTR_WIPHY_TX_POWER_SETTING', mode],
        ]
        if mbm is not None:
            msg['attrs'].append(['NL80211_ATTR_WIPHY_TX_POWER_LEVEL', mbm])

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def set_wiphy_netns_by_pid(self, wiphy, pid):
        '''
        Set wiphy network namespace to process network namespace.
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_SET_WIPHY_NETNS']
        msg['attrs'] = [
            ['NL80211_ATTR_WIPHY', wiphy],
            ['NL80211_ATTR_PID', pid],
        ]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def set_wiphy_netns_by_fd(self, wiphy, netns_fd):
        '''
        Set wiphy network namespace to namespace referenced by fd.
        '''
        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_SET_WIPHY_NETNS']
        msg['attrs'] = [
            ['NL80211_ATTR_WIPHY', wiphy],
            ['NL80211_ATTR_NETNS_FD', netns_fd],
        ]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def set_interface_type(self, ifindex, iftype):
        '''
        Set interface type
            - ifindex — device index
            - iftype — interface type

        `iftype` can be integer or string:
        1. adhoc
        2. station
        3. ap
        4. ap_vlan
        5. wds
        6. monitor
        7. mesh_point
        8. p2p_client
        9. p2p_go
        10. p2p_device
        11. ocb
        '''

        iftype = IFTYPE_NAMES.get(iftype, iftype)
        if not isinstance(iftype, int):
            raise TypeError('iftype must be int')

        msg = nl80211cmd()
        msg['cmd'] = NL80211_NAMES['NL80211_CMD_SET_INTERFACE']

        msg['attrs'] = [
            ['NL80211_ATTR_IFINDEX', ifindex],
            ['NL80211_ATTR_IFTYPE', iftype],
        ]

        self.nlm_request(
            msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_ACK
        )

    def get_interface_type(self, ifindex) -> str:
        '''
        return interface type name
        '''
        dump = self.get_interface_by_ifindex(ifindex)
        type = None
        for d in dump:
            type = d.get_attr('NL80211_ATTR_IFTYPE')

        if type is not None:
            for key, value in IFTYPE_NAMES.items():
                if value == type:
                    res = key
        else:
            res = 'Not Found Type'

        return res
