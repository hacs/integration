cimport libav as lib


cdef class BitStreamFilter(object):

    cdef lib.AVBitStreamFilter *ptr


cdef BitStreamFilter wrap_filter(const lib.AVBitStreamFilter *ptr)
