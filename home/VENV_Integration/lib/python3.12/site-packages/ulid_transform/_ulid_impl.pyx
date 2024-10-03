# distutils: language = c++
# cython: language_level=3, c_string_type=str, c_string_encoding=ascii

# The `<bytes>xxx[:N]` syntax is required for two reasons:
# 1. When working with "ULID bytes", the buffer may contain NULs.
# 2. When working with ULID text, the buffer is exactly 26 bytes long and not NUL-terminated.
# See https://github.com/cython/cython/issues/3234

from libc.stdint cimport uint8_t, uint64_t


cdef extern from "ulid_wrapper.h":
    void _cpp_ulid(char dst[26]) nogil
    void _cpp_ulid_bytes(uint8_t dst[16]) nogil
    void _cpp_ulid_at_time(double epoch_time, char dst[26]) nogil
    void _cpp_ulid_at_time_bytes(double epoch_time, uint8_t dst[16]) nogil
    void _cpp_ulid_to_bytes(const char ulid_string[26], uint8_t dst[16]) nogil
    void _cpp_bytes_to_ulid(const uint8_t b[16], char * dst) nogil
    void _cpp_hexlify_16(const uint8_t b[16], char dst[32]) nogil
    uint64_t _cpp_bytes_to_timestamp(const uint8_t b[16]) nogil


def ulid_hex() -> str:
    """Generate a ULID in lowercase hex that will work for a UUID.

    This ulid should not be used for cryptographically secure
    operations.

    This string can be converted with https://github.com/ahawker/ulid

    ulid.from_uuid(uuid.UUID(ulid_hex))
    """
    cdef unsigned char ulid_bytes_buf[16]
    _cpp_ulid_bytes(ulid_bytes_buf)
    cdef char ulid_hex_buf[32]
    _cpp_hexlify_16(ulid_bytes_buf, ulid_hex_buf)
    return <str>ulid_hex_buf[:32]


def ulid_now_bytes() -> bytes:
    """Generate an ULID as 16 bytes that will work for a UUID."""
    cdef unsigned char ulid_bytes_buf[16]
    _cpp_ulid_bytes(ulid_bytes_buf)
    return <bytes>ulid_bytes_buf[:16]


def ulid_at_time_bytes(timestamp: float) -> bytes:
    """Generate an ULID as 16 bytes that will work for a UUID.

    uuid.UUID(bytes=ulid_bytes)
    """
    cdef unsigned char ulid_bytes_buf[16]
    _cpp_ulid_at_time_bytes(timestamp, ulid_bytes_buf)
    return <bytes>ulid_bytes_buf[:16]


def ulid_now() -> str:
    """Generate a ULID."""
    cdef char ulid_text_buf[26]
    _cpp_ulid(ulid_text_buf)
    return <str>ulid_text_buf[:26]


def ulid_at_time(timestamp: float) -> str:
    """Generate a ULID.

    This ulid should not be used for cryptographically secure
    operations.

     01AN4Z07BY      79KA1307SR9X4MV3
    |----------|    |----------------|
     Timestamp          Randomness
       48bits             80bits

    This string can be loaded directly with https://github.com/ahawker/ulid

    import ulid_transform as ulid_util
    import ulid
    ulid.parse(ulid_util.ulid())
    """
    cdef char ulid_text_buf[26]
    _cpp_ulid_at_time(timestamp, ulid_text_buf)
    return <str>ulid_text_buf[:26]


def ulid_to_bytes(value: str) -> bytes:
    """Decode a ulid to bytes."""
    if len(value) != 26:
        raise ValueError(f"ULID must be a 26 character string: {value}")
    cdef unsigned char ulid_bytes_buf[16]
    _cpp_ulid_to_bytes(value, ulid_bytes_buf)
    return <bytes>ulid_bytes_buf[:16]


def bytes_to_ulid(value: bytes) -> str:
    """Encode bytes to a ulid."""
    if len(value) != 16:
        raise ValueError(f"ULID bytes must be 16 bytes: {value!r}")
    cdef char ulid_text_buf[26]
    _cpp_bytes_to_ulid(value, ulid_text_buf)
    return <str>ulid_text_buf[:26]


def ulid_to_bytes_or_none(ulid: str | None) -> bytes | None:
    """Convert an ulid to bytes."""
    if ulid is None or len(ulid) != 26:
        return None
    cdef unsigned char ulid_bytes_buf[16]
    _cpp_ulid_to_bytes(ulid, ulid_bytes_buf)
    return <bytes>ulid_bytes_buf[:16]


def bytes_to_ulid_or_none(ulid_bytes: bytes | None) -> str | None:
    """Convert bytes to a ulid."""
    if ulid_bytes is None or len(ulid_bytes) != 16:
        return None
    cdef char ulid_text_buf[26]
    _cpp_bytes_to_ulid(ulid_bytes, ulid_text_buf)
    return <str>ulid_text_buf[:26]


def ulid_to_timestamp(ulid: str | bytes) -> int:
    """
    Get the timestamp from a ULID.
    The returned value is in milliseconds since the UNIX epoch.
    """
    cdef unsigned char ulid_bytes_buf[16]
    if not isinstance(ulid, bytes):
        if len(ulid) != 26:
            raise ValueError(f"ULID must be a 26 character string: {ulid}")
        _cpp_ulid_to_bytes(ulid, ulid_bytes_buf)
        return _cpp_bytes_to_timestamp(ulid_bytes_buf)
    else:
        if len(ulid) != 16:
            raise ValueError(f"ULID bytes must be 16 bytes: {ulid!r}")
        return _cpp_bytes_to_timestamp(ulid)
