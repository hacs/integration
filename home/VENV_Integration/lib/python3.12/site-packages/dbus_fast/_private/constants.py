from enum import Enum

PROTOCOL_VERSION = 1

LITTLE_ENDIAN = ord("l")
BIG_ENDIAN = ord("B")


class HeaderField(Enum):
    PATH = 1
    INTERFACE = 2
    MEMBER = 3
    ERROR_NAME = 4
    REPLY_SERIAL = 5
    DESTINATION = 6
    SENDER = 7
    SIGNATURE = 8
    UNIX_FDS = 9
