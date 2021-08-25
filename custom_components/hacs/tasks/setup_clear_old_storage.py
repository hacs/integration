"""Starting setup task: clear storage."""
import os

from ..enums import HacsStage
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
    """Clear old files from storage."""

    stages = [HacsStage.SETUP]

    async def execute(self) -> None:
        await self.hacs.hass.async_add_executor_job(self._clear_storage)

    def _clear_storage(self) -> None:
        """Clear old files from storage."""
        for storage_file in ("hacs",):
            path = f"{self.hacs.core.config_path}/.storage/{storage_file}"
            if os.path.isfile(path):
                self.log.info("Cleaning up old storage file: %s", path)
                os.remove(path)
