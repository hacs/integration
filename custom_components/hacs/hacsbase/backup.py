"""Backup."""
import os
from time import sleep
from shutil import copy2, rmtree
from distutils.dir_util import copy_tree

from integrationhelper import Logger


class Backup:
    """Backup."""

    def __init__(self, local_path):
        """initialize."""
        self.logger = Logger("hacs.backup")
        self.local_path = local_path
        self.backup_path = "/tmp/hacs_backup"

    def create(self):
        """Create a backup in /tmp"""
        if os.path.exists(self.backup_path):
            rmtree(self.backup_path)
            while os.path.exists(self.backup_path):
                sleep(0.1)
        os.makedirs(self.backup_path, exist_ok=True)

        try:
            if os.path.isfile(self.local_path):
                copy2(self.local_path, self.backup_path)
                os.remove(self.local_path)
            else:
                copy_tree(self.local_path, self.backup_path)
                rmtree(self.local_path)
                while os.path.exists(self.local_path):
                    sleep(0.1)
            self.logger.debug(
                f"Backup for {self.local_path}, created in {self.backup_path}"
            )
        except Exception:  # pylint: disable=broad-except
            pass

    def restore(self):
        """Restore from backup."""
        if os.path.isfile(self.local_path):
            os.remove(self.local_path)
        else:
            rmtree(self.local_path)
            while os.path.exists(self.local_path):
                sleep(0.1)
        copy2(self.backup_path, self.local_path)
        self.logger.debug(f"Restored {self.local_path}, from backup {self.backup_path}")

    def cleanup(self):
        """Cleanup backup files."""
        rmtree(self.backup_path)
        while os.path.exists(self.backup_path):
            sleep(0.1)
        self.logger.debug(f"Backup dir {self.backup_path} cleared")
