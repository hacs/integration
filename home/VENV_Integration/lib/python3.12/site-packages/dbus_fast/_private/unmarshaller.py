import array
import errno
import io
import socket
import sys
from struct import Struct
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from ..constants import MESSAGE_FLAG_MAP, MESSAGE_TYPE_MAP, MessageFlag
from ..errors import InvalidMessageError
from ..message import Message
from ..signature import SignatureType, Variant, get_signature_tree
from .constants import BIG_ENDIAN, LITTLE_ENDIAN, PROTOCOL_VERSION

MESSAGE_FLAG_INTENUM = MessageFlag

MAX_UNIX_FDS = 16
MAX_UNIX_FDS_SIZE = array.array("i").itemsize
UNIX_FDS_CMSG_LENGTH = socket.CMSG_LEN(MAX_UNIX_FDS_SIZE)

UNPACK_SYMBOL = {LITTLE_ENDIAN: "<", BIG_ENDIAN: ">"}

UINT32_CAST = "I"
UINT32_SIZE = 4
UINT32_DBUS_TYPE = "u"

INT16_CAST = "h"
INT16_SIZE = 2
INT16_DBUS_TYPE = "n"

UINT16_CAST = "H"
UINT16_SIZE = 2
UINT16_DBUS_TYPE = "q"

SYS_IS_LITTLE_ENDIAN = sys.byteorder == "little"
SYS_IS_BIG_ENDIAN = sys.byteorder == "big"

DBUS_TO_CTYPE = {
    "y": ("B", 1),  # byte
    INT16_DBUS_TYPE: (INT16_CAST, INT16_SIZE),  # int16
    UINT16_DBUS_TYPE: (UINT16_CAST, UINT16_SIZE),  # uint16
    "i": ("i", 4),  # int32
    UINT32_DBUS_TYPE: (UINT32_CAST, UINT32_SIZE),  # uint32
    "x": ("q", 8),  # int64
    "t": ("Q", 8),  # uint64
    "d": ("d", 8),  # double
    "h": (UINT32_CAST, UINT32_SIZE),  # uint32
}

UNPACK_HEADER_LITTLE_ENDIAN = Struct("<III").unpack_from
UNPACK_HEADER_BIG_ENDIAN = Struct(">III").unpack_from

UINT32_UNPACK_LITTLE_ENDIAN = Struct(f"<{UINT32_CAST}").unpack_from
UINT32_UNPACK_BIG_ENDIAN = Struct(f">{UINT32_CAST}").unpack_from

INT16_UNPACK_LITTLE_ENDIAN = Struct(f"<{INT16_CAST}").unpack_from
INT16_UNPACK_BIG_ENDIAN = Struct(f">{INT16_CAST}").unpack_from

UINT16_UNPACK_LITTLE_ENDIAN = Struct(f"<{UINT16_CAST}").unpack_from
UINT16_UNPACK_BIG_ENDIAN = Struct(f">{UINT16_CAST}").unpack_from

HEADER_SIGNATURE_SIZE = 16
HEADER_ARRAY_OF_STRUCT_SIGNATURE_POSITION = 12


SIGNATURE_TREE_EMPTY = get_signature_tree("")
SIGNATURE_TREE_B = get_signature_tree("b")
SIGNATURE_TREE_N = get_signature_tree("n")
SIGNATURE_TREE_S = get_signature_tree("s")
SIGNATURE_TREE_O = get_signature_tree("o")
SIGNATURE_TREE_U = get_signature_tree("u")
SIGNATURE_TREE_Y = get_signature_tree("y")

SIGNATURE_TREE_AY = get_signature_tree("ay")
SIGNATURE_TREE_AS = get_signature_tree("as")
SIGNATURE_TREE_AS_TYPES_0 = SIGNATURE_TREE_AS.types[0]
SIGNATURE_TREE_A_SV = get_signature_tree("a{sv}")
SIGNATURE_TREE_A_SV_TYPES_0 = SIGNATURE_TREE_A_SV.types[0]

SIGNATURE_TREE_AO = get_signature_tree("ao")
SIGNATURE_TREE_AO_TYPES_0 = SIGNATURE_TREE_AO.types[0]

