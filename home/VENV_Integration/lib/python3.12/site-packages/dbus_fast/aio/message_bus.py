import array
import asyncio
import contextlib
import logging
import socket
from collections import deque
from copy import copy
from functools import partial
from typing import Any, Callable, List, Optional, Set, Tuple

from .. import introspection as intr
from ..auth import Authenticator, AuthExternal
from ..constants import (
    BusType,
    MessageFlag,
    MessageType,
    NameFlag,
    ReleaseNameReply,
    RequestNameReply,
)
from ..errors import AuthError
from ..message import Message
from ..message_bus import BaseMessageBus, _block_unexpected_reply
from ..service import ServiceInterface
from .message_reader import build_message_reader
from .proxy_object import ProxyObject

NO_REPLY_EXPECTED_VALUE = MessageFlag.NO_REPLY_EXPECTED.value


def _generate_hello_serialized(next_serial: int) -> bytes:
    return Message(
        destination="org.freedesktop.DBus",
        path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus",
        member="Hello",
        serial=next_serial,
    )._marshall(False)


HELLO_1_SERIALIZED = _generate_hello_serialized(1)


def _future_set_exception(fut: asyncio.Future, exc: Exception) -> None:
    if fut is not None and not fut.done():
        fut.set_exception(exc)


def _future_set_result(fut: asyncio.Future, result: Any) -> None:
    if fut is not None and not fut.done():
        fut.set_result(result)


class _MessageWriter:
    """A class to handle writing messages to the message bus."""

    def __init__(self, bus: "MessageBus") -> None:
        """A class to handle writing messages to the message bus."""
        self.messages: deque[
            Tuple[bytearray, Optional[List[int]], Optional[asyncio.Future]]
        ] = deque()
        self.negotiate_unix_fd = bus._negotiate_unix_fd
        self.bus = bus
        self.sock = bus._sock
        self.loop = bus._loop
        self.buf: Optional[memoryview] = None
        self.fd = bus._fd
        self.offset = 0
        self.unix_fds: Optional[List[int]] = None
        self.fut: Optional[asyncio.Future] = None

    def write_callback(self, remove_writer: bool = True) -> None:
        """The callback to write messages to the message bus."""
        sock = self.sock
        try:
            while True:
                if self.buf is None:
                    # If there is no buffer, get the next message
                    if not self.messages:
                        # nothing more to write
                        if remove_writer:
                            self.loop.remove_writer(self.fd)
                        return

                    # Get the next message
                    buf, unix_fds, fut = self.messages.popleft()
                    self.unix_fds = unix_fds
                    self.buf = memoryview(buf)
                    self.offset = 0
                    self.fut = fut

                if self.unix_fds and self.negotiate_unix_fd:
                    ancdata = [
                        (
                            socket.SOL_SOCKET,
                            socket.SCM_RIGHTS,
                            array.array("i", self.unix_fds),
                        )
                    ]
                    self.offset += sock.sendmsg([self.buf[self.offset :]], ancdata)
                    self.unix_fds = None
                else:
                    self.offset += sock.send(self.buf[self.offset :])

                if self.offset < len(self.buf):
                    # wait for writable
                    return

                # finished writing
                self.buf = None
                _future_set_result(self.fut, None)
        except Exception as e:
            if self.bus._user_disconnect:
                _future_set_result(self.fut, None)
            else:
                _future_set_exception(self.fut, e)
            self.bus._finalize(e)

    def buffer_message(
        self, msg: Message, future: Optional[asyncio.Future] = None
    ) -> None:
        """Buffer a message to be sent later."""
        unix_fds = msg.unix_fds
        self.messages.append(
            (
                msg._marshall(self.negotiate_unix_fd),
                copy(unix_fds) if unix_fds else None,
                future,
            )
        )

    def _write_without_remove_writer(self) -> None:
        """Call the write callback without removing the writer."""
        self.write_callback(remove_writer=False)

    def schedule_write(
        self, msg: Optional[Message] = None, future: Optional[asyncio.Future] = None
    ) -> None:
        """Schedule a message to be written."""
        queue_is_empty = not self.messages
        if msg is not None:
            self.buffer_message(msg, future)

        if self.bus.unique_name:
            # Optimization: try to send now if the queue
            # is empty. With bleak this usually means we
            # can send right away 99% of the time which
            # is a huge improvement in latency.
            if queue_is_empty:
                self._write_without_remove_writer()

            if (
                self.buf is not None
                or self.messages
                or not self.fut
                or not self.fut.done()
            ):
                self.loop.add_writer(self.fd, self.write_callback)


