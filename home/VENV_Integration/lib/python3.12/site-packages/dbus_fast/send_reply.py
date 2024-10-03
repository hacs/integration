import traceback
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type

from .constants import ErrorType
from .errors import DBusError
from .message import Message

if TYPE_CHECKING:
    from .message_bus import BaseMessageBus


class SendReply:
    """A context manager to send a reply to a message."""

    __slots__ = ("_bus", "_msg")

    def __init__(self, bus: "BaseMessageBus", msg: Message) -> None:
        """Create a new reply context manager."""
        self._bus = bus
        self._msg = msg

    def __enter__(self):
        return self

    def __call__(self, reply: Message) -> None:
        self._bus.send(reply)

    def _exit(
        self,
        exc_type: Optional[Type[Exception]],
        exc_value: Optional[Exception],
        tb: Optional[TracebackType],
    ) -> bool:
        if exc_value:
            if isinstance(exc_value, DBusError):
                self(exc_value._as_message(self._msg))
            else:
                self(
                    Message.new_error(
                        self._msg,
                        ErrorType.SERVICE_ERROR,
                        f"The service interface raised an error: {exc_value}.\n{traceback.format_tb(tb)}",
                    )
                )
            return True

        return False

    def __exit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc_value: Optional[Exception],
        tb: Optional[TracebackType],
    ) -> bool:
        return self._exit(exc_type, exc_value, tb)

    def send_error(self, exc: Exception) -> None:
        self._exit(exc.__class__, exc, exc.__traceback__)