SIGNATURE_TREE_OAS = get_signature_tree("oas")
SIGNATURE_TREE_OAS_TYPES_1 = SIGNATURE_TREE_OAS.types[1]

SIGNATURE_TREE_AY_TYPES_0 = SIGNATURE_TREE_AY.types[0]
SIGNATURE_TREE_A_QV = get_signature_tree("a{qv}")
SIGNATURE_TREE_A_QV_TYPES_0 = SIGNATURE_TREE_A_QV.types[0]

SIGNATURE_TREE_SA_SV_AS = get_signature_tree("sa{sv}as")
SIGNATURE_TREE_SA_SV_AS_TYPES_1 = SIGNATURE_TREE_SA_SV_AS.types[1]
SIGNATURE_TREE_SA_SV_AS_TYPES_2 = SIGNATURE_TREE_SA_SV_AS.types[2]

SIGNATURE_TREE_OA_SA_SV = get_signature_tree("oa{sa{sv}}")
SIGNATURE_TREE_OA_SA_SV_TYPES_1 = SIGNATURE_TREE_OA_SA_SV.types[1]

SIGNATURE_TREE_A_OA_SA_SV = get_signature_tree("a{oa{sa{sv}}}")
SIGNATURE_TREE_A_OA_SA_SV_TYPES_0 = SIGNATURE_TREE_A_OA_SA_SV.types[0]

TOKEN_B_AS_INT = ord("b")
TOKEN_U_AS_INT = ord("u")
TOKEN_Y_AS_INT = ord("y")
TOKEN_A_AS_INT = ord("a")
TOKEN_O_AS_INT = ord("o")
TOKEN_S_AS_INT = ord("s")
TOKEN_G_AS_INT = ord("g")
TOKEN_N_AS_INT = ord("n")
TOKEN_X_AS_INT = ord("x")
TOKEN_T_AS_INT = ord("t")
TOKEN_D_AS_INT = ord("d")
TOKEN_Q_AS_INT = ord("q")
TOKEN_V_AS_INT = ord("v")
TOKEN_LEFT_CURLY_AS_INT = ord("{")
TOKEN_LEFT_PAREN_AS_INT = ord("(")


ARRAY = array.array
SOL_SOCKET = socket.SOL_SOCKET
SCM_RIGHTS = socket.SCM_RIGHTS

EAGAIN = errno.EAGAIN
EWOULDBLOCK = errno.EWOULDBLOCK

HEADER_IDX_TO_ARG_NAME = [
    "",
    "path",
    "interface",
    "member",
    "error_name",
    "reply_serial",
    "destination",
    "sender",
    "signature",
    "unix_fds",
]
HEADER_UNIX_FDS_IDX = HEADER_IDX_TO_ARG_NAME.index("unix_fds")

_SignatureType = SignatureType
_int = int

READER_TYPE = Callable[["Unmarshaller", SignatureType], Any]

MARSHALL_STREAM_END_ERROR = BlockingIOError

DEFAULT_BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE


def unpack_parser_factory(unpack_from: Callable, size: int) -> READER_TYPE:
    """Build a parser that unpacks the bytes using the given unpack_from function."""

    def _unpack_from_parser(self: "Unmarshaller", signature: SignatureType) -> Any:
        self._pos += size + (-self._pos & (size - 1))  # align
        return unpack_from(self._buf, self._pos - size)[0]

    return _unpack_from_parser


def build_simple_parsers(
    endian: int,
) -> Dict[str, Callable[["Unmarshaller", SignatureType], Any]]:
    """Build a dict of parsers for simple types."""
    parsers: Dict[str, READER_TYPE] = {}
    for dbus_type, ctype_size in DBUS_TO_CTYPE.items():
        ctype, size = ctype_size
        size = ctype_size[1]
        parsers[dbus_type] = unpack_parser_factory(
            Struct(f"{UNPACK_SYMBOL[endian]}{ctype}").unpack_from, size
        )
    return parsers


try:
    import cython
except ImportError:
    from ._cython_compat import FAKE_CYTHON as cython


