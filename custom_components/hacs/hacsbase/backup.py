"""Backup."""
import os
import shutil
from time import sleep

from integrationhelper import Logger

BACKUP_PATH = "/tmp/hacs_backup/"


class Backup:
    """Backup."""

    def __init__(self, local_path):
        """initialize."""
        self.logger = Logger("hacs.backup")
        self.local_path = local_path
        self.backup_path = f"{BACKUP_PATH}{self.local_path.split('/')[-1]}"

    def create(self):
        """Create a backup in /tmp"""
        if not os.path.exists(self.local_path):
            return
        if os.path.exists(BACKUP_PATH):
            shutil.rmtree(BACKUP_PATH)
            while os.path.exists(BACKUP_PATH):
                sleep(0.1)
        os.makedirs(BACKUP_PATH, exist_ok=True)

        try:
            if os.path.isfile(self.local_path):
                shutil.copyfile(self.local_path, self.backup_path)
                os.remove(self.local_path)
            else:
                shutil.copytree(self.local_path, self.backup_path)
                shutil.rmtree(self.local_path)
                while os.path.exists(self.local_path):
                    sleep(0.1)
            self.logger.debug(
                f"Backup for {self.local_path}, created in {self.backup_path}"
            )
        except Exception:  # pylint: disable=broad-except
            pass

    def restore(self):
        """Restore from backup."""
        if not os.path.exists(self.local_path):
            return
        if not os.path.exists(self.backup_path):
            return

        if os.path.isfile(self.local_path):
            os.remove(self.local_path)
            shutil.copyfile(self.backup_path, self.local_path)
        else:
            shutil.rmtree(self.local_path)
            while os.path.exists(self.local_path):
                sleep(0.1)
            shutil.copytree(self.backup_path, self.local_path)
        self.logger.debug(f"Restored {self.local_path}, from backup {self.backup_path}")

    def cleanup(self):
        """Cleanup backup files."""
        if os.path.exists(BACKUP_PATH):
            shutil.rmtree(BACKUP_PATH)
            while os.path.exists(BACKUP_PATH):
                sleep(0.1)
            self.logger.debug(f"Backup dir {BACKUP_PATH} cleared")
