"""Models for root APIs."""

from dataclasses import dataclass
from enum import StrEnum

from .base import ResponseData

# --- ENUMS ----


class HostFeature(StrEnum):
    """HostFeature type.

    This is an incomplete list. Supervisor regularly adds support for new host
    features as users request them. Therefore when returning a list of host
    features, there may be some which are not in this list parsed as strings on
    older versions of the client.
    """

    DISK = "disk"
    HAOS = "haos"
    HOSTNAME = "hostname"
    JOURNAL = "journal"
    MOUNT = "mount"
    NETWORK = "network"
    OS_AGENT = "os_agent"
    REBOOT = "reboot"
    RESOLVED = "resolved"
    SERVICES = "services"
    SHUTDOWN = "shutdown"
    TIMEDATE = "timedate"


class SupervisorState(StrEnum):
    """SupervisorState type."""

    INITIALIZE = "initialize"
    SETUP = "setup"
    STARTUP = "startup"
    RUNNING = "running"
    FREEZE = "freeze"
    SHUTDOWN = "shutdown"
    STOPPING = "stopping"
    CLOSE = "close"


class UpdateChannel(StrEnum):
    """UpdateChannel type."""

    STABLE = "stable"
    BETA = "beta"
    DEV = "dev"


class LogLevel(StrEnum):
    """LogLevel type."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class UpdateType(StrEnum):
    """UpdateType type."""

    ADDON = "addon"
    CORE = "core"
    OS = "os"
    SUPERVISOR = "supervisor"


# --- OBJECTS ----


@dataclass(frozen=True, slots=True)
class RootInfo(ResponseData):
    """Root info object."""

    supervisor: str
    homeassistant: str | None
    hassos: str | None
    docker: str
    hostname: str | None
    operating_system: str | None
    features: list[HostFeature | str]
    machine: str | None
    arch: str
    state: SupervisorState
    supported_arch: list[str]
    supported: bool
    channel: UpdateChannel
    logging: LogLevel
    timezone: str


@dataclass(frozen=True, slots=True)
class AvailableUpdate(ResponseData):
    """AvailableUpdate type."""

    update_type: UpdateType
    panel_path: str
    version_latest: str
    name: str | None = None
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class AvailableUpdates(ResponseData):
    """AvailableUpdates type."""

    available_updates: list[AvailableUpdate]
