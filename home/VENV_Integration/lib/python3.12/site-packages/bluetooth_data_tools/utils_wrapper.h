#include <stdint.h>

/**
* Convert the given integer bluetooth address to its hexadecimal string representation.
* The buffer passed in must accept at least 17 bytes. It will NOT be null-terminated.
*/
void _uint64_to_bdaddr(uint64_t address, char bdaddr[17]) {
    static const char hex_table[] = "0123456789ABCDEF";
    bdaddr[0] = hex_table[(address >> 44) & 0x0F];
    bdaddr[1] = hex_table[(address >> 40) & 0x0F];
    bdaddr[2] = ':';
    bdaddr[3] = hex_table[(address >> 36) & 0x0F];
    bdaddr[4] = hex_table[(address >> 32) & 0x0F];
    bdaddr[5] = ':';
    bdaddr[6] = hex_table[(address >> 28) & 0x0F];
    bdaddr[7] = hex_table[(address >> 24) & 0x0F];
    bdaddr[8] = ':';
    bdaddr[9] = hex_table[(address >> 20) & 0x0F];
    bdaddr[10] = hex_table[(address >> 16) & 0x0F];
    bdaddr[11] = ':';
    bdaddr[12] = hex_table[(address >> 12) & 0x0F];
    bdaddr[13] = hex_table[(address >> 8) & 0x0F];
    bdaddr[14] = ':';
    bdaddr[15] = hex_table[(address >> 4) & 0x0F];
    bdaddr[16] = hex_table[address & 0x0F];
}
