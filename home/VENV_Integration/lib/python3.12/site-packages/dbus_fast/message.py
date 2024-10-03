from typing import Any, List, Optional, Union

from ._private.constants import LITTLE_ENDIAN, PROTOCOL_VERSION, HeaderField
from ._private.marshaller import Marshaller
from .constants import ErrorType, MessageFlag, MessageType
from .errors import InvalidMessageError
from .signature import SignatureTree, Variant, get_signature_tree
from .validators import (
    assert_bus_name_valid,
    assert_interface_name_valid,
    assert_member_name_valid,
    assert_object_path_valid,
)

REQUIRED_FIELDS = {
    MessageType.METHOD_CALL.value: ("path", "member"),
    MessageType.SIGNAL.value: ("path", "member", "interface"),
    MessageType.ERROR.value: ("error_name", "reply_serial"),
    MessageType.METHOD_RETURN.value: ("reply_serial",),
}

HEADER_PATH = HeaderField.PATH.value
HEADER_INTERFACE = HeaderField.INTERFACE.value
HEADER_MEMBER = HeaderField.MEMBER.value
HEADER_ERROR_NAME = HeaderField.ERROR_NAME.value
HEADER_REPLY_SERIAL = HeaderField.REPLY_SERIAL.value
HEADER_DESTINATION = HeaderField.DESTINATION.value
HEADER_SIGNATURE = HeaderField.SIGNATURE.value
HEADER_UNIX_FDS = HeaderField.UNIX_FDS.value

MESSAGE_FLAG = MessageFlag

MESSAGE_FLAG_NONE = MessageFlag.NONE
MESSAGE_TYPE_METHOD_CALL = MessageType.METHOD_CALL


