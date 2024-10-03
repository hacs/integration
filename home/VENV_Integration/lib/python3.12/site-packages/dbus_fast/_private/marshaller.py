from struct import Struct, error
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..signature import SignatureType, Variant, get_signature_tree

PACK_LITTLE_ENDIAN = "<"

PACK_UINT32 = Struct(f"{PACK_LITTLE_ENDIAN}I").pack
PACKED_UINT32_ZERO = PACK_UINT32(0)
PACKED_BOOL_FALSE = PACK_UINT32(int(0))
PACKED_BOOL_TRUE = PACK_UINT32(int(1))

_int = int
_bytes = bytes
_str = str


class Marshaller:
    """Marshall data for Dbus."""

    __slots__ = ("signature_tree", "_buf", "body")

    def __init__(self, signature: str, body: List[Any]) -> None:
        """Marshaller constructor."""
        self.signature_tree = get_signature_tree(signature)
        self._buf = bytearray()
        self.body = body

    @property
    def buffer(self) -> bytearray:
        return self._buf

    def _buffer(self) -> bytearray:
        return self._buf

    def align(self, n: _int) -> int:
        return self._align(n)

    def _align(self, n: _int) -> _int:
        offset = n - len(self._buf) % n
        if offset == 0 or offset == n:
            return 0
        for _ in range(offset):
            self._buf.append(0)
        return offset

    def write_boolean(self, boolean: bool, type_: SignatureType) -> int:
        return self._write_boolean(boolean)

    def _write_boolean(self, boolean: bool) -> int:
        written = self._align(4)
        self._buf += PACKED_BOOL_TRUE if boolean else PACKED_BOOL_FALSE
        return written + 4

    def write_signature(self, signature: str, type_: SignatureType) -> int:
        return self._write_signature(signature.encode())

    def _write_signature(self, signature_bytes: _bytes) -> int:
        signature_len = len(signature_bytes)
        buf = self._buf
        buf.append(signature_len)
        buf += signature_bytes
        buf.append(0)
        return signature_len + 2

    def write_string(self, value: _str, type_: SignatureType) -> int:
        return self._write_string(value)

    def _write_string(self, value: _str) -> int:
        value_bytes = value.encode()
        value_len = len(value_bytes)
        written = self._align(4) + 4
        buf = self._buf
        buf += PACK_UINT32(value_len)
        buf += value_bytes
        written += value_len
        buf.append(0)
        written += 1
        return written

    def write_variant(self, variant: Variant, type_: SignatureType) -> int:
        return self._write_variant(variant, type_)

    def _write_variant(self, variant: Variant, type_: SignatureType) -> int:
        signature = variant.signature
        signature_bytes = signature.encode()
        written = self._write_signature(signature_bytes)
        written += self._write_single(variant.type, variant.value)  # type: ignore[has-type]
        return written

    def write_array(
        self, array: Union[List[Any], Dict[Any, Any]], type_: SignatureType
    ) -> int:
        return self._write_array(array, type_)

    def _write_array(
        self, array: Union[List[Any], Dict[Any, Any]], type_: SignatureType
    ) -> int:
        # TODO max array size is 64MiB (67108864 bytes)
        written = self._align(4)
        # length placeholder
        buf = self._buf
        offset = len(buf)
        written += self._align(4) + 4
        buf += PACKED_UINT32_ZERO
        child_type = type_.children[0]
        token = child_type.token

        if token in "xtd{(":
            # the first alignment is not included in array size
            written += self._align(8)

        array_len = 0
        if token == "{":
            for key, value in array.items():  # type: ignore[union-attr]
                array_len += self.write_dict_entry([key, value], child_type)
        elif token == "y":
            array_len = len(array)
            buf += array
        elif token == "(":
            for value in array:
                array_len += self._write_struct(value, child_type)
        else:
            writer, packer, size = self._writers[token]
            if not writer:
                for value in array:
                    array_len += self._align(size) + size
                    buf += packer(value)  # type: ignore[misc]
            else:
                for value in array:
                    array_len += writer(self, value, child_type)

        array_len_packed = PACK_UINT32(array_len)
        for i in range(offset, offset + 4):
            buf[i] = array_len_packed[i - offset]

        return written + array_len

    def write_struct(
        self, array: Union[Tuple[Any], List[Any]], type_: SignatureType
    ) -> int:
        return self._write_struct(array, type_)

    def _write_struct(
        self, array: Union[Tuple[Any], List[Any]], type_: SignatureType
    ) -> int:
        written = self._align(8)
        for i, value in enumerate(array):
            written += self._write_single(type_.children[i], value)
        return written

    def write_dict_entry(self, dict_entry: List[Any], type_: SignatureType) -> int:
        written = self._align(8)
        written += self._write_single(type_.children[0], dict_entry[0])
        written += self._write_single(type_.children[1], dict_entry[1])
        return written

    def _write_single(self, type_: SignatureType, body: Any) -> int:
        t = type_.token
        if t == "y":
            self._buf.append(body)
            return 1
        elif t == "u":
            written = self._align(4)
            self._buf += PACK_UINT32(body)
            return written + 4
        elif t == "a":
            return self._write_array(body, type_)
        elif t == "s" or t == "o":
            return self._write_string(body)
        elif t == "v":
            return self._write_variant(body, type_)
        elif t == "b":
            return self._write_boolean(body)
        else:
            writer, packer, size = self._writers[t]
            if not writer:
                written = self._align(size)
                self._buf += packer(body)  # type: ignore[misc]
                return written + size
            return writer(self, body, type_)

    def marshall(self) -> bytearray:
        """Marshalls the body into a byte array"""
        return self._marshall()

    def _marshall(self) -> bytearray:
        """Marshalls the body into a byte array"""
        try:
            return self._construct_buffer()
        except KeyError as ex:
            raise NotImplementedError(f'type is not implemented yet: "{ex.args}"')
        except error:
            self.signature_tree.verify(self.body)
        raise RuntimeError("should not reach here")

    def _construct_buffer(self) -> bytearray:
        self._buf.clear()
        body = self.body
        for i, type_ in enumerate(self.signature_tree.types):
            self._write_single(type_, body[i])
        return self._buf

    _writers: Dict[
        str,
        Tuple[
            Optional[Callable[[Any, Any, SignatureType], int]],
            Optional[Callable[[Any], bytes]],
            int,
        ],
    ] = {
        "y": (None, Struct(f"{PACK_LITTLE_ENDIAN}B").pack, 1),
        "b": (write_boolean, None, 0),
        "n": (None, Struct(f"{PACK_LITTLE_ENDIAN}h").pack, 2),
        "q": (None, Struct(f"{PACK_LITTLE_ENDIAN}H").pack, 2),
        "i": (None, Struct(f"{PACK_LITTLE_ENDIAN}i").pack, 4),
        "u": (None, PACK_UINT32, 4),
        "x": (None, Struct(f"{PACK_LITTLE_ENDIAN}q").pack, 8),
        "t": (None, Struct(f"{PACK_LITTLE_ENDIAN}Q").pack, 8),
        "d": (None, Struct(f"{PACK_LITTLE_ENDIAN}d").pack, 8),
        "h": (None, Struct(f"{PACK_LITTLE_ENDIAN}I").pack, 4),
        "o": (write_string, None, 0),
        "s": (write_string, None, 0),
        "g": (write_signature, None, 0),
        "a": (write_array, None, 0),
        "(": (write_struct, None, 0),
        "{": (write_dict_entry, None, 0),
        "v": (write_variant, None, 0),
    }
