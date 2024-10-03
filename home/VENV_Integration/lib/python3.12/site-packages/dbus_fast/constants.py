from enum import Enum, IntFlag


class BusType(Enum):
    """An enum that indicates a type of bus. On most systems, there are
    normally two different kinds of buses running.
    """

    SESSION = 1  #: A bus for the current graphical user session.
    SYSTEM = 2  #: A persistent bus for the whole machine.


class MessageType(Enum):
    """An enum that indicates a type of message."""

    METHOD_CALL = 1  #: An outgoing method call.
    METHOD_RETURN = 2  #: A return to a previously sent method call
    ERROR = 3  #: A return to a method call that has failed
    SIGNAL = 4  #: A broadcast signal to subscribed connections


MESSAGE_TYPE_MAP = {field.value: field for field in MessageType}


class MessageFlag(IntFlag):
    """Flags that affect the behavior of sent and received messages"""

    NONE = 0
    NO_REPLY_EXPECTED = 1  #: The method call does not expect a method return.
    NO_AUTOSTART = 2
    ALLOW_INTERACTIVE_AUTHORIZATION = 4


# This is written out because of https://github.com/python/cpython/issues/98976
MESSAGE_FLAG_MAP = {
    0: MessageFlag.NONE,
    1: MessageFlag.NO_REPLY_EXPECTED,
    2: MessageFlag.NO_AUTOSTART,
    4: MessageFlag.ALLOW_INTERACTIVE_AUTHORIZATION,
}


class NameFlag(IntFlag):
    """A flag that affects the behavior of a name request."""

    NONE = 0
    ALLOW_REPLACEMENT = 1  #: If another client requests this name, let them have it.
    REPLACE_EXISTING = 2  #: If another client owns this name, try to take it.
    DO_NOT_QUEUE = 4  #: Name requests normally queue and wait for the owner to release the name. Do not enter this queue.


class RequestNameReply(Enum):
    """An enum that describes the result of a name request."""

    PRIMARY_OWNER = 1  #: The bus owns the name.
    IN_QUEUE = 2  #: The bus is in a queue and may receive the name after it is relased by the primary owner.
    EXISTS = 3  #: The name has an owner and NameFlag.DO_NOT_QUEUE was given.
    ALREADY_OWNER = 4  #: The bus already owns the name.


class ReleaseNameReply(Enum):
    """An enum that describes the result of a name release request"""

    RELEASED = 1
    NON_EXISTENT = 2
    NOT_OWNER = 3


class PropertyAccess(Enum):
    """An enum that describes whether a DBus property can be gotten or set with
    the ``org.freedesktop.DBus.Properties`` interface.
    """

    READ = "read"  #: The property is readonly.
    WRITE = "write"  #: The property is writeonly.
    READWRITE = "readwrite"  #: The property can be read or written to.

    def readable(self) -> bool:
        """Get whether the property can be read."""
        return self == PropertyAccess.READ or self == PropertyAccess.READWRITE

    def writable(self) -> bool:
        """Get whether the property can be written to."""
        return self == PropertyAccess.WRITE or self == PropertyAccess.READWRITE


class ArgDirection(Enum):
    """For an introspected argument, indicates whether it is an input parameter or a return value."""

    IN = "in"
    OUT = "out"


class ErrorType(str, Enum):
    """An enum for the type of an error for a message reply.

    :seealso: http://man7.org/linux/man-pages/man3/sd-bus-errors.3.html
    """

    SERVICE_ERROR = "com.dubstepdish.dbus.next.ServiceError"  #: A custom error to indicate an exported service threw an exception.
    INTERNAL_ERROR = "com.dubstepdish.dbus.next.InternalError"  #: A custom error to indicate something went wrong with the library.
    CLIENT_ERROR = "com.dubstepdish.dbus.next.ClientError"  #: A custom error to indicate something went wrong with the client.

    FAILED = "org.freedesktop.DBus.Error.Failed"
    NO_MEMORY = "org.freedesktop.DBus.Error.NoMemory"
    SERVICE_UNKNOWN = "org.freedesktop.DBus.Error.ServiceUnknown"
    NAME_HAS_NO_OWNER = "org.freedesktop.DBus.Error.NameHasNoOwner"
    NO_REPLY = "org.freedesktop.DBus.Error.NoReply"
    IO_ERROR = "org.freedesktop.DBus.Error.IOError"
    BAD_ADDRESS = "org.freedesktop.DBus.Error.BadAddress"
    NOT_SUPPORTED = "org.freedesktop.DBus.Error.NotSupported"
    LIMITS_EXCEEDED = "org.freedesktop.DBus.Error.LimitsExceeded"
    ACCESS_DENIED = "org.freedesktop.DBus.Error.AccessDenied"
    AUTH_FAILED = "org.freedesktop.DBus.Error.AuthFailed"
    NO_SERVER = "org.freedesktop.DBus.Error.NoServer"
    TIMEOUT = "org.freedesktop.DBus.Error.Timeout"
    NO_NETWORK = "org.freedesktop.DBus.Error.NoNetwork"
    ADDRESS_IN_USE = "org.freedesktop.DBus.Error.AddressInUse"
    DISCONNECTED = "org.freedesktop.DBus.Error.Disconnected"
    INVALID_ARGS = "org.freedesktop.DBus.Error.InvalidArgs"
    FILE_NOT_FOUND = "org.freedesktop.DBus.Error.FileNotFound"
    FILE_EXISTS = "org.freedesktop.DBus.Error.FileExists"
    UNKNOWN_METHOD = "org.freedesktop.DBus.Error.UnknownMethod"
    UNKNOWN_OBJECT = "org.freedesktop.DBus.Error.UnknownObject"
    UNKNOWN_INTERFACE = "org.freedesktop.DBus.Error.UnknownInterface"
    UNKNOWN_PROPERTY = "org.freedesktop.DBus.Error.UnknownProperty"
    PROPERTY_READ_ONLY = "org.freedesktop.DBus.Error.PropertyReadOnly"
    UNIX_PROCESS_ID_UNKNOWN = "org.freedesktop.DBus.Error.UnixProcessIdUnknown"
    INVALID_SIGNATURE = "org.freedesktop.DBus.Error.InvalidSignature"
    INCONSISTENT_MESSAGE = "org.freedesktop.DBus.Error.InconsistentMessage"
    MATCH_RULE_NOT_FOUND = "org.freedesktop.DBus.Error.MatchRuleNotFound"
    MATCH_RULE_INVALID = "org.freedesktop.DBus.Error.MatchRuleInvalid"
    INTERACTIVE_AUTHORIZATION_REQUIRED = (
        "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired"
    )
