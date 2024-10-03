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

from typing import Dict, Iterable, List, Optional, Set, Tuple, Union, cast

from ._dns import (
    DNSAddress,
    DNSEntry,
    DNSHinfo,
    DNSNsec,
    DNSPointer,
    DNSRecord,
    DNSService,
    DNSText,
)
from ._utils.time import current_time_millis
from .const import _ONE_SECOND, _TYPE_PTR

_UNIQUE_RECORD_TYPES = (DNSAddress, DNSHinfo, DNSPointer, DNSText, DNSService)
_UniqueRecordsType = Union[DNSAddress, DNSHinfo, DNSPointer, DNSText, DNSService]
_DNSRecordCacheType = Dict[str, Dict[DNSRecord, DNSRecord]]
_DNSRecord = DNSRecord
_str = str
_float = float
_int = int


def _remove_key(cache: _DNSRecordCacheType, key: _str, record: _DNSRecord) -> None:
    """Remove a key from a DNSRecord cache

    This function must be run in from event loop.
    """
    record_cache = cache[key]
    del record_cache[record]
    if not record_cache:
        del cache[key]


class DNSCache:
    """A cache of DNS entries."""

    def __init__(self) -> None:
        self.cache: _DNSRecordCacheType = {}
        self.service_cache: _DNSRecordCacheType = {}

    # Functions prefixed with async_ are NOT threadsafe and must
    # be run in the event loop.

    def _async_add(self, record: _DNSRecord) -> bool:
        """Adds an entry.

        Returns true if the entry was not already in the cache.

        This function must be run in from event loop.
        """
        # Previously storage of records was implemented as a list
        # instead a dict. Since DNSRecords are now hashable, the implementation
        # uses a dict to ensure that adding a new record to the cache
        # replaces any existing records that are __eq__ to each other which
        # removes the risk that accessing the cache from the wrong
        # direction would return the old incorrect entry.
        store = self.cache.setdefault(record.key, {})
        new = record not in store and not isinstance(record, DNSNsec)
        store[record] = record
        if isinstance(record, DNSService):
            service_record = record
            self.service_cache.setdefault(record.server_key, {})[service_record] = service_record
        return new

    def async_add_records(self, entries: Iterable[DNSRecord]) -> bool:
        """Add multiple records.

        Returns true if any of the records were not in the cache.

        This function must be run in from event loop.
        """
        new = False
        for entry in entries:
            if self._async_add(entry):
                new = True
        return new

    def _async_remove(self, record: _DNSRecord) -> None:
        """Removes an entry.

        This function must be run in from event loop.
        """
        if isinstance(record, DNSService):
            service_record = record
            _remove_key(self.service_cache, service_record.server_key, service_record)
        _remove_key(self.cache, record.key, record)

    def async_remove_records(self, entries: Iterable[DNSRecord]) -> None:
        """Remove multiple records.

        This function must be run in from event loop.
        """
        for entry in entries:
            self._async_remove(entry)

    def async_expire(self, now: _float) -> List[DNSRecord]:
        """Purge expired entries from the cache.

        This function must be run in from event loop.
        """
        expired = [record for records in self.cache.values() for record in records if record.is_expired(now)]
        self.async_remove_records(expired)
        return expired

    def async_get_unique(self, entry: _UniqueRecordsType) -> Optional[DNSRecord]:
        """Gets a unique entry by key.  Will return None if there is no
        matching entry.

        This function is not threadsafe and must be called from
        the event loop.
        """
        store = self.cache.get(entry.key)
        if store is None:
            return None
        return store.get(entry)

    def async_all_by_details(self, name: _str, type_: _int, class_: _int) -> List[DNSRecord]:
        """Gets all matching entries by details.

        This function is not thread-safe and must be called from
        the event loop.
        """
        key = name.lower()
        records = self.cache.get(key)
        matches: List[DNSRecord] = []
        if records is None:
            return matches
        for record in records:
            if type_ == record.type and class_ == record.class_:
                matches.append(record)
        return matches

    def async_entries_with_name(self, name: str) -> Dict[DNSRecord, DNSRecord]:
        """Returns a dict of entries whose key matches the name.

        This function is not threadsafe and must be called from
        the event loop.
        """
        return self.cache.get(name.lower()) or {}

    def async_entries_with_server(self, name: str) -> Dict[DNSRecord, DNSRecord]:
        """Returns a dict of entries whose key matches the server.

        This function is not threadsafe and must be called from
        the event loop.
        """
        return self.service_cache.get(name.lower()) or {}

    # The below functions are threadsafe and do not need to be run in the
    # event loop, however they all make copies so they significantly
    # inefficent

    def get(self, entry: DNSEntry) -> Optional[DNSRecord]:
        """Gets an entry by key.  Will return None if there is no
        matching entry."""
        if isinstance(entry, _UNIQUE_RECORD_TYPES):
            return self.cache.get(entry.key, {}).get(entry)
        for cached_entry in reversed(list(self.cache.get(entry.key, []))):
            if entry.__eq__(cached_entry):
                return cached_entry
        return None

    def get_by_details(self, name: str, type_: _int, class_: _int) -> Optional[DNSRecord]:
        """Gets the first matching entry by details. Returns None if no entries match.

        Calling this function is not recommended as it will only
        return one record even if there are multiple entries.

        For example if there are multiple A or AAAA addresses this
        function will return the last one that was added to the cache
        which may not be the one you expect.

        Use get_all_by_details instead.
        """
        key = name.lower()
        records = self.cache.get(key)
        if records is None:
            return None
        for cached_entry in reversed(list(records)):
            if type_ == cached_entry.type and class_ == cached_entry.class_:
                return cached_entry
        return None

    def get_all_by_details(self, name: str, type_: _int, class_: _int) -> List[DNSRecord]:
        """Gets all matching entries by details."""
        key = name.lower()
        records = self.cache.get(key)
        if records is None:
            return []
        return [entry for entry in list(records) if type_ == entry.type and class_ == entry.class_]

    def entries_with_server(self, server: str) -> List[DNSRecord]:
        """Returns a list of entries whose server matches the name."""
        return list(self.service_cache.get(server.lower(), []))

    def entries_with_name(self, name: str) -> List[DNSRecord]:
        """Returns a list of entries whose key matches the name."""
        return list(self.cache.get(name.lower(), []))

    def current_entry_with_name_and_alias(self, name: str, alias: str) -> Optional[DNSRecord]:
        now = current_time_millis()
        for record in reversed(self.entries_with_name(name)):
            if (
                record.type == _TYPE_PTR
                and not record.is_expired(now)
                and cast(DNSPointer, record).alias == alias
            ):
                return record
        return None

    def names(self) -> List[str]:
        """Return a copy of the list of current cache names."""
        return list(self.cache)

    def async_mark_unique_records_older_than_1s_to_expire(
        self,
        unique_types: Set[Tuple[_str, _int, _int]],
        answers: Iterable[DNSRecord],
        now: _float,
    ) -> None:
        # rfc6762#section-10.2 para 2
        # Since unique is set, all old records with that name, rrtype,
        # and rrclass that were received more than one second ago are declared
        # invalid, and marked to expire from the cache in one second.
        answers_rrset = set(answers)
        for name, type_, class_ in unique_types:
            for record in self.async_all_by_details(name, type_, class_):
                created_double = record.created
                if (now - created_double > _ONE_SECOND) and record not in answers_rrset:
                    # Expire in 1s
                    record.set_created_ttl(now, 1)
