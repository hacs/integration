"""cdefs for unmarshaller.py"""

import cython

from ..message cimport Message
from ..signature cimport SignatureTree, SignatureType, Variant


cdef object MAX_UNIX_FDS_SIZE
cdef object ARRAY
cdef object UNIX_FDS_CMSG_LENGTH
cdef object SOL_SOCKET
cdef object SCM_RIGHTS
cdef object MESSAGE_FLAG_INTENUM

cdef unsigned int UINT32_SIZE
cdef unsigned int INT16_SIZE
cdef unsigned int UINT16_SIZE

cdef unsigned int HEADER_ARRAY_OF_STRUCT_SIGNATURE_POSITION
cdef unsigned int HEADER_SIGNATURE_SIZE
cdef unsigned int LITTLE_ENDIAN
cdef unsigned int BIG_ENDIAN
cdef unsigned int PROTOCOL_VERSION
cdef unsigned int HEADER_UNIX_FDS_IDX
cdef cython.list HEADER_IDX_TO_ARG_NAME

cdef str UINT32_CAST
cdef str INT16_CAST
cdef str UINT16_CAST

cdef bint SYS_IS_LITTLE_ENDIAN
cdef bint SYS_IS_BIG_ENDIAN

cdef object UNPACK_HEADER_LITTLE_ENDIAN
cdef object UNPACK_HEADER_BIG_ENDIAN

cdef object UINT32_UNPACK_LITTLE_ENDIAN
cdef object UINT32_UNPACK_BIG_ENDIAN

cdef object INT16_UNPACK_LITTLE_ENDIAN
cdef object INT16_UNPACK_BIG_ENDIAN

cdef object UINT16_UNPACK_LITTLE_ENDIAN
cdef object UINT16_UNPACK_BIG_ENDIAN

cdef cython.dict MESSAGE_TYPE_MAP
cdef cython.dict MESSAGE_FLAG_MAP
cdef dict HEADER_MESSAGE_ARG_NAME

cdef SignatureTree SIGNATURE_TREE_EMPTY
cdef SignatureTree SIGNATURE_TREE_B
cdef SignatureTree SIGNATURE_TREE_N
cdef SignatureTree SIGNATURE_TREE_O
cdef SignatureTree SIGNATURE_TREE_S
cdef SignatureTree SIGNATURE_TREE_U
cdef SignatureTree SIGNATURE_TREE_Y

cdef SignatureTree SIGNATURE_TREE_AS
cdef SignatureType SIGNATURE_TREE_AS_TYPES_0
cdef SignatureTree SIGNATURE_TREE_AO
cdef SignatureType SIGNATURE_TREE_AO_TYPES_0
cdef SignatureTree SIGNATURE_TREE_A_SV
cdef SignatureType SIGNATURE_TREE_A_SV_TYPES_0
cdef SignatureTree SIGNATURE_TREE_SA_SV_AS
cdef SignatureType SIGNATURE_TREE_SA_SV_AS_TYPES_1
cdef SignatureType SIGNATURE_TREE_SA_SV_AS_TYPES_2
cdef SignatureTree SIGNATURE_TREE_OAS
cdef SignatureType SIGNATURE_TREE_OAS_TYPES_1
cdef SignatureTree SIGNATURE_TREE_OA_SA_SV
cdef SignatureType SIGNATURE_TREE_OA_SA_SV_TYPES_1
cdef SignatureTree SIGNATURE_TREE_AY
cdef SignatureType SIGNATURE_TREE_AY_TYPES_0
cdef SignatureTree SIGNATURE_TREE_A_QV
cdef SignatureType SIGNATURE_TREE_A_QV_TYPES_0
cdef SignatureTree SIGNATURE_TREE_A_OA_SA_SV
cdef SignatureType SIGNATURE_TREE_A_OA_SA_SV_TYPES_0

cdef unsigned int TOKEN_B_AS_INT
cdef unsigned int TOKEN_U_AS_INT
cdef unsigned int TOKEN_Y_AS_INT
cdef unsigned int TOKEN_A_AS_INT
cdef unsigned int TOKEN_O_AS_INT
cdef unsigned int TOKEN_S_AS_INT
cdef unsigned int TOKEN_G_AS_INT
cdef unsigned int TOKEN_N_AS_INT
cdef unsigned int TOKEN_X_AS_INT
cdef unsigned int TOKEN_T_AS_INT
cdef unsigned int TOKEN_D_AS_INT
cdef unsigned int TOKEN_Q_AS_INT
cdef unsigned int TOKEN_V_AS_INT
cdef unsigned int TOKEN_LEFT_CURLY_AS_INT
cdef unsigned int TOKEN_LEFT_PAREN_AS_INT

