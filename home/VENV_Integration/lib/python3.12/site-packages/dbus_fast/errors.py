from typing import Optional, Union


class SignatureBodyMismatchError(ValueError):
    pass


class InvalidSignatureError(ValueError):
    pass


class InvalidAddressError(ValueError):
    pass


class AuthError(Exception):
    pass


class InvalidMessageError(ValueError):
    pass


class InvalidIntrospectionError(ValueError):
    pass


class InterfaceNotFoundError(Exception):
    pass


class SignalDisabledError(Exception):
    pass


class InvalidBusNameError(TypeError):
    def __init__(self, name: str) -> None:
        super().__init__(f"invalid bus name: {name}")


class InvalidObjectPathError(TypeError):
    def __init__(self, path: str) -> None:
        super().__init__(f"invalid object path: {path}")


class InvalidInterfaceNameError(TypeError):
    def __init__(self, name: str) -> None:
        super().__init__(f"invalid interface name: {name}")


class InvalidMemberNameError(TypeError):
    def __init__(self, member: str) -> None:
        super().__init__(f"invalid member name: {member}")


from .constants import ErrorType, MessageType
from .message import Message
from .validators import assert_interface_name_valid


class DBusError(Exception):
    def __init__(
        self, type_: Union[ErrorType, str], text: str, reply: Optional[Message] = None
    ) -> None:
        super().__init__(text)

        if type(type_) is ErrorType:
            type_ = type_.value

        assert_interface_name_valid(type_)  # type: ignore[arg-type]
        if reply is not None and type(reply) is not Message:
            raise TypeError("reply must be of type Message")

        self.type = type_
        self.text = text
        self.reply = reply

    @staticmethod
    def _from_message(msg: Message) -> "DBusError":
        assert msg.message_type == MessageType.ERROR
        return DBusError(msg.error_name or "unknown", msg.body[0], reply=msg)

    def _as_message(self, msg: Message) -> Message:
        return Message.new_error(msg, self.type, self.text)
