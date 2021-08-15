"""Backup."""
import os
import shutil
import tempfile
from time import sleep

from custom_components.hacs.helpers.functions.is_safe_to_remove import is_safe_to_remove
from custom_components.hacs.utils.logger import getLogger

BACKUP_PATH = tempfile.gettempdir() + "/hacs_backup/"

_LOGGER = getLogger()


class Backup:
    """Backup."""

    def __init__(self, local_path, backup_path=BACKUP_PATH):
        """initialize."""
        self.local_path = local_path
        self.backup_path = backup_path
        self.backup_path_full = f"{self.backup_path}{self.local_path.split('/')[-1]}"

    def create(self):
        """Create a backup in /tmp"""
        if not os.path.exists(self.local_path):
            return
        if not is_safe_to_remove(self.local_path):
            return
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
            while os.path.exists(self.backup_path):
                sleep(0.1)
        os.makedirs(self.backup_path, exist_ok=True)

        try:
            if os.path.isfile(self.local_path):
                shutil.copyfile(self.local_path, self.backup_path_full)
                os.remove(self.local_path)
            else:
                shutil.copytree(self.local_path, self.backup_path_full)
                shutil.rmtree(self.local_path)
                while os.path.exists(self.local_path):
                    sleep(0.1)
            _LOGGER.debug(
                "Backup for %s, created in %s",
                self.local_path,
                self.backup_path_full,
            )
        except (Exception, BaseException):  # pylint: disable=broad-except
            pass

    def restore(self):
        """Restore from backup."""
        if not os.path.exists(self.backup_path_full):
            return

        if os.path.isfile(self.backup_path_full):
            if os.path.exists(self.local_path):
                os.remove(self.local_path)
            shutil.copyfile(self.backup_path_full, self.local_path)
        else:
            if os.path.exists(self.local_path):
                shutil.rmtree(self.local_path)
                while os.path.exists(self.local_path):
                    sleep(0.1)
            shutil.copytree(self.backup_path_full, self.local_path)
        _LOGGER.debug(
            "Restored %s, from backup %s", self.local_path, self.backup_path_full
        )

    def cleanup(self):
        """Cleanup backup files."""
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
            while os.path.exists(self.backup_path):
                sleep(0.1)
            _LOGGER.debug("Backup dir %s cleared", self.backup_path)


class BackupNetDaemon:
    """BackupNetDaemon."""

    def __init__(self, repository):
        """Initialize."""
        self.repository = repository
        self.backup_path = (
            tempfile.gettempdir() + "/hacs_persistent_netdaemon/" + repository.data.name
        )

    def create(self):
        """Create a backup in /tmp"""
        if not is_safe_to_remove(self.repository.content.path.local):
            return
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
            while os.path.exists(self.backup_path):
                sleep(0.1)
        os.makedirs(self.backup_path, exist_ok=True)

        for filename in os.listdir(self.repository.content.path.local):
            if filename.endswith(".yaml"):
                source_file_name = f"{self.repository.content.path.local}/{filename}"
                target_file_name = f"{self.backup_path}/{filename}"
                shutil.copyfile(source_file_name, target_file_name)

    def restore(self):
        """Create a backup in /tmp"""
        if os.path.exists(self.backup_path):
            for filename in os.listdir(self.backup_path):
                if filename.endswith(".yaml"):
                    source_file_name = f"{self.backup_path}/{filename}"
                    target_file_name = (
                        f"{self.repository.content.path.local}/{filename}"
                    )
                    shutil.copyfile(source_file_name, target_file_name)

    def cleanup(self):
        """Create a backup in /tmp"""
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
            while os.path.exists(self.backup_path):
                sleep(0.1)
            _LOGGER.debug("Backup dir %s cleared", self.backup_path)
