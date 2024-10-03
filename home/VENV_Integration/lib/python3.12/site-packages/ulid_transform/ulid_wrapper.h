#ifndef ULID_WRAPPER_H
#define ULID_WRAPPER_H
#include <stdint.h>

void _cpp_ulid(char dst[26]);
void _cpp_ulid_bytes(uint8_t dst[16]);
void _cpp_ulid_at_time(double epoch_time, char dst[26]);
void _cpp_ulid_at_time_bytes(double epoch_time, uint8_t dst[16]);
void _cpp_ulid_to_bytes(const char * ulid_string, uint8_t dst[16]);
void _cpp_bytes_to_ulid(const uint8_t b[16], char dst[26]);
void _cpp_hexlify_16(const uint8_t b[16], char dst[32]);
uint64_t _cpp_bytes_to_timestamp(const uint8_t b[16]);
#endif
