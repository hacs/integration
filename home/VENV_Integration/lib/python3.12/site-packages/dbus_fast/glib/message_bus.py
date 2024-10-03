import io
import logging
import traceback
from typing import Callable, Optional

from .. import introspection as intr
from .._private.unmarshaller import Unmarshaller
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
from ..message_bus import BaseMessageBus
from .proxy_object import ProxyObject

# glib is optional
_import_error = None
try:
    from gi.repository import GLib

    _GLibSource = GLib.Source
except ImportError as e:
    _import_error = e

    class _GLibSource:
        pass


class _MessageSource(_GLibSource):
    def __init__(self, bus):
        self.unmarshaller = None
        self.bus = bus

    def prepare(self):
        return (False, -1)

    def check(self):
        return False

    def dispatch(self, callback, user_data):
        try:
            while self.bus._stream.readable():
                if not self.unmarshaller:
                    self.unmarshaller = Unmarshaller(self.bus._stream)

                message = self.unmarshaller.unmarshall()
                if message:
                    callback(message)
                    self.unmarshaller = None
                else:
                    break
        except Exception as e:
            self.bus.disconnect()
            self.bus._finalize(e)
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE


class _MessageWritableSource(_GLibSource):
    def __init__(self, bus):
        self.bus = bus
        self.buf = b""
        self.message_stream = None
        self.chunk_size = 128

    def prepare(self):
        return (False, -1)

    def check(self):
        return False

    def dispatch(self, callback, user_data):
        try:
            if self.buf:
                self.bus._stream.write(self.buf)
                self.buf = b""

            if self.message_stream:
                while True:
                    self.buf = self.message_stream.read(self.chunk_size)
                    if self.buf == b"":
                        break
                    self.bus._stream.write(self.buf)
                    if len(self.buf) < self.chunk_size:
                        self.buf = b""
                        break
                    self.buf = b""

            self.bus._stream.flush()

            if not self.bus._buffered_messages:
                return GLib.SOURCE_REMOVE
            else:
                message = self.bus._buffered_messages.pop(0)
                self.message_stream = io.BytesIO(message._marshall(False))
                return GLib.SOURCE_CONTINUE
        except BlockingIOError:
            return GLib.SOURCE_CONTINUE
        except Exception as e:
            self.bus._finalize(e)
            return GLib.SOURCE_REMOVE


class _AuthLineSource(_GLibSource):
    def __init__(self, stream):
        self.stream = stream
        self.buf = b""

    def prepare(self):
        return (False, -1)

    def check(self):
        return False

    def dispatch(self, callback, user_data):
        self.buf += self.stream.read()
        if self.buf[-2:] == b"\r\n":
            resp = callback(self.buf.decode()[:-2])
            if resp:
                return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE


