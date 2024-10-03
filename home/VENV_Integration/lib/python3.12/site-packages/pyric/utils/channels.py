#!/usr/bin/env python

""" channels.py:802.11 channel/freq utilities

Copyright (C) 2016  Dale V. Patterson (wraith.wireless@yandex.com)

This program is free software:you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation,either version 3 of the License,or (at your option) any later
version.

Redistribution and use in source and binary forms,with or without modifications,
are permitted provided that the following conditions are met:
 o Redistributions of source code must retain the above copyright notice,this
   list of conditions and the following disclaimer.
 o Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 o Neither the name of the orginal author Dale V. Patterson nor the names of any
   contributors may be used to endorse or promote products derived from this
   software without specific prior written permission.

Defines ISM 2.4Ghz, UNII 5Ghz and 4.9GHz frequencies and channels

Need to define 3GHz channels/freqs

"""

__name__ = 'channels'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'August 2016'
__author__ = 'Dale Patterson'
__maintainer__ = 'Dale Patterson'
__email__ = 'wraith.wireless@yandex.com'
__status__ = 'Production'

import pyric.net.wireless.nl80211_h as nl80211h

# redefined widths (allowed in nl80211h)
CHTYPES = nl80211h.NL80211_CHAN_TYPES   # widths nl80211 supports i.e HT40- 
CHWIDTHS = nl80211h.NL80211_CHAN_WIDTHS # actual widths

# ISM Bands (ieee80211.h-> BAND_ID_2G)
ISM_24_C2F={1:2412,2:2417,3:2422,4:2427,5:2432,6:2437,7:2442,
            8:2447,9:2452,10:2457,11:2462,12:2467,13:2472,14:2484}
ISM_24_F2C={2432:5,2467:12,2437:6,2472:13,2442:7,2484:14,2412:1,
            2447:8,2417:2,2452:9,2422:3,2457:10,2427:4,2462:11}

# UNII 5 Bands (ieee80211.h-> BAND_ID_5G)
# confirm that ch 34, ch 54, 58, 62, 102, 106, 110, 114 118, 122, 126, 138, 144, 151,
# 155, 159,
UNII_5_C2F={34:5170,36:5180,38:5190,40:5200,42:5210,44:5220,46:5230,48:5240,50:5250,
            52:5260,54:5270,56:5280,58:5290,60:5300,62:5310,64:5320,100:5500,
            102:5510,104:5520,106:5530,108:5540,110:5550,112:5560,114:5570,116:5580,
            118:5590,120:5600,122:5610,124:5620,126:5630,128:5640,132:5660,136:5680,
            138:5690,140:5700,142:5710,144:5720,149:5745,151:5755,153:5765,155:5775,
            157:5785,159:5795,161:5805,165:5825}
UNII_5_F2C={5250:50,5765:153,5510:102,5640:128,5260:52,5775:155,5520:104,5270:54,
            5785:157,5530:106,5660:132,5280:56,5795:159,5540:108,5290:58,5805:161,
            5550:110,5680:136,5170:34,5300:60,5560:112,5690:138,5180:36,5310:62,
            5825:165,5570:114,5700:140,5190:38,5320:64,5580:116,5710:142,5200:40,
            5590:118,5720:144,5210:42,5600:120,5220:44,5610:122,5230:46,5745:149,
            5620:124,5240:48,5755:151,5500:100,5630:126}

# UNII 4 Bands (ieee80211.h-> BAND_ID_5G)
UNII_4_C2F={183:4915,184:4920,185:4925,187:4935,188:4940,189:4945,192:4960,196:4980}
UNII_4_F2C={4960:192,4935:187,4940:188,4945:189,4915:183,4980:196,4920:184,4925:185}

# US high powered backhaul (ieee80211.h-> BAND_ID_3G)
#131 	3657.5 	 132 	36622.5 ? 132 	3660.0 133 	3667.5 133 	3665.0
#134 	3672.5 	 134 	3670.0    135 	3677.5 136 	3682.5 136 	3680.0
#137 	3687.5 	 137 	3685.0    138 	3689.5 138 	3690.0

def channels(band=None):
    """
     returns list of channels
     :param band: one of {None=all|'ISM'=2.4GHz|'UNII'=4.9/5GHz|'UNII5'=5GHz,
      'UNII4'=4GHz}
     :returns:list of channels
    """
    if band == 'ISM': return ISM_24_C2F.keys()
    elif band == 'UNII': return UNII_5_C2F.keys() + UNII_4_C2F.keys()
    elif band == 'UNII4': return UNII_4_C2F.keys()
    elif band == 'UNII5': return UNII_5_C2F.keys()
    try:
        return sorted(ISM_24_C2F.keys() + UNII_5_C2F.keys() + UNII_4_C2F.keys())
    except TypeError:
        # python 3 doesn't like the above (uses dict_keys obj instead of list)
        return sorted(list(ISM_24_C2F.keys()) + list(UNII_5_C2F.keys()) + list(UNII_4_C2F.keys()))

def freqs(band=None):
    """
     returns list of channels
     :param band: one of {None=all|'ISM'=2.4GHz|'UNII'=4.9/5GHz|'UNII5'=5GHz,
      'UNII4'=4GHz}
     :returns:list of frequencies
    """
    if band == 'ISM': return sorted(ISM_24_F2C.keys())
    elif band == 'UNII': return sorted(UNII_5_F2C.keys() + UNII_4_F2C.keys())
    elif band == 'UNII4': return sorted(UNII_4_F2C.keys())
    elif band == 'UNII5': return sorted(UNII_5_F2C.keys())
    return sorted(ISM_24_F2C.keys() + UNII_5_F2C.keys()+ UNII_4_F2C.keys())

def ch2rf(c):
    """
     channel to frequency conversion
     :param c:channel
     :returns:frequency in MHz corresponding to channel
    """
    if c in ISM_24_C2F: return ISM_24_C2F[c]
    if c in UNII_5_C2F: return UNII_5_C2F[c]
    if c in UNII_4_C2F: return UNII_4_C2F[c]
    return None

def rf2ch(f):
    """
     frequency to channel conversion
     :param f:frequency (in MHz)
     :returns:channel number corresponding to frequency
    """
    if f in ISM_24_F2C: return ISM_24_F2C[f]
    if f in UNII_5_F2C: return UNII_5_F2C[f]
    if f in UNII_4_F2C: return UNII_4_F2C[f]
    return None
