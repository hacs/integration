"""cdefs for unpack.py"""

import cython

from .signature cimport Variant


cpdef unpack_variants(object data)

@cython.locals(
    var=Variant
)
cdef _unpack_variants(object data)
