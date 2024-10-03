"""Multicast DNS Service Discovery for Python, v0.14-wmcbrine
Copyright 2003 Paul Scott-Murphy, 2014 William McBrine

This module provides a framework for the use of DNS Service Discovery
using IP multicast.

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
USA
"""

from typing import Optional

from ._dns import DNSRecord


class RecordUpdate:
    __slots__ = ("new", "old")

    def __init__(self, new: DNSRecord, old: Optional[DNSRecord] = None):
        """RecordUpdate represents a change in a DNS record."""
        self.new = new
        self.old = old

    def __getitem__(self, index: int) -> Optional[DNSRecord]:
        """Get the new or old record."""
        if index == 0:
            return self.new
        elif index == 1:
            return self.old
        raise IndexError(index)
