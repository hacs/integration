""""Hacs base setup task."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Hacs update all task."""

    schedule = timedelta(hours=25)

    async def async_execute(self) -> None:
        """Execute the task."""
        self.task_logger(
            self.hacs.log.debug, "Starting recurring background task for all repositories"
        )

        for repository in self.hacs.repositories.list_all:
            if repository.data.category in self.hacs.common.categories:
                self.hacs.queue.add(repository.common_update())

        await self.hacs.data.async_write()
        self.hass.bus.async_fire("hacs/repository", {"action": "reload"})
        self.task_logger(self.hacs.log.debug, "Recurring background task for all repositories done")
