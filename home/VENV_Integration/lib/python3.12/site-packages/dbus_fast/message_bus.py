import inspect
import logging
import socket
import traceback
import xml.etree.ElementTree as ET
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Type, Union

from . import introspection as intr
from ._private.address import get_bus_address, parse_address
from ._private.util import replace_fds_with_idx, replace_idx_with_fds
from .constants import (
    BusType,
    ErrorType,
    MessageFlag,
    MessageType,
    NameFlag,
    ReleaseNameReply,
    RequestNameReply,
)
from .errors import DBusError, InvalidAddressError
from .message import Message
from .proxy_object import BaseProxyObject
from .send_reply import SendReply
from .service import ServiceInterface, _Method
from .signature import Variant
from .validators import assert_bus_name_valid, assert_object_path_valid

MESSAGE_TYPE_CALL = MessageType.METHOD_CALL
MESSAGE_TYPE_SIGNAL = MessageType.SIGNAL
NO_REPLY_EXPECTED_VALUE = MessageFlag.NO_REPLY_EXPECTED.value
NO_REPLY_EXPECTED = MessageFlag.NO_REPLY_EXPECTED
NONE = MessageFlag.NONE
_LOGGER = logging.getLogger(__name__)


_Message = Message


def _expects_reply(msg: _Message) -> bool:
    """Whether a message expects a reply."""
    if msg.flags is NO_REPLY_EXPECTED:
        return False
    if msg.flags is NONE:
        return True
    # Slow check for NO_REPLY_EXPECTED
    flag_value = msg.flags.value
    return not (flag_value & NO_REPLY_EXPECTED_VALUE)


def _block_unexpected_reply(reply: _Message) -> None:
    """Block a reply if it's not expected.

    Previously we silently ignored replies that were not expected, but this
    lead to implementation errors that were hard to debug. Now we log a
    debug message instead.
    """
    _LOGGER.debug(
        "Blocked attempt to send a reply from handler "
        "that received a message with flag "
        "MessageFlag.NO_REPLY_EXPECTED: %s",
        reply,
    )


BLOCK_UNEXPECTED_REPLY = _block_unexpected_reply


