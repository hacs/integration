"""Backup."""
import os


class Backup:
    """Backup."""

    def __init__(self, local_path):
        """initialize."""
        self.local_path = local_path
        self.backup_path = "/tmp/hacs_backup"

    def create(self):
        """Create a backup in /tmp"""
        if not os.path.exists(self.backup_path):
            os.makedirs(self.backup_path, exist_ok=True)

    def restore(self):
        """Restore from backup."""

    def cleanup(self):
        """Cleanup backup files."""
