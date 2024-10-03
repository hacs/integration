import hashlib
from re import split
from typing import Any, Dict, Sequence
from urllib.parse import parse_qsl, unquote, urlparse

from . import contrib  # noqa:F401
from .compat import random
from .hotp import HOTP as HOTP
from .otp import OTP as OTP
from .totp import TOTP as TOTP


def random_base32(length: int = 32, chars: Sequence[str] = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")) -> str:
    # Note: the otpauth scheme DOES NOT use base32 padding for secret lengths not divisible by 8.
    # Some third-party tools have bugs when dealing with such secrets.
    # We might consider warning the user when generating a secret of length not divisible by 8.
    if length < 32:
        raise ValueError("Secrets should be at least 160 bits")

    return "".join(random.choice(chars) for _ in range(length))


def random_hex(length: int = 40, chars: Sequence[str] = list("ABCDEF0123456789")) -> str:
    if length < 40:
        raise ValueError("Secrets should be at least 160 bits")
    return random_base32(length=length, chars=chars)


def parse_uri(uri: str) -> OTP:
    """
    Parses the provisioning URI for the OTP; works for either TOTP or HOTP.

    See also:
        https://github.com/google/google-authenticator/wiki/Key-Uri-Format

    :param uri: the hotp/totp URI to parse
    :returns: OTP object
    """

    # Secret (to be filled in later)
    secret = None

    # Data we'll parse to the correct constructor
    otp_data: Dict[str, Any] = {}

    # Parse with URLlib
    parsed_uri = urlparse(unquote(uri))

    if parsed_uri.scheme != "otpauth":
        raise ValueError("Not an otpauth URI")

    # Parse issuer/accountname info
    accountinfo_parts = split(":|%3A", parsed_uri.path[1:], maxsplit=1)
    if len(accountinfo_parts) == 1:
        otp_data["name"] = accountinfo_parts[0]
    else:
        otp_data["issuer"] = accountinfo_parts[0]
        otp_data["name"] = accountinfo_parts[1]

    # Parse values
    for key, value in parse_qsl(parsed_uri.query):
        if key == "secret":
            secret = value
        elif key == "issuer":
            if "issuer" in otp_data and otp_data["issuer"] is not None and otp_data["issuer"] != value:
                raise ValueError("If issuer is specified in both label and parameters, it should be equal.")
            otp_data["issuer"] = value
        elif key == "algorithm":
            if value == "SHA1":
                otp_data["digest"] = hashlib.sha1
            elif value == "SHA256":
                otp_data["digest"] = hashlib.sha256
            elif value == "SHA512":
                otp_data["digest"] = hashlib.sha512
            else:
                raise ValueError("Invalid value for algorithm, must be SHA1, SHA256 or SHA512")
        elif key == "digits":
            digits = int(value)
            if digits not in [6, 7, 8]:
                raise ValueError("Digits may only be 6, 7, or 8")
            otp_data["digits"] = digits
        elif key == "period":
            otp_data["interval"] = int(value)
        elif key == "counter":
            otp_data["initial_count"] = int(value)
        elif key != "image":
            raise ValueError("{} is not a valid parameter".format(key))

    if not secret:
        raise ValueError("No secret found in URI")

    # Create objects
    if parsed_uri.netloc == "totp":
        return TOTP(secret, **otp_data)
    elif parsed_uri.netloc == "hotp":
        return HOTP(secret, **otp_data)

    raise ValueError("Not a supported OTP type")
