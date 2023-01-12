"""Helper constants."""
# pylint: disable=missing-class-docstring
import sys

if sys.version_info.minor >= 11:
    # Needs Python 3.11
    from enum import StrEnum  # # pylint: disable=no-name-in-module
else:
    try:
        # https://github.com/home-assistant/core/blob/dev/homeassistant/backports/enum.py
        # Considered internal to Home Assistant, can be removed whenever.
        from homeassistant.backports.enum import StrEnum
    except ImportError:
        from enum import Enum

        class StrEnum(str, Enum):
            pass


class HacsGitHubRepo(StrEnum):
    """HacsGitHubRepo."""

    DEFAULT = "hacs/default"
    INTEGRATION = "hacs/integration"


class HacsCategory(StrEnum):
    APPDAEMON = "appdaemon"
    INTEGRATION = "integration"
    LOVELACE = "lovelace"
    PLUGIN = "plugin"  # Kept for legacy purposes
    NETDAEMON = "netdaemon"
    PYTHON_SCRIPT = "python_script"
    THEME = "theme"
    REMOVED = "removed"

    def __str__(self):
        return str(self.value)


class HacsDispatchEvent(StrEnum):
    """HacsDispatchEvent."""

    CONFIG = "hacs_dispatch_config"
    ERROR = "hacs_dispatch_error"
    RELOAD = "hacs_dispatch_reload"
    REPOSITORY = "hacs_dispatch_repository"
    REPOSITORY_DOWNLOAD_PROGRESS = "hacs_dispatch_repository_download_progress"
    STAGE = "hacs_dispatch_stage"
    STARTUP = "hacs_dispatch_startup"
    STATUS = "hacs_dispatch_status"


class RepositoryFile(StrEnum):
    """Repository file names."""

    HACS_JSON = "hacs.json"
    MAINIFEST_JSON = "manifest.json"


class ConfigurationType(StrEnum):
    YAML = "yaml"
    CONFIG_ENTRY = "config_entry"


class LovelaceMode(StrEnum):
    """Lovelace Modes."""

    STORAGE = "storage"
    AUTO = "auto"
    AUTO_GEN = "auto-gen"
    YAML = "yaml"


class HacsStage(StrEnum):
    SETUP = "setup"
    STARTUP = "startup"
    WAITING = "waiting"
    RUNNING = "running"
    BACKGROUND = "background"


class HacsDisabledReason(StrEnum):
    RATE_LIMIT = "rate_limit"
    REMOVED = "removed"
    INVALID_TOKEN = "invalid_token"
    CONSTRAINS = "constrains"
    LOAD_HACS = "load_hacs"
    RESTORE = "restore"
