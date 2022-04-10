""""Hacs base setup task."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsStage
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Hacs update downloaded task."""

    schedule = timedelta(hours=2)
    stages = [HacsStage.STARTUP]

    async def async_execute(self) -> None:
        """Execute the task."""
        self.task_logger(
            self.hacs.log.debug, "Starting recurring background task for installed repositories"
        )

        for repository in self.hacs.repositories.list_downloaded:
            if repository.data.category in self.hacs.common.categories:
                self.hacs.queue.add(repository.update_repository())

        await self.hacs.data.async_write()
        self.task_logger(
            self.hacs.log.debug, "Recurring background task for installed repositories done"
        )
