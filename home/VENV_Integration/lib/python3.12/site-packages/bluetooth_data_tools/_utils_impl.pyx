# cython: language_level=3, c_string_type=str, c_string_encoding=ascii

from libc.stdint cimport uint64_t

cdef extern from "utils_wrapper.h":
    void _uint64_to_bdaddr(uint64_t address, char bdaddr[17]) nogil


def _int_to_bluetooth_address(addr: int) -> str:
    cdef char bdaddr[17]
    _uint64_to_bdaddr(<uint64_t>addr, bdaddr)
    return <str>bdaddr[:17]
