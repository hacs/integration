#!/usr/bin/env python
""" utils PyRIC utilities

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

 utils 0.0.1
  desc: utilities
  includes: hardware 0.0.5 ouifetch 0.0.2 channels 0.0.1 rfkill 0.0.1
  changes:
   o added mac address related to hardware.py
   o randhw does not force an ouis dict, if not present, randomly generates the
    oui and the ulm

"""

__name__ = 'utils'
__license__ = 'GPLv3'
__version__ = '0.0.1'
__date__ = 'June 2016'
__author__ = 'Dale Patterson'
__maintainer__ = 'Dale Patterson'
__email__ = 'wraith.wireless@yandex.com'
__status__ = 'Production'