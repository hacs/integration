import enum
import os
from typing import List, Optional, Tuple

from .errors import AuthError

UID_NOT_SPECIFIED = -1

# The auth interface here is unstable. I would like to eventually open this up
# for people to define their own custom authentication protocols, but I'm not
# familiar with what's needed for that exactly. To work with any message bus
# implementation would require abstracting out all the IO. Async operations
# might be challenging because different IO backends have different ways of
# doing that. I might just end up giving the raw socket and leaving it all up
# to the user, but it would be nice to have a little guidance in the interface
# since a lot of it is strongly specified. If you have a need for this, contact
# the project maintainer to help stabilize this interface.


class _AuthResponse(enum.Enum):
    OK = "OK"
    REJECTED = "REJECTED"
    DATA = "DATA"
    ERROR = "ERROR"
    AGREE_UNIX_FD = "AGREE_UNIX_FD"

    @classmethod
    def parse(klass, line: str) -> Tuple["_AuthResponse", List[str]]:
        args = line.split(" ")
        response = klass(args[0])
        return response, args[1:]


# UNSTABLE
class Authenticator:
    """The base class for authenticators for :class:`MessageBus <dbus_fast.message_bus.BaseMessageBus>` authentication.

    In the future, the library may allow extending this class for custom authentication protocols.

    :seealso: https://dbus.freedesktop.org/doc/dbus-specification.html#auth-protocol
    """

    def _authentication_start(self, negotiate_unix_fd: bool = False) -> str:
        raise NotImplementedError(
            "authentication_start() must be implemented in the inheriting class"
        )

    def _receive_line(self, line: str) -> str:
        raise NotImplementedError(
            "receive_line() must be implemented in the inheriting class"
        )

    @staticmethod
    def _format_line(line: str) -> bytes:
        return f"{line}\r\n".encode()


class AuthExternal(Authenticator):
    """An authenticator class for the external auth protocol for use with the
    :class:`MessageBus <dbus_fast.message_bus.BaseMessageBus>`.

    :param uid: The uid to use when connecting to the message bus. Use UID_NOT_SPECIFIED to use the uid known to the kernel.
    :vartype uid: int

    :sealso: https://dbus.freedesktop.org/doc/dbus-specification.html#auth-protocol
    """

    def __init__(self, uid: Optional[int] = None) -> None:
        self.negotiate_unix_fd: bool = False
        self.negotiating_fds: bool = False
        self.uid: Optional[int] = uid

    def _authentication_start(self, negotiate_unix_fd: bool = False) -> str:
        self.negotiate_unix_fd = negotiate_unix_fd
        uid = self.uid
        if uid == UID_NOT_SPECIFIED:
            return "AUTH EXTERNAL"
        if uid is None:
            uid = os.getuid()
        hex_uid = str(uid).encode().hex()
        return f"AUTH EXTERNAL {hex_uid}"

    def _receive_line(self, line: str) -> str:
        response, args = _AuthResponse.parse(line)

        if response is _AuthResponse.OK:
            if self.negotiate_unix_fd:
                self.negotiating_fds = True
                return "NEGOTIATE_UNIX_FD"
            else:
                return "BEGIN"

        if response is _AuthResponse.AGREE_UNIX_FD:
            return "BEGIN"

        if response is _AuthResponse.DATA and self.uid == UID_NOT_SPECIFIED:
            return "DATA"

        raise AuthError(f"authentication failed: {response.value}: {args}")


class AuthAnonymous(Authenticator):
    """An authenticator class for the anonymous auth protocol for use with the
    :class:`MessageBus <dbus_fast.message_bus.BaseMessageBus>`.

    :sealso: https://dbus.freedesktop.org/doc/dbus-specification.html#auth-protocol
    """

    def _authentication_start(self, negotiate_unix_fd: bool = False) -> str:
        if negotiate_unix_fd:
            raise AuthError(
                "anonymous authentication does not support negotiating unix fds right now"
            )

        return "AUTH ANONYMOUS"

    def _receive_line(self, line: str) -> str:
        response, args = _AuthResponse.parse(line)

        if response != _AuthResponse.OK:
            raise AuthError(f"authentication failed: {response.value}: {args}")

        return "BEGIN"


# The following line provides backwards compatibility, remove at some point? --jrd
AuthAnnonymous = AuthAnonymous
