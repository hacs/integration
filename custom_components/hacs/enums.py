"""Helper constants."""
# pylint: disable=missing-class-docstring
from enum import Enum


class HacsGitHubRepo(str, Enum):
    """HacsGitHubRepo."""

    DEFAULT = "hacs/default"
    INTEGRATION = "hacs/integration"


class HacsCategory(str, Enum):
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


class RepositoryFile(str, Enum):
    """Repository file names."""

    HACS_JSON = "hacs.json"
    MAINIFEST_JSON = "manifest.json"


class ConfigurationType(str, Enum):
    YAML = "yaml"
    CONFIG_ENTRY = "config_entry"


class LovelaceMode(str, Enum):
    """Lovelace Modes."""

    STORAGE = "storage"
    AUTO = "auto"
    AUTO_GEN = "auto-gen"
    YAML = "yaml"


class HacsStage(str, Enum):
    SETUP = "setup"
    STARTUP = "startup"
    WAITING = "waiting"
    RUNNING = "running"
    BACKGROUND = "background"


class HacsDisabledReason(str, Enum):
    RATE_LIMIT = "rate_limit"
    REMOVED = "removed"
    INVALID_TOKEN = "invalid_token"
    CONSTRAINS = "constrains"
    LOAD_HACS = "load_hacs"
    RESTORE = "restore"
