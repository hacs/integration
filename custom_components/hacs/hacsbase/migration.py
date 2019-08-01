"""HACS Migration logic."""
# pylint: disable=broad-except,no-member
import json
from shutil import copy2

from integrationhelper import Logger, Validate

from . import Hacs
from .const import STORAGE_VERSION, STORENAME


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
        old_data = self.data.read()

        if not old_data or old_data.get("hacs", {}).get("schema") is None:
            # new install.
            pass

        if old_data.get("hacs", {}).get("schema") == STORAGE_VERSION:
            # Newest version, no need to do anything.
            return

        current = old_data.get("hacs", {}).get("schema")

        for version in range(current, STORAGE_VERSION + 1):
            if version in MIGRATIONS:
                MIGRATIONS[version](current).migrate()
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
        destination = f"{self.source}.{self.from_version - 1}"
        self.logger.info(f"Backing up current file to '{destination}'")
        copy2(self.source, destination)

    def save(self):
        """Save the content."""
        datastore = f"{self.system.config_path}/.storage/{STORENAME}"

        try:
            with open(
                datastore, mode="w", encoding="utf-8", errors="ignore"
            ) as outfile:
                outfile.write(json.dumps(self.old_data, indent=4))

        except Exception as error:  # Gotta Catch 'Em All
            self.logger.error(f"Could not write data to {datastore} - {error}")


@register
class FromVersion4(Migration):
    """Migrate from version 4"""

    from_version = 4

    def migrate(self):
        """Start migration."""
        self.logger.info(f"Starting migration from {self.from_version}")
        for repository in self.old_data:
            if not self.old_data[repository]["installed"]:
                self.old_data[repository]["show_beta"] = False