class MessageBus(BaseMessageBus):
    """The message bus implementation for use with the GLib main loop.

    The message bus class is the entry point into all the features of the
    library. It sets up a connection to the DBus daemon and exposes an
    interface to send and receive messages and expose services.

    You must call :func:`connect() <dbus_fast.glib.MessageBus.connect>` or
    :func:`connect_sync() <dbus_fast.glib.MessageBus.connect_sync>` before
    using this message bus.

    :param bus_type: The type of bus to connect to. Affects the search path for
        the bus address.
    :type bus_type: :class:`BusType <dbus_fast.BusType>`
    :param bus_address: A specific bus address to connect to. Should not be
        used under normal circumstances.
    :param auth: The authenticator to use, defaults to an instance of
        :class:`AuthExternal <dbus_fast.auth.AuthExternal>`.
    :type auth: :class:`Authenticator <dbus_fast.auth.Authenticator>`

    :ivar connected: True if this message bus is expected to be able to send
        and receive messages.
    :vartype connected: bool
    :ivar unique_name: The unique name of the message bus connection. It will
        be :class:`None` until the message bus connects.
    :vartype unique_name: str
    """

    def __init__(
        self,
        bus_address: Optional[str] = None,
        bus_type: BusType = BusType.SESSION,
        auth: Optional[Authenticator] = None,
    ):
        if _import_error:
            raise _import_error

        super().__init__(bus_address, bus_type, ProxyObject)
        self._main_context = GLib.main_context_default()
        # buffer messages until connect
        self._buffered_messages = []

        if auth is None:
            self._auth = AuthExternal()
        else:
            self._auth = auth

    def _on_message(self, msg: Message) -> None:
        try:
            self._process_message(msg)
        except Exception as e:
            logging.error(
                f"got unexpected error processing a message: {e}.\n{traceback.format_exc()}"
            )

    def connect(
        self,
        connect_notify: Optional[
            Callable[["MessageBus", Optional[Exception]], None]
        ] = None,
    ):
        """Connect this message bus to the DBus daemon.

        This method or the synchronous version must be called before the
        message bus can be used.

        :param connect_notify: A callback that will be called with this message
            bus. May return an :class:`Exception` on connection errors or
            :class:`AuthError <dbus_fast.AuthError>` on authorization errors.
        :type callback: :class:`Callable`
        """

        def authenticate_notify(exc):
            if exc is not None:
                if connect_notify is not None:
                    connect_notify(None, exc)
                return
            self.message_source = _MessageSource(self)
            self.message_source.set_callback(self._on_message)
            self.message_source.attach(self._main_context)

            self.writable_source = None

            self.message_source.add_unix_fd(self._fd, GLib.IO_IN)

            def on_hello(reply, err):
                if err:
                    if connect_notify:
                        connect_notify(reply, err)
                    return

                self.unique_name = reply.body[0]

                for m in self._buffered_messages:
                    self.send(m)

                if connect_notify:
                    connect_notify(self, err)

            hello_msg = Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus",
                member="Hello",
                serial=self.next_serial(),
            )

            self._method_return_handlers[hello_msg.serial] = on_hello
            self._stream.write(hello_msg._marshall(False))
            self._stream.flush()

        self._authenticate(authenticate_notify)

    def connect_sync(self) -> "MessageBus":
        """Connect this message bus to the DBus daemon.

        This method or the asynchronous version must be called before the
        message bus can be used.

        :returns: This message bus for convenience.
        :rtype: :class:`MessageBus <dbus_fast.glib.MessageBus>`

        :raises:
            - :class:`AuthError <dbus_fast.AuthError>` - If authorization to \
              the DBus daemon failed.
            - :class:`Exception` - If there was a connection error.
        """
        main = GLib.MainLoop()
        connection_error = None

        def connect_notify(bus, err):
            nonlocal connection_error
            connection_error = err
            main.quit()

        self.connect(connect_notify)
        main.run()

        if connection_error:
            raise connection_error

        return self

    def call(
        self,
        msg: Message,
        reply_notify: Optional[
            Callable[[Optional[Message], Optional[Exception]], None]
        ] = None,
    ):
        """Send a method call and asynchronously wait for a reply from the DBus
        daemon.

        :param msg: The method call message to send.
        :type msg: :class:`Message <dbus_fast.Message>`
        :param reply_notify: A callback that will be called with the reply to
            this message. May return an :class:`Exception` on connection errors.
        :type reply_notify: Callable
        """
        BaseMessageBus._check_callback_type(reply_notify)
        self._call(msg, reply_notify)

    def call_sync(self, msg: Message) -> Optional[Message]:
        """Send a method call and synchronously wait for a reply from the DBus
        daemon.

        :param msg: The method call message to send.
        :type msg: :class:`Message <dbus_fast.Message>`

        :returns: A message in reply to the message sent. If the message does
            not expect a reply based on the message flags or type, returns
            ``None`` immediately.
        :rtype: :class:`Message <dbus_fast.Message>`

        :raises:
            - :class:`DBusError <dbus_fast.DBusError>` - If the service threw \
                  an error for the method call or returned an invalid result.
            - :class:`Exception` - If a connection error occurred.
        """
        if (
            msg.flags & MessageFlag.NO_REPLY_EXPECTED
            or msg.message_type is not MessageType.METHOD_CALL
        ):
            self.send(msg)
            return None

        if not msg.serial:
            msg.serial = self.next_serial()

        main = GLib.MainLoop()
        handler_reply = None
        connection_error = None

        def reply_handler(reply, err):
            nonlocal handler_reply
            nonlocal connection_error

            handler_reply = reply
            connection_error = err

            main.quit()

        self._method_return_handlers[msg.serial] = reply_handler
        self.send(msg)
        main.run()

        if connection_error:
            raise connection_error

        return handler_reply

    def introspect_sync(self, bus_name: str, path: str) -> intr.Node:
        """Get introspection data for the node at the given path from the given
        bus name.

        Calls the standard ``org.freedesktop.DBus.Introspectable.Introspect``
        on the bus for the path.

        :param bus_name: The name to introspect.
        :type bus_name: str
        :param path: The path to introspect.
        :type path: str

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
        """
        main = GLib.MainLoop()
        request_result = None
        request_error = None

        def reply_notify(result, err):
            nonlocal request_result
            nonlocal request_error

            request_result = result
            request_error = err

            main.quit()

        super().introspect(bus_name, path, reply_notify)
        main.run()

        if request_error:
            raise request_error

        return request_result

    def request_name_sync(
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
        main = GLib.MainLoop()
        request_result = None
        request_error = None

        def reply_notify(result, err):
            nonlocal request_result
            nonlocal request_error

            request_result = result
            request_error = err

            main.quit()

        super().request_name(name, flags, reply_notify)
        main.run()

        if request_error:
            raise request_error

        return request_result

    def release_name_sync(self, name: str) -> ReleaseNameReply:
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
        main = GLib.MainLoop()
        release_result = None
        release_error = None

        def reply_notify(result, err):
            nonlocal release_result
            nonlocal release_error

            release_result = result
            release_error = err

            main.quit()

        super().release_name(name, reply_notify)
        main.run()

        if release_error:
            raise release_error

        return release_result

    def send(self, msg: Message):
        if not msg.serial:
            msg.serial = self.next_serial()

        self._buffered_messages.append(msg)

        if self.unique_name:
            self._schedule_write()

    def get_proxy_object(
        self, bus_name: str, path: str, introspection: intr.Node
    ) -> ProxyObject:
        return super().get_proxy_object(bus_name, path, introspection)

    def _schedule_write(self):
        if self.writable_source is None or self.writable_source.is_destroyed():
            self.writable_source = _MessageWritableSource(self)
            self.writable_source.attach(self._main_context)
            self.writable_source.add_unix_fd(self._fd, GLib.IO_OUT)

    def _authenticate(self, authenticate_notify):
        self._stream.write(b"\0")
        first_line = self._auth._authentication_start()
        if first_line is not None:
            if type(first_line) is not str:
                raise AuthError("authenticator gave response not type str")
            self._stream.write(f"{first_line}\r\n".encode())
            self._stream.flush()

        def line_notify(line):
            try:
                resp = self._auth._receive_line(line)
                self._stream.write(Authenticator._format_line(resp))
                self._stream.flush()
                if resp == "BEGIN":
                    self._readline_source = None
                    authenticate_notify(None)
                    return True
            except Exception as e:
                authenticate_notify(e)
                return True

        readline_source = _AuthLineSource(self._stream)
        readline_source.set_callback(line_notify)
        readline_source.add_unix_fd(self._fd, GLib.IO_IN)
        readline_source.attach(self._main_context)
        # make sure it doesnt get cleaned up
        self._readline_source = readline_source
