cimport libav as lib

from av.bitstream.filter cimport BitStreamFilter


cdef class BitStreamFilterContext(object):

    cdef lib.AVBSFContext *ptr
    cdef readonly BitStreamFilter filter
