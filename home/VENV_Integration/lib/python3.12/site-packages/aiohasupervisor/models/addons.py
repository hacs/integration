"""Models for Supervisor addons."""

from abc import ABC
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mashumaro import field_options

from .base import DEFAULT, Options, Request, RequestConfig, ResponseData

# --- ENUMS ----


class AddonStage(StrEnum):
    """AddonStage type."""

    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class AddonBootConfig(StrEnum):
    """AddonBootConfig type."""

    AUTO = "auto"
    MANUAL = "manual"
    MANUAL_ONLY = "manual_only"


class AddonBoot(StrEnum):
    """AddonBoot type."""

    AUTO = "auto"
    MANUAL = "manual"


class CpuArch(StrEnum):
    """CpuArch type."""

    ARMV7 = "armv7"
    ARMHF = "armhf"
    AARCH64 = "aarch64"
    I386 = "i386"
    AMD64 = "amd64"


class Capability(StrEnum):
    """Capability type.

    This is an incomplete list. Supervisor regularly adds support for new
    privileged capabilities as addon developers request them. Therefore
    when returning a list of capabilities, there may be some which are not in
    this list parsed as strings on older versions of the client.
    """

    BPF = "BPF"
    DAC_READ_SEARCH = "DAC_READ_SEARCH"
    IPC_LOCK = "IPC_LOCK"
    NET_ADMIN = "NET_ADMIN"
    NET_RAW = "NET_RAW"
    PERFMON = "PERFMON"
    SYS_ADMIN = "SYS_ADMIN"
    SYS_MODULE = "SYS_MODULE"
    SYS_NICE = "SYS_NICE"
    SYS_PTRACE = "SYS_PTRACE"
    SYS_RAWIO = "SYS_RAWIO"
    SYS_RESOURCE = "SYS_RESOURCE"
    SYS_TIME = "SYS_TIME"


class AppArmor(StrEnum):
    """AppArmor type."""

    DEFAULT = "default"
    DISABLE = "disable"
    PROFILE = "profile"


class SupervisorRole(StrEnum):
    """SupervisorRole type."""

    ADMIN = "admin"
    BACKUP = "backup"
    DEFAULT = "default"
    HOMEASSISTANT = "homeassistant"
    MANAGER = "manager"


class AddonState(StrEnum):
    """AddonState type."""

    STARTUP = "startup"
    STARTED = "started"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    ERROR = "error"


# --- OBJECTS ----


@dataclass(frozen=True)
class AddonInfoBaseFields(ABC):
    """AddonInfoBaseFields ABC type."""

    advanced: bool
    available: bool
    build: bool
    description: str
    homeassistant: str | None
    icon: bool
    logo: bool
    name: str
    repository: str
    slug: str
    stage: AddonStage
    update_available: bool
    url: str | None
    version_latest: str
    version: str | None


@dataclass(frozen=True)
class AddonInfoStoreBaseFields(ABC):
    """AddonInfoAllStoreFields ABC type."""

    arch: list[CpuArch]
    documentation: bool


@dataclass(frozen=True)
class AddonInfoStoreExtFields(ABC):
    """AddonInfoStoreExtFields ABC type."""

    apparmor: AppArmor
    auth_api: bool
    docker_api: bool
    full_access: bool
    homeassistant_api: bool
    host_network: bool
    host_pid: bool
    ingress: bool
    long_description: str | None
    rating: int
    signed: bool

    # Hassio is deprecated name for supervisor
    supervisor_api: bool = field(metadata=field_options(alias="hassio_api"))
    supervisor_role: SupervisorRole = field(
        metadata=field_options(alias="hassio_role"),
    )


@dataclass(frozen=True)
class AddonInfoStoreExtInstalledBaseFields(ABC):
    """AddonInfoStoreExtInstalledBaseFields ABC type."""

    detached: bool


@dataclass(frozen=True, slots=True)
class StoreAddon(AddonInfoBaseFields, AddonInfoStoreBaseFields, ResponseData):
    """StoreAddon type."""

    installed: bool


