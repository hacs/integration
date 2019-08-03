"""HACS Migration logic."""
# pylint: disable=broad-except,no-member
import json
from shutil import copy2

from integrationhelper import Logger, Validate

from . import Hacs
from .data import save, STORES
from .const import STORAGE_VERSION


MIGRATIONS = {}


def register(cls):
    """Register steps."""
    MIGRATIONS[cls.from_version] = cls
    return cls


class ValidateData(Hacs):
    """Validate."""

    def validate_local_data_file(self):
        """Validate content."""
        validate = Validate()
        old_data = self.data.read("old")

        if old_data is None:
            # new install.
            return True

        if old_data.get("hacs", {}).get("schema") is None:
            return True

        if old_data.get("hacs", {}).get("schema") == STORAGE_VERSION:
            # Newest version, no need to do anything.
            return

        current = old_data.get("hacs", {}).get("schema")

        for version in range(int(current), int(STORAGE_VERSION)):
            if current in MIGRATIONS:
                MIGRATIONS[current](old_data).migrate()
            else:
                validate.errors.append(f"Missing migration step for {version}")

        if validate.errors:
            for error in validate.errors:
                self.logger.critical(error)
        return validate.success


class Migration(Hacs):
    """Hacs migrations"""

    def __init__(self, old_data=None):
        """initialize migration."""
        self.old_data = old_data
        self.logger = Logger("hacs.migration")
        self.source = f"{self.system.config_path}/.storage/hacs"
        self.cleanup()
        self.backup()

    def cleanup(self):
        """Remove files no longer in use."""

    def backup(self):
        """Back up old file."""
        destination = f"{self.source}.{self.from_version}"
        self.logger.info(f"Backing up current file to '{destination}'")
        copy2(self.source, destination)


@register
class FromVersion4(Migration):
    """Migrate from version 4"""

    from_version = "4"

    def migrate(self):
        """Start migration."""
        self.logger.info(f"Starting migration from {self.from_version}")
        hacs = self.old_data["hacs"]
        repositories = self.old_data["repositories"]
        installed = {}

        for repository in repositories:
            repository = repositories[repository]
            repository["full_name"] = repository["repository_name"]
            repository["category"] = repository["repository_type"]
            if not repository["installed"]:
                repository["show_beta"] = False
            else:
                if repository["version_installed"] is not None:
                    version_type = "version"
                    version_installed = repository["version_installed"]
                    version_available = repository["last_release_tag"]
                else:
                    version_type = "commit"
                    version_installed = repository["installed_commit"]
                    version_available = repository["last_commit"]
                if repository["full_name"] != "custom-components/hacs":
                    installed[repository["repository_name"]] = {
                        "version_type": str(version_type),
                        "version_installed": str(version_installed),
                        "version_available": str(version_available),
                    }

        path = f"{self.system.config_path}/.storage/{STORES['hacs']}"
        save(path, hacs)

        path = f"{self.system.config_path}/.storage/{STORES['repositories']}"
        save(path, repositories)

        path = f"{self.system.config_path}/.storage/{STORES['installed']}"
        save(path, installed)
        self.logger.info("Migration done")
