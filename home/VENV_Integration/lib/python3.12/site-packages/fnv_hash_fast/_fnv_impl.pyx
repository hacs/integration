# distutils: language = c++
from libcpp.string cimport string

import cython


cdef extern from "fnv_wrapper.h":
    cython.uint _cpp_fnv1a_32(string data)

def _fnv1a_32(data: bytes) -> int:
    return _cpp_fnv1a_32(data)
