"""Starting setup task: clear storage."""
from __future__ import annotations

import os

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsStage
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Clear old files from storage."""

    stages = [HacsStage.SETUP]

    def execute(self) -> None:
        """Execute the task."""
        for storage_file in ("hacs",):
            path = f"{self.hacs.core.config_path}/.storage/{storage_file}"
            if os.path.isfile(path):
                self.task_logger(self.hacs.log.info, f"Cleaning up old storage file: {path}")
                os.remove(path)
