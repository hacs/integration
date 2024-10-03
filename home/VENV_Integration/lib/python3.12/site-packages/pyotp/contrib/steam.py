import hashlib
from typing import Optional

from ..totp import TOTP

STEAM_CHARS = "23456789BCDFGHJKMNPQRTVWXY"  # steam's custom alphabet
STEAM_DEFAULT_DIGITS = 5  # Steam TOTP code length


class Steam(TOTP):
    """
    Steam's custom TOTP. Subclass of `pyotp.totp.TOTP`.
    """

    def __init__(self, s: str, name: Optional[str] = None, issuer: Optional[str] = None, interval: int = 30) -> None:
        """
        :param s: secret in base32 format
        :param interval: the time interval in seconds for OTP. This defaults to 30.
        :param name: account name
        :param issuer: issuer
        """
        self.interval = interval
        super().__init__(s=s, digits=10, digest=hashlib.sha1, name=name, issuer=issuer)

    def generate_otp(self, input: int) -> str:
        """
        :param input: the HMAC counter value to use as the OTP input.
            Usually either the counter, or the computed integer based on the Unix timestamp
        """
        str_code = super().generate_otp(input)
        int_code = int(str_code)

        steam_code = ""
        total_chars = len(STEAM_CHARS)

        for _ in range(STEAM_DEFAULT_DIGITS):
            pos = int_code % total_chars
            char = STEAM_CHARS[int(pos)]
            steam_code += char
            int_code //= total_chars

        return steam_code
