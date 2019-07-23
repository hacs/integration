"""Backup."""
import os
from shutil import copy2


class Backup:
    """Backup."""

    def __init__(self, local_path):
        """initialize."""
        self.local_path = local_path
        self.backup_path = "/tmp/hacs_backup"

    def create(self):
        """Create a backup in /tmp"""
        if os.path.exists(self.backup_path):
            os.removedirs(self.backup_path)
        os.makedirs(self.backup_path, exist_ok=True)

        copy2(self.local_path, self.backup_path)

    def restore(self):
        """Restore from backup."""
        if os.path.isfile(self.local_path):
            os.remove(self.local_path)
        else:
            os.removedirs(self.local_path)
        copy2(self.backup_path, self.local_path)

    def cleanup(self):
        """Cleanup backup files."""
        os.removedirs(self.backup_path)
