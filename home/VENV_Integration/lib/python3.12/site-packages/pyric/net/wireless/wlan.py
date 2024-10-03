#!/usr/bin/env python
""" wlan.py: IEEE Std 802.11-2012

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

Definition of constants et al found in IEEE Std 802.11-2012

Std will refer to IEEE Std 802.11-2012
"""

__name__ = 'wlan'
__license__ = 'GPLv3'
__version__ = '0.0.1'
__date__ = 'June 2016'
__author__ = 'Dale Patterson'
__maintainer__ = 'Dale Patterson'
__email__ = 'wraith.wireless@yandex.com'
__status__ = 'Production'

"""
 cipher suite selectors - decided to (over)document this because it was such a
 hassle to figure out, want to make sure I can come back at a later date and
 figure it out again faster

 From nl80211.h @NL80211_ATTR_CIPHER_SUITES: a set of u32 values indicating the
 supported cipher suites

 The returned cipher suite (from phyinfo) for an alfa card is:
     \x01\xac\x0f\x00\x05\xac\x0f\x00\x02\xac\x0f\x00\x04\xac\x0f\x00
 which is not a nested attribute. Does 'set' mean something? There is no set
 or array or list defined netlink.h and I cannot find any reference to such in
  http://www.carisma.slowglass.com/~tgr/libnl/doc/core.html
 Another way nl80211 breaks the rules or another way I'm just not getting it?

 iw 3.17 info.c includes, but where did these values come from?
 case 0x000fac01: return "WEP40 (00-0f-ac:1)";
 case 0x000fac05: return "WEP104 (00-0f-ac:5)";
 case 0x000fac02: return "TKIP (00-0f-ac:2)";
 case 0x000fac04: return "CCMP (00-0f-ac:4)";
 case 0x000fac06: return "CMAC (00-0f-ac:6)";
 case 0x000fac08: return "GCMP (00-0f-ac:8)";
 case 0x00147201: return "WPI-SMS4 (00-14-72:1)";

 The only reference is in nl80211.h which says:
  @NL80211_KEY_CIPHER: key cipher suite (u32, as defined by IEEE 802.11 section
  7.3.2.25.1, e.g. 0x000FAC04)
 Looking in the standard we find Table 8-99 in Std which defines these values.

 Lets look in ieee80211.h and voila we find
 #define WLAN_CIPHER_SUITE_USE_GROUP	0x000FAC00
 #define WLAN_CIPHER_SUITE_WEP40		0x000FAC01
 #define WLAN_CIPHER_SUITE_TKIP		0x000FAC02
 /* reserved: 				0x000FAC03 */
 #define WLAN_CIPHER_SUITE_CCMP		0x000FAC04
 #define WLAN_CIPHER_SUITE_WEP104	0x000FAC05
 #define WLAN_CIPHER_SUITE_AES_CMAC	0x000FAC06
 #define WLAN_CIPHER_SUITE_GCMP		0x000FAC08
 #define WLAN_CIPHER_SUITE_SMS4		0x00147201

 Recall our results for the cipher key
  \x01\xac\x0f\x00\x05\xac\x0f\x00\x02\xac\x0f\x00\x04\xac\x0f\x00
 Looks similar to above. u32 is four bytes what does that give us?
  \x01\xac\x0f\x00
  \x05\xac\x0f\x00
  \x02\xac\x0f\x00
  \x04\xac\x0f\x00
 Aha, it's reversed. All we have to do is:
  hex(struct.unpack('I','\x01\xac\x0f\x00')[0])
 and we get
  '0xfac01' => WEP-40

 What a convoluted trip down the rabbit hole. This is why I hate when people
 say read the source code.

"""
#WLAN_CIPHER_SUITE_LEN = 4
WLAN_CIPHER_SUITE_GROUP    = 0x000fac00
WLAN_CIPHER_SUITE_WEP40    = 0x000fac01
WLAN_CIPHER_SUITE_TKIP     = 0x000fac02
WLAN_CIPHER_SUITE_CCMP     = 0x000fac04
WLAN_CIPHER_SUITE_WEP104   = 0x000fac05
WLAN_CIPHER_SUITE_ACS_CMAC = 0x000fac06
WLAN_CIPHER_SUITE_GCMP     = 0x000fac08
WLAN_CIPHER_SUITE_SMS4     = 0x00147201
WLAN_CIPHER_SUITE_SELECTORS = {
    WLAN_CIPHER_SUITE_GROUP:'GROUP',
    WLAN_CIPHER_SUITE_WEP40:'WEP-40',
    WLAN_CIPHER_SUITE_TKIP:'TKIP',
    WLAN_CIPHER_SUITE_CCMP:'CCMP',
    WLAN_CIPHER_SUITE_WEP104:'WEP-104',
    WLAN_CIPHER_SUITE_ACS_CMAC:'AES-CMAC',
    WLAN_CIPHER_SUITE_GCMP:'GCMP',
    WLAN_CIPHER_SUITE_SMS4:'SMS4'
}

""" COV Class Limits IAW Std Table 8-56 """
COV_CLASS_MIN =  0
COV_CLASS_MAX = 31

"""
 Retry (short and long) Limits IAW Std dot11ShortRetryLimit pg 2133 and
 dot11LongRetryLimit pg 2134
"""
RETRY_MIN = 1
RETRY_MAX = 255

""" RTS THRESH limits IAW Std dot11RTSTHRESH definition pg 2133 """
RTS_THRESH_MIN = 0
RTS_THRESH_MAX = 65536
RTS_THRESH_OFF = 4294967295 #(2^32 -1 or the max value of a u32)

""" Fragmentation THRESH limits IAW Std dot11FragmentTHRESH def. pg 2133 """
FRAG_THRESH_MIN = 256
FRAG_THRESH_MAX = 8000
FRAG_THRESH_OFF = 4294967295 #(2^32 -1 or the max value of a u32)