"""cdefs for address.py"""

import cython


cdef object unquote

@cython.locals(kv=cython.str, opt_string=cython.str, address=cython.str)
cpdef parse_address(cython.str address_str)

cpdef get_bus_address(object bus_type)

cpdef get_session_bus_address()

cpdef get_system_bus_address()