@dataclass(frozen=True, slots=True)
class StoreAddonComplete(
    AddonInfoBaseFields,
    AddonInfoStoreBaseFields,
    AddonInfoStoreExtFields,
    AddonInfoStoreExtInstalledBaseFields,
    ResponseData,
):
    """StoreAddonComplete type."""

    installed: bool


@dataclass(frozen=True, slots=True)
class InstalledAddon(
    AddonInfoBaseFields,
    AddonInfoStoreExtInstalledBaseFields,
    ResponseData,
):
    """InstalledAddon type."""

    state: AddonState


@dataclass(frozen=True, slots=True)
class InstalledAddonComplete(
    AddonInfoBaseFields,
    AddonInfoStoreExtInstalledBaseFields,
    AddonInfoStoreBaseFields,
    AddonInfoStoreExtFields,
    ResponseData,
):
    """InstalledAddonComplete model."""

    state: AddonState
    hostname: str
    dns: list[str]
    protected: bool
    boot: AddonBoot
    boot_config: AddonBootConfig
    options: dict[str, Any]
    schema: list[dict[str, Any]] | None
    machine: list[str]
    network: dict[str, int | None] | None
    network_description: dict[str, str] | None
    host_ipc: bool
    host_uts: bool
    host_dbus: bool
    privileged: list[Capability | str]
    changelog: bool
    stdin: bool
    gpio: bool
    usb: bool
    uart: bool
    kernel_modules: bool
    devicetree: bool
    udev: bool
    video: bool
    audio: bool
    services: list[str]
    discovery: list[str]
    translations: dict[str, Any]
    webui: str | None
    ingress_entry: str | None
    ingress_url: str | None
    ingress_port: int | None
    ingress_panel: bool | None
    audio_input: str | None
    audio_output: str | None
    auto_update: bool
    ip_address: bool
    watchdog: bool
    devices: list[str]


@dataclass(frozen=True, slots=True)
class AddonsList(ResponseData):
    """AddonsList model."""

    addons: list[InstalledAddon]


@dataclass(frozen=True, slots=True)
class AddonsOptions(Options):
    """AddonsOptions model."""

    # Options term is used to reference both general options and addon-specific config
    # Therefore this field is config to match UI rather then Supervisor's API
    config: dict[str, Any] | None = field(  # type: ignore[assignment]
        default=DEFAULT,
        metadata=field_options(alias="options"),
    )
    boot: AddonBoot | None = None
    auto_update: bool | None = None
    network: dict[str, int | None] | None = DEFAULT  # type: ignore[assignment]
    audio_input: str | None = DEFAULT  # type: ignore[assignment]
    audio_output: str | None = DEFAULT  # type: ignore[assignment]
    ingress_panel: bool | None = None
    watchdog: bool | None = None

    class Config(RequestConfig):
        """Mashumaro config options."""

        serialize_by_alias = True


@dataclass(frozen=True, slots=True)
class AddonsConfigValidate(ResponseData):
    """AddonsConfigValidate model."""

    message: str
    valid: bool
    pwned: bool | None


@dataclass(frozen=True, slots=True)
class AddonsSecurityOptions(Options):
    """AddonsSecurityOptions model."""

    protected: bool | None = None


@dataclass(frozen=True, slots=True)
class AddonsStats(ResponseData):
    """AddonsStats model."""

    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_rx: int
    network_tx: int
    blk_read: int
    blk_write: int


@dataclass(frozen=True, slots=True)
class AddonsUninstall(Request):
    """AddonsUninstall model."""

    remove_config: bool | None = None


@dataclass(frozen=True, slots=True)
class Repository(ResponseData):
    """Repository model."""

    slug: str
    name: str
    source: str
    url: str
    maintainer: str


@dataclass(frozen=True, slots=True)
class StoreAddonsList(ResponseData):
    """StoreAddonsList model."""

    addons: list[StoreAddon]


@dataclass(frozen=True, slots=True)
class StoreInfo(StoreAddonsList, ResponseData):
    """StoreInfo model."""

    repositories: list[Repository]


@dataclass(frozen=True, slots=True)
class StoreAddonUpdate(Request):
    """StoreAddonUpdate model."""

    backup: bool | None = None


@dataclass(frozen=True, slots=True)
class StoreAddRepository(Request):
    """StoreAddRepository model."""

    repository: str
