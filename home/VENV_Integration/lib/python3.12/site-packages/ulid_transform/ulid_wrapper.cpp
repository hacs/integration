#include "ulid_wrapper.h"
#include "ulid.hh"

/**
* Generate a new text ULID and write it to the provided buffer.
* The buffer is NOT null-terminated.
*/
void _cpp_ulid(char dst[26]) {
  ulid::ULID ulid;
  ulid::EncodeTimeSystemClockNow(ulid);
  ulid::EncodeEntropyRand(ulid);
  ulid::MarshalTo(ulid, dst);
}

/**
* Generate a new binary ULID and write it to the provided buffer.
*/
void _cpp_ulid_bytes(uint8_t dst[16]) {
  ulid::ULID ulid;
  ulid::EncodeTimeSystemClockNow(ulid);
  ulid::EncodeEntropyRand(ulid);
  ulid::MarshalBinaryTo(ulid, dst);
}

/**
* Generate a new text ULID at the provided epoch time and write it to the provided buffer.
* The buffer is NOT null-terminated.
*/
void _cpp_ulid_at_time(double epoch_time, char dst[26]) {
  ulid::ULID ulid;
  ulid::EncodeTimestamp(static_cast<int64_t>(epoch_time*1000), ulid);
  ulid::EncodeEntropyRand(ulid);
  ulid::MarshalTo(ulid, dst);
}

/**
* Generate a new binary ULID at the provided epoch time and write it to the provided buffer.
*/
void _cpp_ulid_at_time_bytes(double epoch_time, uint8_t dst[16]) {
  ulid::ULID ulid;
  ulid::EncodeTimestamp(static_cast<int64_t>(epoch_time*1000), ulid);
  ulid::EncodeEntropyRand(ulid);
  ulid::MarshalBinaryTo(ulid, dst);
}

/**
* Convert a text ULID to a binary ULID.
* The buffer passed in must contain at least 26 bytes.
* Invalid data will result in undefined behavior.
*/
void _cpp_ulid_to_bytes(const char * ulid_string, uint8_t dst[16]) {
  ulid::ULID ulid;
  ulid::UnmarshalFrom(ulid_string, ulid);
  ulid::MarshalBinaryTo(ulid, dst);
}

/**
* Convert a binary ULID to a text ULID.
* The buffer passed in must contain at least 16 bytes.
* The output buffer will NOT be null-terminated.
*/
void _cpp_bytes_to_ulid(const uint8_t b[16], char dst[26]) {
  ulid::ULID ulid;
  ulid::UnmarshalBinaryFrom(b, ulid);
  ulid::MarshalTo(ulid, dst);
}

/**
* Convert a buffer of exactly 16 bytes to 32 hex characters.
* The output buffer will NOT be null-terminated.
*/
void _cpp_hexlify_16(const uint8_t b[16], char dst[32]) {
    static const char hexdigits[17] = "0123456789abcdef";
    int in_index, out_index;
    for (in_index = out_index = 0; in_index < 16; in_index++) {
        uint8_t c = b[in_index];
        dst[out_index++] = hexdigits[c >> 4];
        dst[out_index++] = hexdigits[c & 0x0f];
    }
}

/**
* Interpret the first 6 bytes of a binary ULID as a timestamp.
*/
uint64_t _cpp_bytes_to_timestamp(const uint8_t b[16]) {
    uint64_t timestamp = 0;
    timestamp |= static_cast<uint64_t>(b[0]) << 40;
    timestamp |= static_cast<uint64_t>(b[1]) << 32;
    timestamp |= static_cast<uint64_t>(b[2]) << 24;
    timestamp |= static_cast<uint64_t>(b[3]) << 16;
    timestamp |= static_cast<uint64_t>(b[4]) << 8;
    timestamp |= static_cast<uint64_t>(b[5]);
    return timestamp;
}
