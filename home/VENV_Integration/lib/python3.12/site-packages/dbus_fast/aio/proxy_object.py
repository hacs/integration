import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, List, Union

from .. import introspection as intr
from .._private.util import replace_fds_with_idx, replace_idx_with_fds
from ..constants import ErrorType, MessageFlag
from ..errors import DBusError
from ..message import Message
from ..message_bus import BaseMessageBus
from ..proxy_object import BaseProxyInterface, BaseProxyObject
from ..signature import Variant
from ..unpack import unpack_variants as unpack

if TYPE_CHECKING:
    from .message_bus import MessageBus as AioMessageBus

NO_REPLY_EXPECTED_VALUE = MessageFlag.NO_REPLY_EXPECTED.value


class ProxyInterface(BaseProxyInterface):
    """A class representing a proxy to an interface exported on the bus by
    another client for the asyncio :class:`MessageBus
    <dbus_fast.aio.MessageBus>` implementation.

    This class is not meant to be constructed directly by the user. Use
    :func:`ProxyObject.get_interface()
    <dbus_fast.aio.ProxyObject.get_interface>` on a asyncio proxy object to get
    a proxy interface.

    This class exposes methods to call DBus methods, listen to signals, and get
    and set properties on the interface that are created dynamically based on
    the introspection data passed to the proxy object that made this proxy
    interface.

    A *method call* takes this form:

    .. code-block:: python3

        result = await interface.call_[METHOD](*args)

    Where ``METHOD`` is the name of the method converted to snake case.

    DBus methods are exposed as coroutines that take arguments that correpond
    to the *in args* of the interface method definition and return a ``result``
    that corresponds to the *out arg*. If the method has more than one out arg,
    they are returned within a :class:`list`.

    To *listen to a signal* use this form:

    .. code-block:: python3

        interface.on_[SIGNAL](callback)

    To *stop listening to a signal* use this form:

    .. code-block:: python3

        interface.off_[SIGNAL](callback)

    Where ``SIGNAL`` is the name of the signal converted to snake case.

    DBus signals are exposed with an event-callback interface. The provided
    ``callback`` will be called when the signal is emitted with arguments that
    correspond to the *out args* of the interface signal definition.

    To *get or set a property* use this form:

    .. code-block:: python3

        value = await interface.get_[PROPERTY]()
        await interface.set_[PROPERTY](value)

    Where ``PROPERTY`` is the name of the property converted to snake case.

    DBus property getters and setters are exposed as coroutines. The ``value``
    must correspond to the type of the property in the interface definition.

    If the service returns an error for a DBus call, a :class:`DBusError
    <dbus_fast.DBusError>` will be raised with information about the error.
    """

    bus: "AioMessageBus"

    def _add_method(self, intr_method: intr.Method) -> None:
        async def method_fn(
            *args, flags=MessageFlag.NONE, unpack_variants: bool = False
        ):
            input_body, unix_fds = replace_fds_with_idx(
                intr_method.in_signature, list(args)
            )

            msg = await self.bus.call(
                Message(
                    destination=self.bus_name,
                    path=self.path,
                    interface=self.introspection.name,
                    member=intr_method.name,
                    signature=intr_method.in_signature,
                    body=input_body,
                    flags=flags,
                    unix_fds=unix_fds,
                )
            )

            if flags is not None and flags.value & NO_REPLY_EXPECTED_VALUE:
                return None

            BaseProxyInterface._check_method_return(msg, intr_method.out_signature)

            out_len = len(intr_method.out_args)

            body = replace_idx_with_fds(msg.signature_tree, msg.body, msg.unix_fds)

            if not out_len:
                return None

            if unpack_variants:
                body = unpack(body)

            if out_len == 1:
                return body[0]
            return body

        method_name = f"call_{BaseProxyInterface._to_snake_case(intr_method.name)}"
        setattr(self, method_name, method_fn)

    def _add_property(
        self,
        intr_property: intr.Property,
    ) -> None:
        async def property_getter(
            *, flags=MessageFlag.NONE, unpack_variants: bool = False
        ):
            msg = await self.bus.call(
                Message(
                    destination=self.bus_name,
                    path=self.path,
                    interface="org.freedesktop.DBus.Properties",
                    member="Get",
                    signature="ss",
                    body=[self.introspection.name, intr_property.name],
                )
            )

            BaseProxyInterface._check_method_return(msg, "v")
            variant = msg.body[0]
            if variant.signature != intr_property.signature:
                raise DBusError(
                    ErrorType.CLIENT_ERROR,
                    f'property returned unexpected signature "{variant.signature}"',
                    msg,
                )

            body = replace_idx_with_fds("v", msg.body, msg.unix_fds)[0].value

            if unpack_variants:
                return unpack(body)
            return body

        async def property_setter(val: Any) -> None:
            variant = Variant(intr_property.signature, val)

            body, unix_fds = replace_fds_with_idx(
                "ssv", [self.introspection.name, intr_property.name, variant]
            )

            msg = await self.bus.call(
                Message(
                    destination=self.bus_name,
                    path=self.path,
                    interface="org.freedesktop.DBus.Properties",
                    member="Set",
                    signature="ssv",
                    body=body,
                    unix_fds=unix_fds,
                )
            )

            BaseProxyInterface._check_method_return(msg)

        snake_case = BaseProxyInterface._to_snake_case(intr_property.name)
        setattr(self, f"get_{snake_case}", property_getter)
        setattr(self, f"set_{snake_case}", property_setter)


class ProxyObject(BaseProxyObject):
    """The proxy object implementation for the GLib :class:`MessageBus <dbus_fast.glib.MessageBus>`.

    For more information, see the :class:`BaseProxyObject <dbus_fast.proxy_object.BaseProxyObject>`.
    """

    def __init__(
        self,
        bus_name: str,
        path: str,
        introspection: Union[intr.Node, str, ET.Element],
        bus: BaseMessageBus,
    ) -> None:
        super().__init__(bus_name, path, introspection, bus, ProxyInterface)

    def get_interface(self, name: str) -> ProxyInterface:
        return super().get_interface(name)

    def get_children(self) -> List["ProxyObject"]:
        return super().get_children()
