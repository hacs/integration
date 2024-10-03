"""Helpers for resolving a private address if you know its identity resolving key.

This process uses 128bit IRK as encryption key for ECB AES.

One half of address is used to store a random 24bit number
(prand). This is encrypted to produce a "hash". The top 24 bits
of the hash should math the other half of the MAC address.

See https://www.mdpi.com/2227-7390/10/22/4346
"""

import binascii

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PADDING = b"\x00" * 13


def get_cipher_for_irk(irk: bytes) -> Cipher:
    return Cipher(algorithms.AES(irk), modes.ECB())  # noqa: S305


def resolve_private_address(
    cipher: Cipher,
    address: str,
) -> bool:
    rpa = binascii.unhexlify(address.replace(":", ""))

    if rpa[0] & 0xC0 != 0x40:
        # Not an RPA
        return False

    pt = PADDING + rpa[:3]

    encryptor = cipher.encryptor()
    ct = encryptor.update(pt) + encryptor.finalize()

    if ct[13:] != rpa[3:]:
        return False

    return True
