import logging
import socket
from functools import partial
from typing import Callable, Optional

from .._private.unmarshaller import Unmarshaller
from ..message import Message


def _message_reader(
    unmarshaller: Unmarshaller,
    process: Callable[[Message], None],
    finalize: Callable[[Optional[Exception]], None],
    negotiate_unix_fd: bool,
) -> None:
    """Reads messages from the unmarshaller and passes them to the process function."""
    try:
        while True:
            message = unmarshaller._unmarshall()
            if message is None:
                return
            try:
                process(message)
            except Exception:
                logging.error("Unexpected error processing message: %s", exc_info=True)
            # If we are not negotiating unix fds, we can stop reading as soon as we have
            # the buffer is empty as asyncio will call us again when there is more data.
            if (
                not negotiate_unix_fd
                and not unmarshaller._has_another_message_in_buffer()
            ):
                return
    except Exception as e:
        finalize(e)


def build_message_reader(
    sock: Optional[socket.socket],
    process: Callable[[Message], None],
    finalize: Callable[[Optional[Exception]], None],
    negotiate_unix_fd: bool,
) -> Callable[[], None]:
    """Build a callable that reads messages from the unmarshaller and passes them to the process function."""
    unmarshaller = Unmarshaller(None, sock, negotiate_unix_fd)
    return partial(_message_reader, unmarshaller, process, finalize, negotiate_unix_fd)