class MessageBus(BaseMessageBus):
    """The message bus implementation for use with asyncio.

    The message bus class is the entry point into all the features of the
    library. It sets up a connection to the DBus daemon and exposes an
    interface to send and receive messages and expose services.

    You must call :func:`connect() <dbus_fast.aio.MessageBus.connect>` before
    using this message bus.

    :param bus_type: The type of bus to connect to. Affects the search path for
        the bus address.
    :type bus_type: :class:`BusType <dbus_fast.BusType>`
    :param bus_address: A specific bus address to connect to. Should not be
        used under normal circumstances.
    :param auth: The authenticator to use, defaults to an instance of
        :class:`AuthExternal <dbus_fast.auth.AuthExternal>`.
    :type auth: :class:`Authenticator <dbus_fast.auth.Authenticator>`
    :param negotiate_unix_fd: Allow the bus to send and receive Unix file
        descriptors (DBus type 'h'). This must be supported by the transport.
    :type negotiate_unix_fd: bool

    :ivar unique_name: The unique name of the message bus connection. It will
        be :class:`None` until the message bus connects.
    :vartype unique_name: str
    :ivar connected: True if this message bus is expected to be able to send
        and receive messages.
    :vartype connected: bool
    """

    __slots__ = ("_loop", "_auth", "_writer", "_disconnect_future", "_pending_futures")

    def __init__(
        self,
        bus_address: Optional[str] = None,
        bus_type: BusType = BusType.SESSION,
        auth: Optional[Authenticator] = None,
        negotiate_unix_fd: bool = False,
    ) -> None:
        super().__init__(bus_address, bus_type, ProxyObject, negotiate_unix_fd)
        self._loop = asyncio.get_running_loop()

        self._writer = _MessageWriter(self)

        if auth is None:
            self._auth = AuthExternal()
        else:
            self._auth = auth

        self._disconnect_future = self._loop.create_future()
        self._pending_futures: Set[asyncio.Future] = set()

    async def connect(self) -> "MessageBus":
        """Connect this message bus to the DBus daemon.

        This method must be called before the message bus can be used.

        :returns: This message bus for convenience.
        :rtype: :class:`MessageBus <dbus_fast.aio.MessageBus>`

        :raises:
            - :class:`AuthError <dbus_fast.AuthError>` - If authorization to \
              the DBus daemon failed.
            - :class:`Exception` - If there was a connection error.
        """
        await self._authenticate()

        future = self._loop.create_future()

        self._loop.add_reader(
            self._fd,
            build_message_reader(
                self._sock,
                self._process_message,
                self._finalize,
                self._negotiate_unix_fd,
            ),
        )

        def on_hello(reply, err):
            try:
                if err:
                    raise err
                self.unique_name = reply.body[0]
                self._writer.schedule_write()
                _future_set_result(future, self)
            except Exception as e:
                _future_set_exception(future, e)
                self.disconnect()
                self._finalize(err)

        next_serial = self.next_serial()
        self._method_return_handlers[next_serial] = on_hello
        if next_serial == 1:
            serialized = HELLO_1_SERIALIZED
        else:
            serialized = _generate_hello_serialized(next_serial)
        self._stream.write(serialized)
        self._stream.flush()
        return await future

    async def introspect(
        self, bus_name: str, path: str, timeout: float = 30.0
    ) -> intr.Node:
        """Get introspection data for the node at the given path from the given
        bus name.

        Calls the standard ``org.freedesktop.DBus.Introspectable.Introspect``
        on the bus for the path.

        :param bus_name: The name to introspect.
        :type bus_name: str
        :param path: The path to introspect.
        :type path: str
        :param timeout: The timeout to introspect.
        :type timeout: float

        :returns: The introspection data for the name at the path.
        :rtype: :class:`Node <dbus_fast.introspection.Node>`

        :raises:
            - :class:`InvalidObjectPathError <dbus_fast.InvalidObjectPathError>` \
                    - If the given object path is not valid.
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If \
                  the given bus name is not valid.
            - :class:`DBusError <dbus_fast.DBusError>` - If the service threw \
                  an error for the method call or returned an invalid result.
            - :class:`Exception` - If a connection error occurred.
            - :class:`asyncio.TimeoutError` - Waited for future but time run out.
        """
        future = self._loop.create_future()

        super().introspect(
            bus_name,
            path,
            partial(self._reply_handler, future),
            check_callback_type=False,
        )

        timer_handle = self._loop.call_later(
            timeout, _future_set_exception, future, asyncio.TimeoutError
        )
        try:
            return await future
        finally:
            timer_handle.cancel()

    async def request_name(
        self, name: str, flags: NameFlag = NameFlag.NONE
    ) -> RequestNameReply:
        """Request that this message bus owns the given name.

        :param name: The name to request.
        :type name: str
        :param flags: Name flags that affect the behavior of the name request.
        :type flags: :class:`NameFlag <dbus_fast.NameFlag>`

        :returns: The reply to the name request.
        :rtype: :class:`RequestNameReply <dbus_fast.RequestNameReply>`

        :raises:
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If \
                  the given bus name is not valid.
            - :class:`DBusError <dbus_fast.DBusError>` - If the service threw \
                  an error for the method call or returned an invalid result.
            - :class:`Exception` - If a connection error occurred.
        """
        future = self._loop.create_future()

        super().request_name(
            name, flags, partial(self._reply_handler, future), check_callback_type=False
        )

        return await future

    async def release_name(self, name: str) -> ReleaseNameReply:
        """Request that this message bus release the given name.

        :param name: The name to release.
        :type name: str

        :returns: The reply to the release request.
        :rtype: :class:`ReleaseNameReply <dbus_fast.ReleaseNameReply>`

        :raises:
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If \
                  the given bus name is not valid.
            - :class:`DBusError <dbus_fast.DBusError>` - If the service threw \
                  an error for the method call or returned an invalid result.
            - :class:`Exception` - If a connection error occurred.
        """
        future = self._loop.create_future()

        super().release_name(
            name, partial(self._reply_handler, future), check_callback_type=False
        )

        return await future

    async def call(self, msg: Message) -> Optional[Message]:
        """Send a method call and wait for a reply from the DBus daemon.

        :param msg: The method call message to send.
        :type msg: :class:`Message <dbus_fast.Message>`

        :returns: A message in reply to the message sent. If the message does
            not expect a reply based on the message flags or type, returns
            ``None`` after the message is sent.
        :rtype: :class:`Message <dbus_fast.Message>` or :class:`None` if no reply is expected.

        :raises:
            - :class:`Exception` - If a connection error occurred.
        """
        if (
            msg.flags.value & NO_REPLY_EXPECTED_VALUE
            or msg.message_type is not MessageType.METHOD_CALL
        ):
            await self.send(msg)
            return None

        future = self._loop.create_future()

        self._call(msg, partial(self._reply_handler, future))

        await future

        return future.result()

    def send(self, msg: Message) -> asyncio.Future:
        """Asynchronously send a message on the message bus.

        .. note:: This method may change to a couroutine function in the 1.0
            release of the library.

        :param msg: The message to send.
        :type msg: :class:`Message <dbus_fast.Message>`

        :returns: A future that resolves when the message is sent or a
            connection error occurs.
        :rtype: :class:`Future <asyncio.Future>`
        """
        if not msg.serial:
            msg.serial = self.next_serial()

        future = self._loop.create_future()
        self._writer.schedule_write(msg, future)
        return future

    def get_proxy_object(
        self, bus_name: str, path: str, introspection: intr.Node
    ) -> ProxyObject:
        return super().get_proxy_object(bus_name, path, introspection)

    async def wait_for_disconnect(self):
        """Wait for the message bus to disconnect.

        :returns: :class:`None` when the message bus has disconnected.
        :rtype: :class:`None`

        :raises:
            - :class:`Exception` - If connection was terminated unexpectedly or \
              an internal error occurred in the library.
        """
        return await self._disconnect_future

    def _make_method_handler(self, interface, method):
        if not asyncio.iscoroutinefunction(method.fn):
            return super()._make_method_handler(interface, method)

        negotiate_unix_fd = self._negotiate_unix_fd
        msg_body_to_args = ServiceInterface._msg_body_to_args
        fn_result_to_body = ServiceInterface._fn_result_to_body

        def _coroutine_method_handler(
            msg: Message, send_reply: Callable[[Message], None]
        ) -> None:
            """A coroutine method handler."""
            args = msg_body_to_args(msg) if msg.unix_fds else msg.body
            fut = asyncio.ensure_future(method.fn(interface, *args))
            # Hold a strong reference to the future to ensure
            # it is not garbage collected before it is done.
            self._pending_futures.add(fut)
            if (
                send_reply is _block_unexpected_reply
                or msg.flags.value & NO_REPLY_EXPECTED_VALUE
            ):
                fut.add_done_callback(self._pending_futures.discard)
                return

            # We only create the closure function if we are actually going to reply
            def _done(fut: asyncio.Future) -> None:
                """The callback for when the method is done."""
                with send_reply:
                    result = fut.result()
                    body, unix_fds = fn_result_to_body(
                        result, method.out_signature_tree, replace_fds=negotiate_unix_fd
                    )
                    send_reply(
                        Message.new_method_return(
                            msg, method.out_signature, body, unix_fds
                        )
                    )

            fut.add_done_callback(_done)
            # Discard the future only after running the done callback
            fut.add_done_callback(self._pending_futures.discard)

        return _coroutine_method_handler

    async def _auth_readline(self) -> str:
        buf = b""
        while buf[-2:] != b"\r\n":
            # The auth protocol is line based, so we can read until we get a
            # newline.
            buf += await self._loop.sock_recv(self._sock, 1024)
        return buf[:-2].decode()

    async def _authenticate(self) -> None:
        await self._loop.sock_sendall(self._sock, b"\0")

        first_line = self._auth._authentication_start(
            negotiate_unix_fd=self._negotiate_unix_fd
        )

        if first_line is not None:
            if type(first_line) is not str:
                raise AuthError("authenticator gave response not type str")
            await self._loop.sock_sendall(
                self._sock, Authenticator._format_line(first_line)
            )

        while True:
            response = self._auth._receive_line(await self._auth_readline())
            if response is not None:
                await self._loop.sock_sendall(
                    self._sock, Authenticator._format_line(response)
                )
                self._stream.flush()
            if response == "BEGIN":
                # The first octet received by the server after the \r\n of the BEGIN command
                # from the client must be the first octet of the authenticated/encrypted stream
                # of D-Bus messages.
                break

    def disconnect(self) -> None:
        """Disconnect the message bus by closing the underlying connection asynchronously.

        All pending  and future calls will error with a connection error.
        """
        super().disconnect()
        try:
            self._sock.close()
        except Exception:
            logging.warning("could not close socket", exc_info=True)

    def _finalize(self, err: Optional[Exception] = None) -> None:
        try:
            self._loop.remove_reader(self._fd)
        except Exception:
            logging.warning("could not remove message reader", exc_info=True)
        try:
            self._loop.remove_writer(self._fd)
        except Exception:
            logging.warning("could not remove message writer", exc_info=True)

        had_handlers = bool(self._method_return_handlers or self._user_message_handlers)

        super()._finalize(err)

        if self._disconnect_future.done():
            return

        if err and not self._user_disconnect:
            _future_set_exception(self._disconnect_future, err)
            # If this happens during a reply, the message handlers
            # will have the exception set and wait_for_disconnect will
            # never be called so we need to manually set the exception
            # as retrieved to avoid asyncio warnings when the future
            # is garbage collected.
            if had_handlers:
                with contextlib.suppress(Exception):
                    self._disconnect_future.exception()
        else:
            _future_set_result(self._disconnect_future, None)

    def _reply_handler(
        self, future: asyncio.Future, reply: Optional[Any], err: Optional[Exception]
    ) -> None:
        """The reply handler for method calls."""
        if err:
            _future_set_exception(future, err)
        else:
            _future_set_result(future, reply)
