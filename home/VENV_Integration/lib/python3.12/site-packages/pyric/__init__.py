#!/usr/bin/env python
""" pyric Python Radio Interface Controller

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

Defines the PyRIC error class and constants for some errors. All pyric errors
will follow the 2-tuple form of EnvironmentError. Also defines constansts for
PyPI packaging.

WARNING: DO NOT import *

Requires:
 linux (3.x or 4.x kernel)
 Python 2.7

 pyric 0.1.5 through 0.1.6
  desc: wireless nic library: wireless radio identification, manipulation, enumeration
   concentrate on STA/AP related functionality
  includes: /nlhelp /lib /net /utils pyw.py
  changes:
   See CHANGES in top-level directory
"""

__name__ = 'pyric'
__license__ = 'GPLv3'
__version__ = '0.1.6.3'
__date__ = 'December 2016'
__author__ = 'Dale Patterson'
__maintainer__ = 'Dale Patterson'
__email__ = 'wraith.wireless@yandex.com'
__status__ = 'Production'

"""
 define pyric exceptions
  all exceptions are tuples t=(error code,error message)
  we use error codes defined in errno, using EUNDEF = -1 to define an undefined
  error I don't like importing all from errno but it provides conformity in
  error handling i.e modules using pyric.error do not need to call pyric.EUNDEF
  and errno.EINVAL but can call pyric.EUNDEF and pyric.EINVAL
"""
EUNDEF = -1                   # undefined error
from errno import *           # make all errno errors pyric errors
errorcode[EUNDEF] = "EUNDEF"  # add ours to errorcode dicts
class error(EnvironmentError):
    def __init__(self,errno,errmsg=None):
        if not errmsg: errmsg = strerror(errno)
        EnvironmentError.__init__(self,errno,errmsg)

def strerror(errno):
    """
    :param errno: error code
    :returns: error message
    """
    import os
    if errno < 0: return "Undefined error"
    elif errno == EPERM: return "Superuser privileges required"
    elif errno == EINVAL: return "Invalid parameter"
    elif errno == EBUSY:
        msg = "{0}. Make sure Card is up and no other devices share the same phy"
        return msg.format(os.strerror(EBUSY))
    elif errno == ENFILE: return "There are no available netlink sockets"
    else:
        return os.strerror(errno)

# for setup.py use
# redefine version for easier access
version = __version__

# define long description
long_desc = """
# PyRIC 0.1.6.3: Python Radio Interface Controller
## Linux wireless library for the Python Wireless Developer and Pentester

## DESCRIPTION:
PyRIC (is a Linux only) library providing wireless developers and pentesters the
ability to identify, enumerate and manipulate their system's wireless cards
programmatically in Python. Pentesting applications and scripts written in Python
have increased dramatically in recent years. However, these tools still rely on
Linux command lines tools for setup/preparation and restoration of the system for
use. Until now. Why use subprocess.Popen, regular expressions and str.find to
interact with your wireless cards? PyRIC is:

1. Pythonic: no ctypes, SWIG etc. PyRIC redefines C header files as Python and
uses sockets to communicate with the kernel.
2. Self-sufficient: No third-party files used. PyRIC is completely self-contained.
3. Fast: (relatively speaking) PyRIC is faster than using command line tools
through subprocess.Popen
4. Parseless: Get the output you want without parsing output from command line
tools. Never worry about newer iw versions and having to rewrite your parsers.
5. Easy: If you can use iw, you can use PyRIC.

## CURRENT STATE
ATT, PyRIC pyw provides the following:
* enumerate interfaces and wireless interfaces
* identify a cards chipset and driver
* get/set hardware address
* get/set ip4 address, netmask and or broadcast
* turn card on/off
* get supported standards
* get supported commands
* get supported modes
* get dev info
* get phy info
* get link info
* get/set regulatory domain
* get/set mode
* get/set coverage class, RTS threshold, Fragmentation threshold & retry limits
* add/delete interfaces
* enumerate ISM and UNII channels
* block/unblock rfkill devices
* check 'connectivity', disconnect from AP

In utils, several helpers can be found that can be used to:
* enumerate channels and frequencies and convert between the two
* manipulate mac addresses and generate random ones
* fetch and parse the IEEE oui text file
* further rfkill operations to include listing all rfkill devices

At it's heart, PyRIC is a Python port of (a subset of) iw and by extension, a
Python port of Netlink w.r.t nl80211 functionality. The original goal of PyRIC
was to provide a simple interface to the underlying nl80211 kernel support,
handling the complex operations of Netlink seamlessy while maintaining a minimum
of "code walking" to understand, modify and extend. But, why stop there? Since
it's initial inception, PyRIC has grown. PyRIC puts iw, ifconfig, rfkill, udevadm,
airmon-ng and macchanger in your hands (or your program).
"""
