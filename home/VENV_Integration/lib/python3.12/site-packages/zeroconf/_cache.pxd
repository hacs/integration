import cython

from ._dns cimport (
    DNSAddress,
    DNSEntry,
    DNSHinfo,
    DNSNsec,
    DNSPointer,
    DNSRecord,
    DNSService,
    DNSText,
)


cdef object _UNIQUE_RECORD_TYPES
cdef unsigned int _TYPE_PTR
cdef cython.uint _ONE_SECOND

@cython.locals(
    record_cache=dict,
)
cdef _remove_key(cython.dict cache, object key, DNSRecord record)


cdef class DNSCache:

    cdef public cython.dict cache
    cdef public cython.dict service_cache

    cpdef bint async_add_records(self, object entries)

    cpdef void async_remove_records(self, object entries)

    @cython.locals(
        store=cython.dict,
    )
    cpdef DNSRecord async_get_unique(self, DNSRecord entry)

    @cython.locals(
        record=DNSRecord,
    )
    cpdef list async_expire(self, double now)

    @cython.locals(
        records=cython.dict,
        record=DNSRecord,
    )
    cpdef list async_all_by_details(self, str name, unsigned int type_, unsigned int class_)

    cpdef cython.dict async_entries_with_name(self, str name)

    cpdef cython.dict async_entries_with_server(self, str name)

    @cython.locals(
        cached_entry=DNSRecord,
    )
    cpdef DNSRecord get_by_details(self, str name, unsigned int type_, unsigned int class_)

    @cython.locals(
        records=cython.dict,
        entry=DNSRecord,
    )
    cpdef cython.list get_all_by_details(self, str name, unsigned int type_, unsigned int class_)

    @cython.locals(
        store=cython.dict,
        service_record=DNSService
    )
    cdef bint _async_add(self, DNSRecord record)

    @cython.locals(
        service_record=DNSService
    )
    cdef void _async_remove(self, DNSRecord record)

    @cython.locals(
        record=DNSRecord,
        created_double=double,
    )
    cpdef void async_mark_unique_records_older_than_1s_to_expire(self, cython.set unique_types, object answers, double now)

    cpdef entries_with_name(self, str name)

    @cython.locals(
        record=DNSRecord,
        now=double
    )
    cpdef current_entry_with_name_and_alias(self, str name, str alias)