cdef object MARSHALL_STREAM_END_ERROR
cdef object DEFAULT_BUFFER_SIZE

cdef cython.uint EAGAIN
cdef cython.uint EWOULDBLOCK

cdef get_signature_tree


cdef inline unsigned long _cast_uint32_native(const char * payload, unsigned int offset):
    cdef unsigned long *u32p = <unsigned long *> &payload[offset]
    return u32p[0]

cdef inline short _cast_int16_native(const char *  payload, unsigned int offset):
    cdef short *s16p = <short *> &payload[offset]
    return s16p[0]

cdef inline unsigned short _cast_uint16_native(const char *  payload, unsigned int offset):
    cdef unsigned short *u16p = <unsigned short *> &payload[offset]
    return u16p[0]



cdef class Unmarshaller:

    cdef object _unix_fds
    cdef bytearray _buf
    cdef unsigned int _pos
    cdef object _stream
    cdef object _sock
    cdef object _message
    cdef object _readers
    cdef unsigned int _body_len
    cdef unsigned int _serial
    cdef unsigned int _header_len
    cdef object _message_type
    cdef object _flag
    cdef unsigned int _msg_len
    cdef unsigned int _is_native
    cdef object _uint32_unpack
    cdef object _int16_unpack
    cdef object _uint16_unpack
    cdef object _stream_reader
    cdef object _sock_reader
    cdef bint _negotiate_unix_fd
    cdef bint _read_complete
    cdef unsigned int _endian

    cdef _next_message(self)

    cdef bint _has_another_message_in_buffer(self)

    @cython.locals(
        msg=cython.bytes,
        recv=cython.tuple,
        errno=cython.uint
    )
    cdef void _read_sock_with_fds(self, unsigned int pos, unsigned int missing_bytes)

    @cython.locals(
        data=cython.bytes,
        errno=cython.uint
    )
    cdef void _read_sock_without_fds(self, unsigned int pos)

    @cython.locals(
        data=cython.bytes
    )
    cdef void _read_stream(self, unsigned int pos, unsigned int missing_bytes)

    cdef void _read_to_pos(self, unsigned int pos)

    cpdef read_boolean(self, SignatureType type_)

    cdef _read_boolean(self)

    cpdef read_uint32_unpack(self, SignatureType type_)

    cdef unsigned int _read_uint32_unpack(self)

    cpdef read_int16_unpack(self, SignatureType type_)

    cdef int _read_int16_unpack(self)

    cpdef read_uint16_unpack(self, SignatureType type_)

    cdef unsigned int _read_uint16_unpack(self)

    cpdef read_string_unpack(self, SignatureType type_)

    @cython.locals(
        str_start=cython.uint,
    )
    cdef str _read_string_unpack(self)

    @cython.locals(
        tree=SignatureTree,
        token_as_int=cython.uint,
    )
    cdef Variant _read_variant(self)

    @cython.locals(
        beginning_pos=cython.ulong,
        array_length=cython.uint,
        children=cython.list,
        child_type=SignatureType,
        child_0=SignatureType,
        child_1=SignatureType,
        token_as_int=cython.uint,
    )
    cpdef object read_array(self, SignatureType type_)

    cpdef read_signature(self, SignatureType type_)

    @cython.locals(
        o=cython.ulong,
        signature_len=cython.uint,
    )
    cdef str _read_signature(self)

    @cython.locals(
        endian=cython.uint,
        buffer=cython.bytearray,
        protocol_version=cython.uint,
        key=cython.str,
    )
    cdef _read_header(self)

    @cython.locals(
        body=cython.list,
        header_fields=cython.dict,
        token_as_int=cython.uint,
        signature=cython.str,
    )
    cdef _read_body(self)

    cdef _unmarshall(self)

    cpdef unmarshall(self)

    @cython.locals(
        beginning_pos=cython.ulong,
        o=cython.ulong,
        token_as_int=cython.uint,
        signature_len=cython.uint,
    )
    cdef cython.dict _header_fields(self, unsigned int header_length)
