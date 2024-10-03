"""cdefs for message_reader.py"""

import cython

from .._private.unmarshaller cimport Unmarshaller


cpdef _message_reader(
    Unmarshaller unmarshaller,
    object process,
    object finalize,
    bint negotiate_unix_fd
)
