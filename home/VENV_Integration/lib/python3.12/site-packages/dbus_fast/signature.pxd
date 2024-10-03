"""cdefs for signature.py"""

import cython


cdef class SignatureType:

    cdef public str token
    cdef public list children
    cdef str _signature


cdef class SignatureTree:

    cdef public str signature
    cdef public list types


cdef class Variant:

    cdef public SignatureType type
    cdef public str signature
    cdef public object value

    @cython.locals(signature_tree=SignatureTree)
    cdef _init_variant(self, object signature, object value, bint verify)
