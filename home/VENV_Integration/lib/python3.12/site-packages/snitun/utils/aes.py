"""AES helper functions."""
from __future__ import annotations

import os


def generate_aes_keyset() -> tuple[bytes]:
    """Generate AES key + IV for CBC."""
    return (os.urandom(32), os.urandom(16))
