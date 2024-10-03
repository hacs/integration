"""cdefs for message.py"""

import cython

from ._private.marshaller cimport Marshaller
from .signature cimport Variant


cdef object ErrorType
cdef object SignatureTree
cdef object SignatureType
cdef object MessageType


cdef object HEADER_PATH
cdef object HEADER_INTERFACE
cdef object HEADER_MEMBER
cdef object HEADER_ERROR_NAME
cdef object HEADER_REPLY_SERIAL
cdef object HEADER_DESTINATION
cdef object HEADER_SENDER
cdef object HEADER_SIGNATURE
cdef object HEADER_UNIX_FDS


cdef object LITTLE_ENDIAN
cdef object PROTOCOL_VERSION

cdef object MESSAGE_FLAG
cdef object MESSAGE_FLAG_NONE
cdef object MESSAGE_TYPE_METHOD_CALL

cdef get_signature_tree

cdef class Message:

    cdef public object destination
    cdef public object path
    cdef public object interface
    cdef public object member
    cdef public object message_type
    cdef public object flags
    cdef public object error_name
    cdef public object reply_serial
    cdef public object sender
    cdef public cython.list unix_fds
    cdef public object signature
    cdef public object signature_tree
    cdef public object body
    cdef public object serial

    @cython.locals(
        body_buffer=cython.bytearray,
        header_buffer=cython.bytearray
    )
    cpdef _marshall(self, object negotiate_unix_fd)