#
# Alignment padding is handled with the following formula below
#
# For any align value, the correct padding formula is:
#
#    (align - (pos % align)) % align
#
# However, if align is a power of 2 (always the case here), the slow MOD
# operator can be replaced by a bitwise AND:
#
#    (align - (pos & (align - 1))) & (align - 1)
#
# Which can be simplified to:
#
#    (-pos) & (align - 1)
#
#
class Unmarshaller:
    """Unmarshall messages from a stream.

    When calling with sock and _negotiate_unix_fd False, the unmashaller must
    be called continuously for each new message as it will buffer the data
    until a complete message is available.
    """

    __slots__ = (
        "_unix_fds",
        "_buf",
        "_pos",
        "_stream",
        "_sock",
        "_message",
        "_readers",
        "_body_len",
        "_serial",
        "_header_len",
        "_message_type",
        "_flag",
        "_msg_len",
        "_uint32_unpack",
        "_int16_unpack",
        "_uint16_unpack",
        "_is_native",
        "_stream_reader",
        "_sock_reader",
        "_negotiate_unix_fd",
        "_read_complete",
        "_endian",
    )

    def __init__(
        self,
        stream: Optional[io.BufferedRWPair] = None,
        sock: Optional[socket.socket] = None,
        negotiate_unix_fd: bool = True,
    ) -> None:
        self._unix_fds: List[int] = []
        self._buf = bytearray()  # Actual buffer
        self._stream = stream
        self._sock = sock
        self._message: Optional[Message] = None
        self._readers: Dict[str, READER_TYPE] = {}
        self._pos = 0
        self._body_len = 0
        self._serial = 0
        self._header_len = 0
        self._message_type = 0
        self._flag = 0
        self._msg_len = 0
        self._is_native = 0
        self._uint32_unpack: Optional[Callable] = None
        self._int16_unpack: Optional[Callable] = None
        self._uint16_unpack: Optional[Callable] = None
        self._stream_reader: Optional[Callable] = None
        self._negotiate_unix_fd = negotiate_unix_fd
        self._read_complete = False
        if stream:
            if isinstance(stream, io.BufferedRWPair) and hasattr(stream, "reader"):
                self._stream_reader = stream.reader.read  # type: ignore[attr-defined]
            self._stream_reader = stream.read
        elif self._negotiate_unix_fd:
            self._sock_reader = self._sock.recvmsg
        else:
            self._sock_reader = self._sock.recv
        self._endian = 0

    def _next_message(self) -> None:
        """Reset the unmarshaller to its initial state.

        Call this before processing a new message.
        """
        self._unix_fds = []
        to_clear = HEADER_SIGNATURE_SIZE + self._msg_len
        if len(self._buf) == to_clear:
            self._buf = bytearray()
        else:
            del self._buf[:to_clear]
        self._msg_len = 0  # used to check if we have ready the header
        self._read_complete = False  # used to check if we have ready the message
        # No need to reset the unpack functions, they are set in _read_header
        # every time a new message is processed.

    @property
    def message(self) -> Optional[Message]:
        """Return the message that has been unmarshalled."""
        if self._read_complete:
            return self._message
        return None

    def _has_another_message_in_buffer(self) -> bool:
        """Check if there is another message in the buffer."""
        return len(self._buf) > HEADER_SIGNATURE_SIZE + self._msg_len

    def _read_sock_with_fds(self, pos: _int, missing_bytes: _int) -> None:
        """reads from the socket, storing any fds sent and handling errors
        from the read itself.

        This function is greedy and will read as much data as possible
        from the underlying socket.
        """
        # This will raise BlockingIOError if there is no data to read
        # which we store in the MARSHALL_STREAM_END_ERROR object
        try:
            recv = self._sock_reader(missing_bytes, UNIX_FDS_CMSG_LENGTH)  # type: ignore[union-attr]
        except OSError as e:
            errno = e.errno
            if errno == EAGAIN or errno == EWOULDBLOCK:
                raise MARSHALL_STREAM_END_ERROR
            raise
        msg = recv[0]
        ancdata = recv[1]
        if ancdata:
            for level, type_, data in ancdata:
                if not (level == SOL_SOCKET and type_ == SCM_RIGHTS):
                    continue
                self._unix_fds.extend(
                    ARRAY("i", data[: len(data) - (len(data) % MAX_UNIX_FDS_SIZE)])
                )
        if not msg:
            raise EOFError()
        self._buf += msg
        if len(self._buf) < pos:
            raise MARSHALL_STREAM_END_ERROR

    def _read_sock_without_fds(self, pos: _int) -> None:
        """reads from the socket and handling errors from the read itself.

        This function is greedy and will read as much data as possible
        from the underlying socket.
        """
        # This will raise BlockingIOError if there is no data to read
        # which we store in the MARSHALL_STREAM_END_ERROR object
        while True:
            try:
                data = self._sock_reader(DEFAULT_BUFFER_SIZE)  # type: ignore[union-attr]
            except OSError as e:
                errno = e.errno
                if errno == EAGAIN or errno == EWOULDBLOCK:
                    raise MARSHALL_STREAM_END_ERROR
                raise
            if not data:
                raise EOFError()
            self._buf += data
            if len(self._buf) >= pos:
                return

    def _read_stream(self, pos: _int, missing_bytes: _int) -> bytes:
        """Read from the stream."""
        data = self._stream_reader(missing_bytes)  # type: ignore[misc]
        if data is None:
            raise MARSHALL_STREAM_END_ERROR
        if not data:
            raise EOFError()
        self._buf += data
        if len(self._buf) < pos:
            raise MARSHALL_STREAM_END_ERROR

    def _read_to_pos(self, pos: _int) -> None:
        """
        Read from underlying socket into buffer.

        Raises BlockingIOError if there is not enough data to be read.

        :arg pos:
            The pos to read to. If not enough bytes are available in the
            buffer, read more from it.

        :returns:
            None
        """
        missing_bytes = pos - len(self._buf)
        if missing_bytes <= 0:
            return
        if self._sock is None:
            self._read_stream(pos, missing_bytes)
        elif self._negotiate_unix_fd:
            self._read_sock_with_fds(pos, missing_bytes)
        else:
            self._read_sock_without_fds(pos)

    def read_uint32_unpack(self, type_: _SignatureType) -> int:
        return self._read_uint32_unpack()

    def _read_uint32_unpack(self) -> int:
        self._pos += UINT32_SIZE + (-self._pos & (UINT32_SIZE - 1))  # align
        if self._is_native and cython.compiled:
            return _cast_uint32_native(  # type: ignore[name-defined] # pragma: no cover
                self._buf, self._pos - UINT32_SIZE
            )
        return self._uint32_unpack(self._buf, self._pos - UINT32_SIZE)[0]  # type: ignore[misc]

    def read_uint16_unpack(self, type_: _SignatureType) -> int:
        return self._read_uint16_unpack()

    def _read_uint16_unpack(self) -> int:
        self._pos += UINT16_SIZE + (-self._pos & (UINT16_SIZE - 1))  # align
        if self._is_native and cython.compiled:
            return _cast_uint16_native(  # type: ignore[name-defined] # pragma: no cover
                self._buf, self._pos - UINT16_SIZE
            )
        return self._uint16_unpack(self._buf, self._pos - UINT16_SIZE)[0]  # type: ignore[misc]

    def read_int16_unpack(self, type_: _SignatureType) -> int:
        return self._read_int16_unpack()

    def _read_int16_unpack(self) -> int:
        self._pos += INT16_SIZE + (-self._pos & (INT16_SIZE - 1))  # align
        if self._is_native and cython.compiled:
            return _cast_int16_native(  # type: ignore[name-defined] # pragma: no cover
                self._buf, self._pos - INT16_SIZE
            )
        return self._int16_unpack(self._buf, self._pos - INT16_SIZE)[0]  # type: ignore[misc]

    def read_boolean(self, type_: _SignatureType) -> bool:
        return self._read_boolean()

    def _read_boolean(self) -> bool:
        return bool(self._read_uint32_unpack())

    def read_string_unpack(self, type_: _SignatureType) -> str:
        return self._read_string_unpack()

    def _read_string_unpack(self) -> str:
        """Read a string using unpack."""
        self._pos += UINT32_SIZE + (-self._pos & (UINT32_SIZE - 1))  # align
        str_start = self._pos
        # read terminating '\0' byte as well (str_length + 1)
        if self._is_native and cython.compiled:
            self._pos += (  # pragma: no cover
                _cast_uint32_native(self._buf, str_start - UINT32_SIZE) + 1  # type: ignore[name-defined]
            )
        else:
            self._pos += self._uint32_unpack(self._buf, str_start - UINT32_SIZE)[0] + 1  # type: ignore[misc]
        return self._buf[str_start : self._pos - 1].decode()

    def read_signature(self, type_: _SignatureType) -> str:
        return self._read_signature()

    def _read_signature(self) -> str:
        signature_len = self._buf[self._pos]  # byte
        o = self._pos + 1
        # read terminating '\0' byte as well (str_length + 1)
        self._pos = o + signature_len + 1
        return self._buf[o : o + signature_len].decode()

    def read_variant(self, type_: _SignatureType) -> Variant:
        return self._read_variant()

    def _read_variant(self) -> Variant:
        signature = self._read_signature()
        token_as_int = ord(signature[0])
        # verify in Variant is only useful on construction not unmarshalling
        if len(signature) == 1:
            if token_as_int == TOKEN_N_AS_INT:
                return Variant(SIGNATURE_TREE_N, self._read_int16_unpack(), False)
            if token_as_int == TOKEN_S_AS_INT:
                return Variant(SIGNATURE_TREE_S, self._read_string_unpack(), False)
            if token_as_int == TOKEN_B_AS_INT:
                return Variant(SIGNATURE_TREE_B, self._read_boolean(), False)
            if token_as_int == TOKEN_O_AS_INT:
                return Variant(SIGNATURE_TREE_O, self._read_string_unpack(), False)
            if token_as_int == TOKEN_U_AS_INT:
                return Variant(SIGNATURE_TREE_U, self._read_uint32_unpack(), False)
            if token_as_int == TOKEN_Y_AS_INT:
                self._pos += 1
                return Variant(SIGNATURE_TREE_Y, self._buf[self._pos - 1], False)
        elif token_as_int == TOKEN_A_AS_INT:
            if signature == "ay":
                return Variant(
                    SIGNATURE_TREE_AY, self.read_array(SIGNATURE_TREE_AY_TYPES_0), False
                )
            if signature == "a{qv}":
                return Variant(
                    SIGNATURE_TREE_A_QV,
                    self.read_array(SIGNATURE_TREE_A_QV_TYPES_0),
                    False,
                )
            if signature == "as":
                return Variant(
                    SIGNATURE_TREE_AS, self.read_array(SIGNATURE_TREE_AS_TYPES_0), False
                )
            if signature == "a{sv}":
                return Variant(
                    SIGNATURE_TREE_A_SV,
                    self.read_array(SIGNATURE_TREE_A_SV_TYPES_0),
                    False,
                )
            if signature == "ao":
                return Variant(
                    SIGNATURE_TREE_AO, self.read_array(SIGNATURE_TREE_AO_TYPES_0), False
                )
        tree = get_signature_tree(signature)
        signature_type = tree.types[0]
        return Variant(
            tree,
            self._readers[signature_type.token](self, signature_type),
            False,
        )

    def read_struct(self, type_: _SignatureType) -> List[Any]:
        self._pos += -self._pos & 7  # align 8
        readers = self._readers
        return [
            readers[child_type.token](self, child_type) for child_type in type_.children
        ]

    def read_dict_entry(self, type_: _SignatureType) -> Tuple[Any, Any]:
        self._pos += -self._pos & 7  # align 8
        return self._readers[type_.children[0].token](
            self, type_.children[0]
        ), self._readers[type_.children[1].token](self, type_.children[1])

    def read_array(self, type_: _SignatureType) -> Iterable[Any]:
        self._pos += -self._pos & 3  # align 4 for the array
        self._pos += (
            -self._pos & (UINT32_SIZE - 1)
        ) + UINT32_SIZE  # align for the uint32
        if self._is_native and cython.compiled:
            array_length = _cast_uint32_native(  # type: ignore[name-defined] # pragma: no cover
                self._buf, self._pos - UINT32_SIZE
            )
        else:
            array_length = self._uint32_unpack(self._buf, self._pos - UINT32_SIZE)[0]  # type: ignore[misc]

        child_type: SignatureType = type_.children[0]
        token_as_int = ord(child_type.token[0])

        if (
            token_as_int == TOKEN_X_AS_INT
            or token_as_int == TOKEN_T_AS_INT
            or token_as_int == TOKEN_D_AS_INT
            or token_as_int == TOKEN_LEFT_CURLY_AS_INT
            or token_as_int == TOKEN_LEFT_PAREN_AS_INT
        ):
            # the first alignment is not included in the array size
            self._pos += -self._pos & 7  # align 8

        if token_as_int == TOKEN_Y_AS_INT:
            self._pos += array_length
            return self._buf[self._pos - array_length : self._pos]

        if token_as_int == TOKEN_LEFT_CURLY_AS_INT:
            result_dict: Dict[Any, Any] = {}
            beginning_pos = self._pos
            children = child_type.children
            child_0 = children[0]
            child_1 = children[1]
            child_0_token_as_int = ord(child_0.token[0])
            child_1_token_as_int = ord(child_1.token[0])
            # Strings with variant values are the most common case
            # so we optimize for that by inlining the string reading
            # and the variant reading here
            if (
                child_0_token_as_int == TOKEN_O_AS_INT
                or child_0_token_as_int == TOKEN_S_AS_INT
            ) and child_1_token_as_int == TOKEN_V_AS_INT:
                while self._pos - beginning_pos < array_length:
                    self._pos += -self._pos & 7  # align 8
                    key: Union[str, int] = self._read_string_unpack()
                    result_dict[key] = self._read_variant()
            elif (
                child_0_token_as_int == TOKEN_Q_AS_INT
                and child_1_token_as_int == TOKEN_V_AS_INT
            ):
                while self._pos - beginning_pos < array_length:
                    self._pos += -self._pos & 7  # align 8
                    key = self._read_uint16_unpack()
                    result_dict[key] = self._read_variant()
            if (
                child_0_token_as_int == TOKEN_O_AS_INT
                or child_0_token_as_int == TOKEN_S_AS_INT
            ) and child_1_token_as_int == TOKEN_A_AS_INT:
                while self._pos - beginning_pos < array_length:
                    self._pos += -self._pos & 7  # align 8
                    key = self._read_string_unpack()
                    result_dict[key] = self.read_array(child_1)
            else:
                reader_1 = self._readers[child_1.token]
                reader_0 = self._readers[child_0.token]
                while self._pos - beginning_pos < array_length:
                    self._pos += -self._pos & 7  # align 8
                    key = reader_0(self, child_0)
                    result_dict[key] = reader_1(self, child_1)

            return result_dict

        if array_length == 0:
            return []

        result_list = []
        beginning_pos = self._pos
        if token_as_int == TOKEN_O_AS_INT or token_as_int == TOKEN_S_AS_INT:
            while self._pos - beginning_pos < array_length:
                result_list.append(self._read_string_unpack())
            return result_list
        reader = self._readers[child_type.token]
        while self._pos - beginning_pos < array_length:
            result_list.append(reader(self, child_type))
        return result_list

    def _header_fields(self, header_length: _int) -> Dict[str, Any]:
        """Header fields are always a(yv)."""
        beginning_pos = self._pos
        headers = {}
        buf = self._buf
        readers = self._readers
        while self._pos - beginning_pos < header_length:
            # Now read the y (byte) of struct (yv)
            self._pos += (-self._pos & 7) + 1  # align 8 + 1 for 'y' byte
            field_0 = buf[self._pos - 1]

            # Now read the v (variant) of struct (yv)
            # first we read the signature
            signature_len = buf[self._pos]  # byte
            o = self._pos + 1
            self._pos += signature_len + 2  # one for the byte, one for the '\0'
            if field_0 == HEADER_UNIX_FDS_IDX:  # defined by self._unix_fds
                continue
            token_as_int = buf[o]
            # Now that we have the token we can read the variant value
            key = HEADER_IDX_TO_ARG_NAME[field_0]
            # Strings and signatures are the most common types
            # so we inline them for performance
            if token_as_int == TOKEN_O_AS_INT or token_as_int == TOKEN_S_AS_INT:
                headers[key] = self._read_string_unpack()
            elif token_as_int == TOKEN_G_AS_INT:
                headers[key] = self._read_signature()
            else:
                token = buf[o : o + signature_len].decode()
                # There shouldn't be any other types in the header
                # but just in case, we'll read it using the slow path
                headers[key] = readers[token](self, get_signature_tree(token).types[0])
        return headers

    def _read_header(self) -> None:
        """Read the header of the message."""
        # Signature is of the header is
        # BYTE, BYTE, BYTE, BYTE, UINT32, UINT32, ARRAY of STRUCT of (BYTE,VARIANT)
        self._read_to_pos(HEADER_SIGNATURE_SIZE)
        buffer = self._buf
        endian = buffer[0]
        self._message_type = buffer[1]
        self._flag = buffer[2]
        protocol_version = buffer[3]

        if protocol_version != PROTOCOL_VERSION:
            raise InvalidMessageError(
                f"got unknown protocol version: {protocol_version}"
            )

        if cython.compiled and (
            (endian == LITTLE_ENDIAN and SYS_IS_LITTLE_ENDIAN)
            or (endian == BIG_ENDIAN and SYS_IS_BIG_ENDIAN)
        ):
            self._is_native = 1  # pragma: no cover
            self._body_len = _cast_uint32_native(  # type: ignore[name-defined] # pragma: no cover
                buffer, 4
            )
            self._serial = _cast_uint32_native(  # type: ignore[name-defined] # pragma: no cover
                buffer, 8
            )
            self._header_len = _cast_uint32_native(  # type: ignore[name-defined] # pragma: no cover
                buffer, 12
            )
        elif endian == LITTLE_ENDIAN:
            (
                self._body_len,
                self._serial,
                self._header_len,
            ) = UNPACK_HEADER_LITTLE_ENDIAN(buffer, 4)
            self._uint32_unpack = UINT32_UNPACK_LITTLE_ENDIAN
            self._int16_unpack = INT16_UNPACK_LITTLE_ENDIAN
            self._uint16_unpack = UINT16_UNPACK_LITTLE_ENDIAN
        elif endian == BIG_ENDIAN:
            self._body_len, self._serial, self._header_len = UNPACK_HEADER_BIG_ENDIAN(
                buffer, 4
            )
            self._uint32_unpack = UINT32_UNPACK_BIG_ENDIAN
            self._int16_unpack = INT16_UNPACK_BIG_ENDIAN
            self._uint16_unpack = UINT16_UNPACK_BIG_ENDIAN
        else:
            raise InvalidMessageError(
                f"Expecting endianness as the first byte, got {endian} from {buffer}"
            )

        self._msg_len = (
            self._header_len + (-self._header_len & 7) + self._body_len
        )  # align 8
        if self._endian != endian:
            self._readers = self._readers_by_type[endian]
            self._endian = endian

    def _read_body(self) -> None:
        """Read the body of the message."""
        self._read_to_pos(HEADER_SIGNATURE_SIZE + self._msg_len)
        self._pos = HEADER_ARRAY_OF_STRUCT_SIGNATURE_POSITION
        header_fields = self._header_fields(self._header_len)
        self._pos += -self._pos & 7  # align 8
        signature = header_fields.pop("signature", "")
        if not self._body_len:
            tree = SIGNATURE_TREE_EMPTY
            body: List[Any] = []
        else:
            token_as_int = ord(signature[0])
            if len(signature) == 1:
                if token_as_int == TOKEN_O_AS_INT:
                    tree = SIGNATURE_TREE_O
                    body = [self._read_string_unpack()]
                elif token_as_int == TOKEN_S_AS_INT:
                    tree = SIGNATURE_TREE_S
                    body = [self._read_string_unpack()]
                else:
                    tree = get_signature_tree(signature)
                    body = [self._readers[t.token](self, t) for t in tree.types]
            elif token_as_int == TOKEN_S_AS_INT and signature == "sa{sv}as":
                tree = SIGNATURE_TREE_SA_SV_AS
                body = [
                    self._read_string_unpack(),
                    self.read_array(SIGNATURE_TREE_SA_SV_AS_TYPES_1),
                    self.read_array(SIGNATURE_TREE_SA_SV_AS_TYPES_2),
                ]
            elif token_as_int == TOKEN_O_AS_INT and signature == "oa{sa{sv}}":
                tree = SIGNATURE_TREE_OA_SA_SV
                body = [
                    self._read_string_unpack(),
                    self.read_array(SIGNATURE_TREE_OA_SA_SV_TYPES_1),
                ]
            elif token_as_int == TOKEN_O_AS_INT and signature == "oas":
                tree = SIGNATURE_TREE_OAS
                body = [
                    self._read_string_unpack(),
                    self.read_array(SIGNATURE_TREE_OAS_TYPES_1),
                ]
            elif token_as_int == TOKEN_A_AS_INT and signature == "a{oa{sa{sv}}}":
                tree = SIGNATURE_TREE_A_OA_SA_SV
                body = [self.read_array(SIGNATURE_TREE_A_OA_SA_SV_TYPES_0)]
            else:
                tree = get_signature_tree(signature)
                body = [self._readers[t.token](self, t) for t in tree.types]

        flags = MESSAGE_FLAG_MAP.get(self._flag)
        if flags is None:
            flags = MESSAGE_FLAG_INTENUM(self._flag)
        self._message = Message(
            message_type=MESSAGE_TYPE_MAP[self._message_type],
            flags=flags,
            unix_fds=self._unix_fds,
            signature=tree,
            body=body,
            serial=self._serial,
            # The D-Bus implementation already validates the message,
            # so we don't need to do it again.
            validate=False,
            **header_fields,
        )
        self._read_complete = True

    def unmarshall(self) -> Optional[Message]:
        """Unmarshall the message.

        The underlying read function will raise BlockingIOError if the
        if there are not enough bytes in the buffer. This allows unmarshall
        to be resumed when more data comes in over the wire.
        """
        return self._unmarshall()

    def _unmarshall(self) -> Optional[Message]:
        """Unmarshall the message.

        The underlying read function will raise BlockingIOError if the
        if there are not enough bytes in the buffer. This allows unmarshall
        to be resumed when more data comes in over the wire.
        """
        if self._read_complete:
            self._next_message()
        try:
            if not self._msg_len:
                self._read_header()
            self._read_body()
        except MARSHALL_STREAM_END_ERROR:
            return None
        return self._message

    _complex_parsers_unpack: Dict[
        str, Callable[["Unmarshaller", SignatureType], Any]
    ] = {
        "b": read_boolean,
        "o": read_string_unpack,
        "s": read_string_unpack,
        "g": read_signature,
        "a": read_array,
        "(": read_struct,
        "{": read_dict_entry,
        "v": read_variant,
        "h": read_uint32_unpack,
        UINT32_DBUS_TYPE: read_uint32_unpack,
        INT16_DBUS_TYPE: read_int16_unpack,
        UINT16_DBUS_TYPE: read_uint16_unpack,
    }

    _ctype_by_endian: Dict[int, Dict[str, READER_TYPE]] = {
        endian: build_simple_parsers(endian) for endian in (LITTLE_ENDIAN, BIG_ENDIAN)
    }

    _readers_by_type: Dict[int, Dict[str, READER_TYPE]] = {
        LITTLE_ENDIAN: {
            **_ctype_by_endian[LITTLE_ENDIAN],
            **_complex_parsers_unpack,
        },
        BIG_ENDIAN: {
            **_ctype_by_endian[BIG_ENDIAN],
            **_complex_parsers_unpack,
        },
    }