class BaseMessageBus:
    """An abstract class to manage a connection to a DBus message bus.

    The message bus class is the entry point into all the features of the
    library. It sets up a connection to the DBus daemon and exposes an
    interface to send and receive messages and expose services.

    This class is not meant to be used directly by users. For more information,
    see the documentation for the implementation of the message bus you plan to
    use.

    :param bus_type: The type of bus to connect to. Affects the search path for
        the bus address.
    :type bus_type: :class:`BusType <dbus_fast.BusType>`
    :param bus_address: A specific bus address to connect to. Should not be
        used under normal circumstances.
    :type bus_address: str
    :param ProxyObject: The proxy object implementation for this message bus.
        Must be passed in by an implementation that supports the high-level client.
    :type ProxyObject: Type[:class:`BaseProxyObject
        <dbus_fast.proxy_object.BaseProxyObject>`]

    :ivar unique_name: The unique name of the message bus connection. It will
        be :class:`None` until the message bus connects.
    :vartype unique_name: str
    :ivar connected: True if this message bus is expected to be able to send
        and receive messages.
    :vartype connected: bool
    """

    __slots__ = (
        "unique_name",
        "_disconnected",
        "_user_disconnect",
        "_method_return_handlers",
        "_serial",
        "_user_message_handlers",
        "_name_owners",
        "_path_exports",
        "_bus_address",
        "_name_owner_match_rule",
        "_match_rules",
        "_high_level_client_initialized",
        "_ProxyObject",
        "_machine_id",
        "_negotiate_unix_fd",
        "_sock",
        "_stream",
        "_fd",
    )

    def __init__(
        self,
        bus_address: Optional[str] = None,
        bus_type: BusType = BusType.SESSION,
        ProxyObject: Optional[Type[BaseProxyObject]] = None,
        negotiate_unix_fd: bool = False,
    ) -> None:
        self.unique_name: Optional[str] = None
        self._disconnected = False
        self._negotiate_unix_fd = negotiate_unix_fd

        # True if the user disconnected himself, so don't throw errors out of
        # the main loop.
        self._user_disconnect = False

        self._method_return_handlers: Dict[
            int, Callable[[Optional[Message], Optional[Exception]], None]
        ] = {}
        self._serial = 0
        self._user_message_handlers: List[
            Callable[[Message], Union[Message, bool, None]]
        ] = []
        # the key is the name and the value is the unique name of the owner.
        # This cache is kept up to date by the NameOwnerChanged signal and is
        # used to route messages to the correct proxy object. (used for the
        # high level client only)
        self._name_owners: Dict[str, str] = {}
        # used for the high level service
        self._path_exports: Dict[str, list[ServiceInterface]] = {}
        self._bus_address = (
            parse_address(bus_address)
            if bus_address
            else parse_address(get_bus_address(bus_type))
        )
        # the bus implementations need this rule for the high level client to
        # work correctly.
        self._name_owner_match_rule = "sender='org.freedesktop.DBus',interface='org.freedesktop.DBus',path='/org/freedesktop/DBus',member='NameOwnerChanged'"
        # _match_rules: the keys are match rules and the values are ref counts
        # (used for the high level client only)
        self._match_rules: Dict[str, int] = {}
        self._high_level_client_initialized = False
        self._ProxyObject = ProxyObject

        # machine id is lazy loaded
        self._machine_id: Optional[int] = None
        self._sock: Optional[socket.socket] = None
        self._fd: Optional[int] = None
        self._stream: Optional[Any] = None

        self._setup_socket()

    @property
    def connected(self) -> bool:
        if self.unique_name is None or self._disconnected or self._user_disconnect:
            return False
        return True

    def export(self, path: str, interface: ServiceInterface) -> None:
        """Export the service interface on this message bus to make it available
        to other clients.

        :param path: The object path to export this interface on.
        :type path: str
        :param interface: The service interface to export.
        :type interface: :class:`ServiceInterface
            <dbus_fast.service.ServiceInterface>`

        :raises:
            - :class:`InvalidObjectPathError <dbus_fast.InvalidObjectPathError>` - If the given object path is not valid.
            - :class:`ValueError` - If an interface with this name is already exported on the message bus at this path
        """
        assert_object_path_valid(path)
        if not isinstance(interface, ServiceInterface):
            raise TypeError("interface must be a ServiceInterface")

        if path not in self._path_exports:
            self._path_exports[path] = []

        for f in self._path_exports[path]:
            if f.name == interface.name:
                raise ValueError(
                    f'An interface with this name is already exported on this bus at path "{path}": "{interface.name}"'
                )

        self._path_exports[path].append(interface)
        ServiceInterface._add_bus(interface, self, self._make_method_handler)
        self._emit_interface_added(path, interface)

    def unexport(
        self, path: str, interface: Optional[Union[ServiceInterface, str]] = None
    ) -> None:
        """Unexport the path or service interface to make it no longer
        available to clients.

        :param path: The object path to unexport.
        :type path: str
        :param interface: The interface instance or the name of the interface
            to unexport. If ``None``, unexport every interface on the path.
        :type interface: :class:`ServiceInterface
            <dbus_fast.service.ServiceInterface>` or str or None

        :raises:
            - :class:`InvalidObjectPathError <dbus_fast.InvalidObjectPathError>` - If the given object path is not valid.
        """
        assert_object_path_valid(path)
        if type(interface) not in [str, type(None)] and not isinstance(
            interface, ServiceInterface
        ):
            raise TypeError("interface must be a ServiceInterface or interface name")

        if path not in self._path_exports:
            return

        exports = self._path_exports[path]

        if type(interface) is str:
            try:
                interface = next(iface for iface in exports if iface.name == interface)
            except StopIteration:
                return

        removed_interfaces = []
        if interface is None:
            del self._path_exports[path]
            for iface in filter(lambda e: not self._has_interface(e), exports):
                removed_interfaces.append(iface.name)
                ServiceInterface._remove_bus(iface, self)
        else:
            for i, iface in enumerate(exports):
                if iface is interface:
                    removed_interfaces.append(iface.name)
                    del self._path_exports[path][i]
                    if not self._path_exports[path]:
                        del self._path_exports[path]
                    if not self._has_interface(iface):
                        ServiceInterface._remove_bus(iface, self)
                    break
        self._emit_interface_removed(path, removed_interfaces)

    def introspect(
        self,
        bus_name: str,
        path: str,
        callback: Callable[[Optional[intr.Node], Optional[Exception]], None],
        check_callback_type: bool = True,
    ) -> None:
        """Get introspection data for the node at the given path from the given
        bus name.

        Calls the standard ``org.freedesktop.DBus.Introspectable.Introspect``
        on the bus for the path.

        :param bus_name: The name to introspect.
        :type bus_name: str
        :param path: The path to introspect.
        :type path: str
        :param callback: A callback that will be called with the introspection
            data as a :class:`Node <dbus_fast.introspection.Node>`.
        :type callback: :class:`Callable`

        :raises:
            - :class:`InvalidObjectPathError <dbus_fast.InvalidObjectPathError>` - If the given object path is not valid.
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If the given bus name is not valid.
        """
        if check_callback_type:
            BaseMessageBus._check_callback_type(callback)

        def reply_notify(reply: Optional[Message], err: Optional[Exception]) -> None:
            try:
                BaseMessageBus._check_method_return(reply, err, "s")
                result = intr.Node.parse(reply.body[0])  # type: ignore[union-attr]
            except Exception as e:
                callback(None, e)
                return

            callback(result, None)

        self._call(
            Message(
                destination=bus_name,
                path=path,
                interface="org.freedesktop.DBus.Introspectable",
                member="Introspect",
            ),
            reply_notify,
        )

    def _emit_interface_added(self, path: str, interface: ServiceInterface) -> None:
        """Emit the ``org.freedesktop.DBus.ObjectManager.InterfacesAdded`` signal.

        This signal is intended to be used to alert clients when
        a new interface has been added.

        :param path: Path of exported object.
        :type path: str
        :param interface: Exported service interface.
        :type interface: :class:`ServiceInterface
            <dbus_fast.service.ServiceInterface>`
        """
        if self._disconnected:
            return

        def get_properties_callback(
            interface: ServiceInterface,
            result: Any,
            user_data: Any,
            e: Optional[Exception],
        ) -> None:
            if e is not None:
                try:
                    raise e
                except Exception:
                    logging.error(
                        "An exception ocurred when emitting ObjectManager.InterfacesAdded for %s. "
                        "Some properties will not be included in the signal.",
                        interface.name,
                        exc_info=True,
                    )

            body = {interface.name: result}

            self.send(
                Message.new_signal(
                    path=path,
                    interface="org.freedesktop.DBus.ObjectManager",
                    member="InterfacesAdded",
                    signature="oa{sa{sv}}",
                    body=[path, body],
                )
            )

        ServiceInterface._get_all_property_values(interface, get_properties_callback)

    def _emit_interface_removed(self, path: str, removed_interfaces: List[str]) -> None:
        """Emit the ``org.freedesktop.DBus.ObjectManager.InterfacesRemoved` signal.

        This signal is intended to be used to alert clients when
        a interface has been removed.

        :param path: Path of removed (unexported) object.
        :type path: str
        :param removed_interfaces: List of unexported service interfaces.
        :type removed_interfaces: list[str]
        """
        if self._disconnected:
            return

        self.send(
            Message.new_signal(
                path=path,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesRemoved",
                signature="oas",
                body=[path, removed_interfaces],
            )
        )

    def request_name(
        self,
        name: str,
        flags: NameFlag = NameFlag.NONE,
        callback: Optional[
            Callable[[Optional[RequestNameReply], Optional[Exception]], None]
        ] = None,
        check_callback_type: bool = True,
    ) -> None:
        """Request that this message bus owns the given name.

        :param name: The name to request.
        :type name: str
        :param flags: Name flags that affect the behavior of the name request.
        :type flags: :class:`NameFlag <dbus_fast.NameFlag>`
        :param callback: A callback that will be called with the reply of the
            request as a :class:`RequestNameReply <dbus_fast.RequestNameReply>`.
        :type callback: :class:`Callable`

        :raises:
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If the given bus name is not valid.
        """
        assert_bus_name_valid(name)

        if callback is not None and check_callback_type:
            BaseMessageBus._check_callback_type(callback)

        if type(flags) is not NameFlag:
            flags = NameFlag(flags)

        message = Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="RequestName",
            signature="su",
            body=[name, flags],
        )

        if callback is None:
            self._call(message, None)
            return

        def reply_notify(reply: Optional[Message], err: Optional[Exception]) -> None:
            try:
                BaseMessageBus._check_method_return(reply, err, "u")
                result = RequestNameReply(reply.body[0])  # type: ignore[union-attr]
            except Exception as e:
                callback(None, e)  # type: ignore[misc]
                return

            callback(result, None)  # type: ignore[misc]

        self._call(message, reply_notify)

    def release_name(
        self,
        name: str,
        callback: Optional[
            Callable[[Optional[ReleaseNameReply], Optional[Exception]], None]
        ] = None,
        check_callback_type: bool = True,
    ) -> None:
        """Request that this message bus release the given name.

        :param name: The name to release.
        :type name: str
        :param callback: A callback that will be called with the reply of the
            release request as a :class:`ReleaseNameReply
            <dbus_fast.ReleaseNameReply>`.
        :type callback: :class:`Callable`

        :raises:
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If the given bus name is not valid.
        """
        assert_bus_name_valid(name)

        if callback is not None and check_callback_type:
            BaseMessageBus._check_callback_type(callback)

        message = Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="ReleaseName",
            signature="s",
            body=[name],
        )

        if callback is None:
            self._call(message, None)
            return

        def reply_notify(reply: Optional[Message], err: Optional[Exception]) -> None:
            try:
                BaseMessageBus._check_method_return(reply, err, "u")
                result = ReleaseNameReply(reply.body[0])  # type: ignore[union-attr]
            except Exception as e:
                callback(None, e)  # type: ignore[misc]
                return

            callback(result, None)  # type: ignore[misc]

        self._call(message, reply_notify)

    def get_proxy_object(
        self, bus_name: str, path: str, introspection: Union[intr.Node, str, ET.Element]
    ) -> BaseProxyObject:
        """Get a proxy object for the path exported on the bus that owns the
        name. The object is expected to export the interfaces and nodes
        specified in the introspection data.

        This is the entry point into the high-level client.

        :param bus_name: The name on the bus to get the proxy object for.
        :type bus_name: str
        :param path: The path on the client for the proxy object.
        :type path: str
        :param introspection: XML introspection data used to build the
            interfaces on the proxy object.
        :type introspection: :class:`Node <dbus_fast.introspection.Node>` or str or :class:`ElementTree`

        :returns: A proxy object for the given path on the given name.
        :rtype: :class:`BaseProxyObject <dbus_fast.proxy_object.BaseProxyObject>`

        :raises:
            - :class:`InvalidBusNameError <dbus_fast.InvalidBusNameError>` - If the given bus name is not valid.
            - :class:`InvalidObjectPathError <dbus_fast.InvalidObjectPathError>` - If the given object path is not valid.
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the introspection data for the node is not valid.
        """
        if self._ProxyObject is None:
            raise Exception(
                "the message bus implementation did not provide a proxy object class"
            )

        self._init_high_level_client()

        return self._ProxyObject(bus_name, path, introspection, self)

    def disconnect(self) -> None:
        """Disconnect the message bus by closing the underlying connection asynchronously.

        All pending  and future calls will error with a connection error.
        """
        self._user_disconnect = True
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            logging.warning("could not shut down socket", exc_info=True)

    def next_serial(self) -> int:
        """Get the next serial for this bus. This can be used as the ``serial``
        attribute of a :class:`Message <dbus_fast.Message>` to manually handle
        the serial of messages.

        :returns: The next serial for the bus.
        :rtype: int
        """
        self._serial += 1
        return self._serial

    def add_message_handler(
        self, handler: Callable[[Message], Optional[Union[Message, bool]]]
    ) -> None:
        """Add a custom message handler for incoming messages.

        The handler should be a callable that takes a :class:`Message
        <dbus_fast.Message>`. If the message is a method call, you may return
        another Message as a reply and it will be marked as handled. You may
        also return ``True`` to mark the message as handled without sending a
        reply.

        :param handler: A handler that will be run for every message the bus
            connection received.
        :type handler: :class:`Callable` or None
        """
        error_text = "a message handler must be callable with a single parameter"
        if not callable(handler):
            raise TypeError(error_text)

        handler_signature = inspect.signature(handler)
        if len(handler_signature.parameters) != 1:
            raise TypeError(error_text)

        self._user_message_handlers.append(handler)

    def remove_message_handler(
        self, handler: Callable[[Message], Optional[Union[Message, bool]]]
    ) -> None:
        """Remove a message handler that was previously added by
        :func:`add_message_handler()
        <dbus_fast.message_bus.BaseMessageBus.add_message_handler>`.

        :param handler: A message handler.
        :type handler: :class:`Callable`
        """
        for i, h in enumerate(self._user_message_handlers):
            if h == handler:
                del self._user_message_handlers[i]
                return

    def send(self, msg: Message) -> None:
        """Asynchronously send a message on the message bus.

        :param msg: The message to send.
        :type msg: :class:`Message <dbus_fast.Message>`
        """
        raise NotImplementedError(
            'the "send" method must be implemented in the inheriting class'
        )

    def _finalize(self, err: Optional[Exception]) -> None:
        """should be called after the socket disconnects with the disconnection
        error to clean up resources and put the bus in a disconnected state"""
        if self._disconnected:
            return

        self._disconnected = True

        for handler in self._method_return_handlers.values():
            try:
                handler(None, err)
            except Exception:
                logging.warning(
                    "a message handler threw an exception on shutdown", exc_info=True
                )

        self._method_return_handlers.clear()

        for path in list(self._path_exports):
            self.unexport(path)

        self._user_message_handlers.clear()

    def _has_interface(self, interface: ServiceInterface) -> bool:
        for _, exports in self._path_exports.items():
            for iface in exports:
                if iface is interface:
                    return True

        return False

    def _interface_signal_notify(
        self,
        interface: ServiceInterface,
        interface_name: str,
        member: str,
        signature: str,
        body: List[Any],
        unix_fds: List[int] = [],
    ) -> None:
        path = None
        for p, ifaces in self._path_exports.items():
            for i in ifaces:
                if i is interface:
                    path = p

        if path is None:
            raise Exception(
                "Could not find interface on bus (this is a bug in dbus-fast)"
            )

        self.send(
            Message.new_signal(
                path=path,
                interface=interface_name,
                member=member,
                signature=signature,
                body=body,
                unix_fds=unix_fds,
            )
        )

    def _introspect_export_path(self, path: str) -> intr.Node:
        assert_object_path_valid(path)

        if path in self._path_exports:
            node = intr.Node.default(path)
            for interface in self._path_exports[path]:
                node.interfaces.append(interface.introspect())
        else:
            node = intr.Node(path)

        children = set()

        for export_path in self._path_exports:
            if not export_path.startswith(path):
                continue

            child_path = export_path.split(path, maxsplit=1)[1]
            if path != "/" and child_path and child_path[0] != "/":
                continue

            child_path = child_path.lstrip("/")
            child_name = child_path.split("/", maxsplit=1)[0]

            children.add(child_name)

        node.nodes = [intr.Node(name) for name in children if name]

        return node

    def _setup_socket(self) -> None:
        err = None

        for transport, options in self._bus_address:
            filename = None
            ip_addr = ""
            ip_port = 0

            if transport == "unix":
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._stream = self._sock.makefile("rwb")
                self._fd = self._sock.fileno()

                if "path" in options:
                    filename = options["path"]
                elif "abstract" in options:
                    filename = b"\0" + options["abstract"].encode()
                else:
                    raise InvalidAddressError(
                        "got unix transport with unknown path specifier"
                    )

                try:
                    self._sock.connect(filename)
                    self._sock.setblocking(False)
                    break
                except Exception as e:
                    err = e

            elif transport == "tcp":
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._stream = self._sock.makefile("rwb")
                self._fd = self._sock.fileno()

                if "host" in options:
                    ip_addr = options["host"]
                if "port" in options:
                    ip_port = int(options["port"])

                try:
                    self._sock.connect((ip_addr, ip_port))
                    self._sock.setblocking(False)
                    break
                except Exception as e:
                    err = e

            else:
                raise InvalidAddressError(f"got unknown address transport: {transport}")

        if err:
            raise err

    def _reply_notify(
        self,
        msg: Message,
        callback: Optional[Callable[[Optional[Message], Optional[Exception]], None]],
        reply: Optional[Message],
        err: Optional[Exception],
    ) -> None:
        """Callback on reply."""
        if reply and msg.destination and reply.sender:
            self._name_owners[msg.destination] = reply.sender
        callback(reply, err)

    def _call(
        self,
        msg: Message,
        callback: Optional[Callable[[Optional[Message], Optional[Exception]], None]],
    ) -> None:
        if not msg.serial:
            msg.serial = self.next_serial()

        reply_expected = _expects_reply(msg)
        # Make sure the return reply handler is installed
        # before sending the message to avoid a race condition
        # where the reply is lost in case the backend can
        # send it right away.
        if reply_expected:
            self._method_return_handlers[msg.serial] = partial(
                self._reply_notify, msg, callback
            )

        self.send(msg)

        if not reply_expected:
            callback(None, None)

    @staticmethod
    def _check_callback_type(callback: Callable) -> None:
        """Raise a TypeError if the user gives an invalid callback as a parameter"""

        text = "a callback must be callable with two parameters"

        if not callable(callback):
            raise TypeError(text)

        fn_signature = inspect.signature(callback)
        if len(fn_signature.parameters) != 2:
            raise TypeError(text)

    @staticmethod
    def _check_method_return(
        msg: Optional[Message], err: Optional[Exception], signature: str
    ) -> None:
        if err:
            raise err
        elif msg is None:
            raise DBusError(
                ErrorType.INTERNAL_ERROR, "invalid message type for method call", msg
            )
        elif (
            msg.message_type == MessageType.METHOD_RETURN and msg.signature == signature
        ):
            return
        elif msg.message_type == MessageType.ERROR:
            raise DBusError._from_message(msg)
        else:
            raise DBusError(
                ErrorType.INTERNAL_ERROR, "invalid message type for method call", msg
            )

    def _process_message(self, msg: _Message) -> None:
        """Process a message received from the message bus."""
        handled = False
        for user_handler in self._user_message_handlers:
            try:
                result = user_handler(msg)
                if result:
                    if type(result) is Message:
                        self.send(result)
                    handled = True
                    break
            except DBusError as e:
                if msg.message_type is MESSAGE_TYPE_CALL:
                    self.send(e._as_message(msg))
                    handled = True
                    break
                else:
                    logging.exception("A message handler raised an exception: %s", e)
            except Exception as e:
                logging.exception("A message handler raised an exception: %s", e)
                if msg.message_type is MESSAGE_TYPE_CALL:
                    self.send(
                        Message.new_error(
                            msg,
                            ErrorType.INTERNAL_ERROR,
                            f"An internal error occurred: {e}.\n{traceback.format_exc()}",
                        )
                    )
                    handled = True
                    break

        if msg.message_type is MESSAGE_TYPE_SIGNAL:
            if (
                msg.member == "NameOwnerChanged"
                and msg.sender == "org.freedesktop.DBus"
                and msg.path == "/org/freedesktop/DBus"
                and msg.interface == "org.freedesktop.DBus"
            ):
                [name, old_owner, new_owner] = msg.body
                if new_owner:
                    self._name_owners[name] = new_owner
                elif name in self._name_owners:
                    del self._name_owners[name]
            return

        if msg.message_type is MESSAGE_TYPE_CALL:
            if not handled:
                handler = self._find_message_handler(msg)
                if _expects_reply(msg) is False:
                    if handler:
                        handler(msg, BLOCK_UNEXPECTED_REPLY)
                    else:
                        _LOGGER.error(
                            '"%s.%s" with signature "%s" could not be found',
                            msg.interface,
                            msg.member,
                            msg.signature,
                        )
                    return

                send_reply = SendReply(self, msg)
                with send_reply:
                    if handler:
                        handler(msg, send_reply)
                    else:
                        send_reply(
                            Message.new_error(
                                msg,
                                ErrorType.UNKNOWN_METHOD,
                                f"{msg.interface}.{msg.member} with signature "
                                f'"{msg.signature}" could not be found',
                            )
                        )
            return

        # An ERROR or a METHOD_RETURN
        return_handler = self._method_return_handlers.get(msg.reply_serial)
        if return_handler is not None:
            if not handled:
                return_handler(msg, None)
            del self._method_return_handlers[msg.reply_serial]

    def _callback_method_handler(
        self,
        interface: ServiceInterface,
        method: _Method,
        msg: Message,
        send_reply: Callable[[Message], None],
    ) -> None:
        """This is the callback that will be called when a method call is."""
        args = ServiceInterface._c_msg_body_to_args(msg) if msg.unix_fds else msg.body
        result = method.fn(interface, *args)
        if send_reply is BLOCK_UNEXPECTED_REPLY or _expects_reply(msg) is False:
            return
        body, fds = ServiceInterface._c_fn_result_to_body(
            result,
            signature_tree=method.out_signature_tree,
            replace_fds=self._negotiate_unix_fd,
        )
        send_reply(
            Message(
                message_type=MessageType.METHOD_RETURN,
                reply_serial=msg.serial,
                destination=msg.sender,
                signature=method.out_signature,
                body=body,
                unix_fds=fds,
            )
        )

    def _make_method_handler(
        self, interface: ServiceInterface, method: _Method
    ) -> Callable[[Message, Callable[[Message], None]], None]:
        return partial(self._callback_method_handler, interface, method)

    def _find_message_handler(
        self, msg: _Message
    ) -> Optional[Callable[[Message, Callable[[Message], None]], None]]:
        if "org.freedesktop.DBus." in msg.interface:
            if (
                msg.interface == "org.freedesktop.DBus.Introspectable"
                and msg.member == "Introspect"
                and msg.signature == ""
            ):
                return self._default_introspect_handler

            if msg.interface == "org.freedesktop.DBus.Properties":
                return self._default_properties_handler

            if msg.interface == "org.freedesktop.DBus.Peer":
                if msg.member == "Ping" and msg.signature == "":
                    return self._default_ping_handler
                elif msg.member == "GetMachineId" and msg.signature == "":
                    return self._default_get_machine_id_handler

            if (
                msg.interface == "org.freedesktop.DBus.ObjectManager"
                and msg.member == "GetManagedObjects"
            ):
                return self._default_get_managed_objects_handler

        msg_path = msg.path
        if msg_path:
            interfaces = self._path_exports.get(msg_path)
            if not interfaces:
                return None
            for interface in interfaces:
                methods = ServiceInterface._c_get_methods(interface)
                for method in methods:
                    if method.disabled:
                        continue

                    if (
                        msg.interface == interface.name
                        and msg.member == method.name
                        and msg.signature == method.in_signature
                    ):
                        return ServiceInterface._c_get_handler(interface, method, self)

        return None

    def _default_introspect_handler(
        self, msg: Message, send_reply: Callable[[Message], None]
    ) -> None:
        introspection = self._introspect_export_path(msg.path).tostring()
        send_reply(Message.new_method_return(msg, "s", [introspection]))

    def _default_ping_handler(
        self, msg: Message, send_reply: Callable[[Message], None]
    ) -> None:
        send_reply(Message.new_method_return(msg))

    def _default_get_machine_id_handler(
        self, msg: Message, send_reply: Callable[[Message], None]
    ) -> None:
        if self._machine_id:
            send_reply(Message.new_method_return(msg, "s", self._machine_id))
            return

        def reply_handler(reply, err):
            if err:
                # the bus has been disconnected, cannot send a reply
                return

            if reply.message_type == MessageType.METHOD_RETURN:
                self._machine_id = reply.body[0]
                send_reply(Message.new_method_return(msg, "s", [self._machine_id]))
            elif reply.message_type == MessageType.ERROR:
                send_reply(Message.new_error(msg, reply.error_name, reply.body))
            else:
                send_reply(
                    Message.new_error(msg, ErrorType.FAILED, "could not get machine_id")
                )

        self._call(
            Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus.Peer",
                member="GetMachineId",
            ),
            reply_handler,
        )

    def _default_get_managed_objects_handler(
        self, msg: Message, send_reply: Callable[[Message], None]
    ) -> None:
        result = {}
        result_signature = "a{oa{sa{sv}}}"
        error_handled = False

        def is_result_complete():
            if not result:
                return True
            for n, interfaces in result.items():
                for value in interfaces.values():
                    if value is None:
                        return False

            return True

        nodes = [
            node
            for node in self._path_exports
            if msg.path == "/" or node.startswith(msg.path + "/")
        ]

        # first build up the result object to know when it's complete
        for node in nodes:
            result[node] = {}
            for interface in self._path_exports[node]:
                result[node][interface.name] = None

        if is_result_complete():
            send_reply(Message.new_method_return(msg, result_signature, [result]))
            return

        def get_all_properties_callback(interface, values, node, err):
            nonlocal error_handled
            if err is not None:
                if not error_handled:
                    error_handled = True
                    send_reply.send_error(err)
                return

            result[node][interface.name] = values

            if is_result_complete():
                send_reply(Message.new_method_return(msg, result_signature, [result]))

        for node in nodes:
            for interface in self._path_exports[node]:
                ServiceInterface._get_all_property_values(
                    interface, get_all_properties_callback, node
                )

    def _default_properties_handler(
        self, msg: Message, send_reply: Callable[[Message], None]
    ) -> None:
        methods = {"Get": "ss", "Set": "ssv", "GetAll": "s"}
        if msg.member not in methods or methods[msg.member] != msg.signature:
            raise DBusError(
                ErrorType.UNKNOWN_METHOD,
                f'properties interface doesn\'t have method "{msg.member}" with signature "{msg.signature}"',
            )

        interface_name = msg.body[0]
        if interface_name == "":
            raise DBusError(
                ErrorType.NOT_SUPPORTED,
                "getting and setting properties with an empty interface string is not supported yet",
            )

        elif msg.path not in self._path_exports:
            raise DBusError(
                ErrorType.UNKNOWN_OBJECT, f'no interfaces at path: "{msg.path}"'
            )

        match = [
            iface
            for iface in self._path_exports[msg.path]
            if iface.name == interface_name
        ]
        if not match:
            if interface_name in [
                "org.freedesktop.DBus.Properties",
                "org.freedesktop.DBus.Introspectable",
                "org.freedesktop.DBus.Peer",
                "org.freedesktop.DBus.ObjectManager",
            ]:
                # the standard interfaces do not have properties
                if msg.member == "Get" or msg.member == "Set":
                    prop_name = msg.body[1]
                    raise DBusError(
                        ErrorType.UNKNOWN_PROPERTY,
                        f'interface "{interface_name}" does not have property "{prop_name}"',
                    )
                elif msg.member == "GetAll":
                    send_reply(Message.new_method_return(msg, "a{sv}", [{}]))
                    return
                else:
                    assert False
            raise DBusError(
                ErrorType.UNKNOWN_INTERFACE,
                f'could not find an interface "{interface_name}" at path: "{msg.path}"',
            )

        interface = match[0]
        properties = ServiceInterface._get_properties(interface)

        if msg.member == "Get" or msg.member == "Set":
            prop_name = msg.body[1]
            match = [
                prop
                for prop in properties
                if prop.name == prop_name and not prop.disabled
            ]
            if not match:
                raise DBusError(
                    ErrorType.UNKNOWN_PROPERTY,
                    f'interface "{interface_name}" does not have property "{prop_name}"',
                )

            prop = match[0]
            if msg.member == "Get":
                if not prop.access.readable():
                    raise DBusError(
                        ErrorType.UNKNOWN_PROPERTY,
                        "the property does not have read access",
                    )

                def get_property_callback(interface, prop, prop_value, err):
                    try:
                        if err is not None:
                            send_reply.send_error(err)
                            return

                        body, unix_fds = replace_fds_with_idx(
                            prop.signature, [prop_value]
                        )

                        send_reply(
                            Message.new_method_return(
                                msg,
                                "v",
                                [Variant(prop.signature, body[0])],
                                unix_fds=unix_fds,
                            )
                        )
                    except Exception as e:
                        send_reply.send_error(e)

                ServiceInterface._get_property_value(
                    interface, prop, get_property_callback
                )

            elif msg.member == "Set":
                if not prop.access.writable():
                    raise DBusError(
                        ErrorType.PROPERTY_READ_ONLY, "the property is readonly"
                    )
                value = msg.body[2]
                if value.signature != prop.signature:
                    raise DBusError(
                        ErrorType.INVALID_SIGNATURE,
                        f'wrong signature for property. expected "{prop.signature}"',
                    )
                assert prop.prop_setter

                def set_property_callback(interface, prop, err):
                    if err is not None:
                        send_reply.send_error(err)
                        return
                    send_reply(Message.new_method_return(msg))

                body = replace_idx_with_fds(
                    value.signature, [value.value], msg.unix_fds
                )
                ServiceInterface._set_property_value(
                    interface, prop, body[0], set_property_callback
                )

        elif msg.member == "GetAll":

            def get_all_properties_callback(interface, values, user_data, err):
                if err is not None:
                    send_reply.send_error(err)
                    return
                body, unix_fds = replace_fds_with_idx("a{sv}", [values])
                send_reply(
                    Message.new_method_return(msg, "a{sv}", body, unix_fds=unix_fds)
                )

            ServiceInterface._get_all_property_values(
                interface, get_all_properties_callback
            )

        else:
            assert False

    def _init_high_level_client(self) -> None:
        """The high level client is initialized when the first proxy object is
        gotten. Currently just sets up the match rules for the name owner cache
        so signals can be routed to the right objects."""
        if self._high_level_client_initialized:
            return
        self._high_level_client_initialized = True

        def add_match_notify(msg, err):
            if err:
                logging.error(
                    f'add match request failed. match="{self._name_owner_match_rule}", {err}'
                )
            elif msg.message_type == MessageType.ERROR:
                logging.error(
                    f'add match request failed. match="{self._name_owner_match_rule}", {msg.body[0]}'
                )

        self._call(
            Message(
                destination="org.freedesktop.DBus",
                interface="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                member="AddMatch",
                signature="s",
                body=[self._name_owner_match_rule],
            ),
            add_match_notify,
        )

    def _add_match_rule(self, match_rule):
        """Add a match rule. Match rules added by this function are refcounted
        and must be removed by _remove_match_rule(). This is for use in the
        high level client only."""
        if match_rule == self._name_owner_match_rule:
            return

        if match_rule in self._match_rules:
            self._match_rules[match_rule] += 1
            return

        self._match_rules[match_rule] = 1

        def add_match_notify(msg: Message, err: Optional[Exception]) -> None:
            if err:
                logging.error(f'add match request failed. match="{match_rule}", {err}')
            elif msg.message_type == MessageType.ERROR:
                logging.error(
                    f'add match request failed. match="{match_rule}", {msg.body[0]}'
                )

        self._call(
            Message(
                destination="org.freedesktop.DBus",
                interface="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                member="AddMatch",
                signature="s",
                body=[match_rule],
            ),
            add_match_notify,
        )

    def _remove_match_rule(self, match_rule):
        """Remove a match rule added with _add_match_rule(). This is for use in
        the high level client only."""
        if match_rule == self._name_owner_match_rule:
            return

        if match_rule in self._match_rules:
            self._match_rules[match_rule] -= 1
            if self._match_rules[match_rule] > 0:
                return

        del self._match_rules[match_rule]

        def remove_match_notify(msg, err):
            if self._disconnected:
                return

            if err:
                logging.error(
                    f'remove match request failed. match="{match_rule}", {err}'
                )
            elif msg.message_type == MessageType.ERROR:
                logging.error(
                    f'remove match request failed. match="{match_rule}", {msg.body[0]}'
                )

        self._call(
            Message(
                destination="org.freedesktop.DBus",
                interface="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                member="RemoveMatch",
                signature="s",
                body=[match_rule],
            ),
            remove_match_notify,
        )
