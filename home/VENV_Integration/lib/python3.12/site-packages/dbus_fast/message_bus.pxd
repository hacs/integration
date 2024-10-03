import cython

from ._private.address cimport get_bus_address, parse_address
from .message cimport Message
from .service cimport ServiceInterface, _Method


cdef object MessageType
cdef object DBusError
cdef object MessageFlag

cdef object MESSAGE_TYPE_CALL
cdef object MESSAGE_TYPE_SIGNAL
cdef cython.uint NO_REPLY_EXPECTED_VALUE
cdef object NONE
cdef object NO_REPLY_EXPECTED

cdef object BLOCK_UNEXPECTED_REPLY
cdef object assert_object_path_valid
cdef object assert_bus_name_valid

@cython.locals(flag_value=cython.uint)
cdef bint _expects_reply(Message msg)


cdef class BaseMessageBus:

    cdef public object unique_name
    cdef public bint _disconnected
    cdef public object _user_disconnect
    cdef public cython.dict _method_return_handlers
    cdef public object _serial
    cdef public cython.dict _path_exports
    cdef public cython.list _user_message_handlers
    cdef public cython.dict _name_owners
    cdef public object _bus_address
    cdef public object _name_owner_match_rule
    cdef public cython.dict _match_rules
    cdef public object _high_level_client_initialized
    cdef public object _ProxyObject
    cdef public object _machine_id
    cdef public object _negotiate_unix_fd
    cdef public object _sock
    cdef public object _stream
    cdef public object _fd

    cpdef _process_message(self, Message msg)

    @cython.locals(
        methods=cython.list,
        method=_Method,
        interface=ServiceInterface,
        interfaces=cython.list,
    )
    cdef _find_message_handler(self, Message msg)

    cdef _setup_socket(self)

    @cython.locals(no_reply_expected=bint)
    cpdef _call(self, Message msg, object callback)

    cpdef next_serial(self)

    cpdef void _callback_method_handler(
        self,
        ServiceInterface interface,
        _Method method,
        Message msg,
        object send_reply
    )