class Message:
    """A class for sending and receiving messages through the
    :class:`MessageBus <dbus_fast.message_bus.BaseMessageBus>` with the
    low-level api.

    A ``Message`` can be constructed by the user to send over the message bus.
    When messages are received, such as from method calls or signal emissions,
    they will use this class as well.

    :ivar destination: The address of the client for which this message is intended.
    :vartype destination: str
    :ivar path: The intended object path exported on the destination bus.
    :vartype path: str
    :ivar interface: The intended interface on the object path.
    :vartype interface: str
    :ivar member: The intended member on the interface.
    :vartype member: str
    :ivar message_type: The type of this message. A method call, signal, method return, or error.
    :vartype message_type: :class:`MessageType`
    :ivar flags: Flags that affect the behavior of this message.
    :vartype flags: :class:`MessageFlag`
    :ivar error_name: If this message is an error, the name of this error. Must be a valid interface name.
    :vartype error_name: str
    :ivar reply_serial: If this is a return type, the serial this message is in reply to.
    :vartype reply_serial: int
    :ivar sender: The address of the sender of this message. Will be a unique name.
    :vartype sender: str
    :ivar unix_fds: A list of unix fds that were sent in the header of this message.
    :vartype unix_fds: list(int)
    :ivar signature: The signature of the body of this message.
    :vartype signature: str
    :ivar signature_tree: The signature parsed as a signature tree.
    :vartype signature_tree: :class:`SignatureTree`
    :ivar body: The body of this message. Must match the signature.
    :vartype body: list(Any)
    :ivar serial: The serial of the message. Will be automatically set during message sending if not present. Use the ``new_serial()`` method of the bus to generate a serial.
    :vartype serial: int

    :raises:
        - :class:`InvalidMessageError` - If the message is malformed or missing fields for the message type.
        - :class:`InvalidSignatureError` - If the given signature is not valid.
        - :class:`InvalidObjectPathError` - If ``path`` is not a valid object path.
        - :class:`InvalidBusNameError` - If ``destination`` is not a valid bus name.
        - :class:`InvalidMemberNameError` - If ``member`` is not a valid member name.
        - :class:`InvalidInterfaceNameError` - If ``error_name`` or ``interface`` is not a valid interface name.
    """

    __slots__ = (
        "destination",
        "path",
        "interface",
        "member",
        "message_type",
        "flags",
        "error_name",
        "reply_serial",
        "sender",
        "unix_fds",
        "signature",
        "signature_tree",
        "body",
        "serial",
    )

    def __init__(
        self,
        destination: Optional[str] = None,
        path: Optional[str] = None,
        interface: Optional[str] = None,
        member: Optional[str] = None,
        message_type: MessageType = MESSAGE_TYPE_METHOD_CALL,
        flags: Union[MessageFlag, int] = MESSAGE_FLAG_NONE,
        error_name: Optional[Union[str, ErrorType]] = None,
        reply_serial: int = 0,
        sender: Optional[str] = None,
        unix_fds: List[int] = [],
        signature: Optional[Union[SignatureTree, str]] = None,
        body: List[Any] = [],
        serial: int = 0,
        validate: bool = True,
    ) -> None:
        self.destination = destination
        self.path = path
        self.interface = interface
        self.member = member
        self.message_type = message_type
        self.flags = flags if type(flags) is MESSAGE_FLAG else MESSAGE_FLAG(flags)
        self.error_name = (
            str(error_name.value) if type(error_name) is ErrorType else error_name
        )
        self.reply_serial = reply_serial or 0
        self.sender = sender
        self.unix_fds = unix_fds
        if type(signature) is SignatureTree:
            self.signature = signature.signature
            self.signature_tree = signature
        else:
            self.signature = signature or ""  # type: ignore[assignment]
            self.signature_tree = get_signature_tree(signature or "")
        self.body = body
        self.serial = serial or 0

        if not validate:
            return
        if self.destination is not None:
            assert_bus_name_valid(self.destination)
        if self.interface is not None:
            assert_interface_name_valid(self.interface)
        if self.path is not None:
            assert_object_path_valid(self.path)
        if self.member is not None:
            assert_member_name_valid(self.member)
        if self.error_name is not None:
            assert_interface_name_valid(self.error_name)  # type: ignore[arg-type]

        required_fields = REQUIRED_FIELDS.get(self.message_type.value)
        if not required_fields:
            raise InvalidMessageError(f"got unknown message type: {self.message_type}")
        for field in required_fields:
            if not getattr(self, field):
                raise InvalidMessageError(f"missing required field: {field}")

    def __repr__(self) -> str:
        """Return a string representation of this message."""
        return (
            f"<Message {self.message_type.name} "
            f"serial={self.serial} "
            f"reply_serial={self.reply_serial} "
            f"sender={self.sender} "
            f"destination={self.destination} "
            f"path={self.path} "
            f"interface={self.interface} "
            f"member={self.member} "
            f"error_name={self.error_name} "
            f"signature={self.signature} "
            f"body={self.body}>"
        )

    @staticmethod
    def new_error(
        msg: "Message", error_name: Union[str, ErrorType], error_text: str
    ) -> "Message":
        """A convenience constructor to create an error message in reply to the given message.

        :param msg: The message this error is in reply to.
        :type msg: :class:`Message`
        :param error_name: The name of this error. Must be a valid interface name.
        :type error_name: str
        :param error_text: Human-readable text for the error.

        :returns: The error message.
        :rtype: :class:`Message`

        :raises:
            - :class:`InvalidInterfaceNameError` - If the error_name is not a valid interface name.
        """
        return Message(
            message_type=MessageType.ERROR,
            reply_serial=msg.serial,
            destination=msg.sender,
            error_name=error_name,
            signature="s",
            body=[error_text],
        )

    @staticmethod
    def new_method_return(
        msg: "Message",
        signature: str = "",
        body: List[Any] = [],
        unix_fds: List[int] = [],
    ) -> "Message":
        """A convenience constructor to create a method return to the given method call message.

        :param msg: The method call message this is a reply to.
        :type msg: :class:`Message`
        :param signature: The signature for the message body.
        :type signature: str
        :param body: The body of this message. Must match the signature.
        :type body: list(Any)
        :param unix_fds: List integer file descriptors to send with this message.
        :type body: list(int)

        :returns: The method return message
        :rtype: :class:`Message`

        :raises:
            - :class:`InvalidSignatureError` - If the signature is not a valid signature.
        """
        return Message(
            message_type=MessageType.METHOD_RETURN,
            reply_serial=msg.serial,
            destination=msg.sender,
            signature=signature,
            body=body,
            unix_fds=unix_fds,
        )

    @staticmethod
    def new_signal(
        path: str,
        interface: str,
        member: str,
        signature: str = "",
        body: Optional[List[Any]] = None,
        unix_fds: Optional[List[int]] = None,
    ) -> "Message":
        """A convenience constructor to create a new signal message.

        :param path: The path of this signal.
        :type path: str
        :param interface: The interface of this signal.
        :type interface: str
        :param member: The member name of this signal.
        :type member: str
        :param signature: The signature of the signal body.
        :type signature: str
        :param body: The body of this signal message.
        :type body: list(Any)
        :param unix_fds: List integer file descriptors to send with this message.
        :type body: list(int)

        :returns: The signal message.
        :rtype: :class:`Message`

        :raises:
            - :class:`InvalidSignatureError` - If the signature is not a valid signature.
            - :class:`InvalidObjectPathError` - If ``path`` is not a valid object path.
            - :class:`InvalidInterfaceNameError` - If ``interface`` is not a valid interface name.
            - :class:`InvalidMemberNameError` - If ``member`` is not a valid member name.
        """
        return Message(
            message_type=MessageType.SIGNAL,
            interface=interface,
            path=path,
            member=member,
            signature=signature,
            body=body or [],
            unix_fds=unix_fds or [],
        )

    def _marshall(self, negotiate_unix_fd: bool) -> bytearray:
        """Marshall this message into a byte array."""
        # TODO maximum message size is 134217728 (128 MiB)
        body_block = Marshaller(self.signature, self.body)
        body_buffer = body_block._marshall()

        fields = []

        # No verify here since the marshaller will raise an exception if the
        # Variant is invalid.

        if self.path:
            fields.append([HEADER_PATH, Variant("o", self.path, False)])
        if self.interface:
            fields.append([HEADER_INTERFACE, Variant("s", self.interface, False)])
        if self.member:
            fields.append([HEADER_MEMBER, Variant("s", self.member, False)])
        if self.error_name:
            fields.append([HEADER_ERROR_NAME, Variant("s", self.error_name, False)])
        if self.reply_serial:
            fields.append([HEADER_REPLY_SERIAL, Variant("u", self.reply_serial, False)])
        if self.destination:
            fields.append([HEADER_DESTINATION, Variant("s", self.destination, False)])
        if self.signature:
            fields.append([HEADER_SIGNATURE, Variant("g", self.signature, False)])
        if self.unix_fds and negotiate_unix_fd:
            fields.append([HEADER_UNIX_FDS, Variant("u", len(self.unix_fds), False)])

        header_body = [
            LITTLE_ENDIAN,
            self.message_type.value,
            self.flags.value,
            PROTOCOL_VERSION,
            len(body_buffer),
            self.serial,
            fields,
        ]
        header_block = Marshaller("yyyyuua(yv)", header_body)
        header_block._marshall()
        header_block._align(8)
        header_buffer = header_block._buffer()
        return header_buffer + body_buffer
