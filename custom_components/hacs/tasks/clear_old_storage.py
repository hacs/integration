"""Starting setup task: clear storage."""
import os

from ..enums import HacsStage
from .base import HacsTask


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTask):
    """Clear old files from storage."""

    stages = [HacsStage.SETUP]

    def execute(self) -> None:
        for storage_file in ("hacs",):
            path = f"{self.hacs.core.config_path}/.storage/{storage_file}"
            if os.path.isfile(path):
                self.log.info("Cleaning up old storage file: %s", path)
                os.remove(path)
