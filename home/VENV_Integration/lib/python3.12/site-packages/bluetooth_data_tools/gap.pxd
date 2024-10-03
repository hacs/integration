import cython


cdef str BLE_UUID

cdef object from_bytes
cdef object from_bytes_little
cdef object from_bytes_signed

cdef object _cached_uint16_bytes_as_uuid
cdef object _cached_uint32_bytes_as_uuid
cdef object _cached_uint128_bytes_as_uuid
cdef object _cached_parse_advertisement_data
cdef object _cached_parse_advertisement_data_tuple
cdef object _cached_manufacturer_id_bytes_to_int
cdef object _cached_from_bytes_signed

cdef object _LOGGER

cdef class BLEGAPAdvertisement:

    cdef readonly object local_name
    cdef readonly object service_uuids
    cdef readonly object service_data
    cdef readonly object manufacturer_data
    cdef readonly object tx_power

cdef cython.uint TYPE_SHORT_LOCAL_NAME
cdef cython.uint TYPE_COMPLETE_LOCAL_NAME
cdef cython.uint TYPE_MANUFACTURER_SPECIFIC_DATA
cdef cython.uint TYPE_16BIT_SERVICE_UUID_COMPLETE
cdef cython.uint TYPE_16BIT_SERVICE_UUID_MORE_AVAILABLE
cdef cython.uint TYPE_128BIT_SERVICE_UUID_COMPLETE
cdef cython.uint TYPE_128BIT_SERVICE_UUID_MORE_AVAILABLE
cdef cython.uint TYPE_SERVICE_DATA
cdef cython.uint TYPE_SERVICE_DATA_32BIT_UUID
cdef cython.uint TYPE_SERVICE_DATA_128BIT_UUID
cdef cython.uint TYPE_TX_POWER_LEVEL

cpdef parse_advertisement_data(object data)

cpdef parse_advertisement_data_tuple(cython.tuple data)

@cython.locals(
    gap_data=cython.bytes,
    gap_value=cython.bytes,
    gap_type_num="unsigned char",
    total_length=cython.uint,
    length="unsigned char",
    offset=cython.uint,
    start=cython.uint,
    end=cython.uint,
)
cpdef _uncached_parse_advertisement_data(tuple data)
