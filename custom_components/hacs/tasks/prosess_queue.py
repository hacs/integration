""""Hacs base setup task."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..exceptions import HacsExecutionStillInProgress
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """ "Hacs task base."""

    schedule = timedelta(minutes=10)

    async def async_execute(self) -> None:
        """Execute the task."""
        if not self.hacs.queue.has_pending_tasks:
            self.task_logger(self.hacs.log.debug, "Nothing in the queue")
            return
        if self.hacs.queue.running:
            self.task_logger(self.hacs.log.debug, "Queue is already running")
            return

        can_update = await self.hacs.async_can_update()
        self.task_logger(
            self.hacs.log.debug,
            f"Can update {can_update} repositories, items in queue {self.hacs.queue.pending_tasks}",
        )
        if can_update != 0:
            self.hacs.status.background_task = True
            self.hass.bus.async_fire("hacs/status", {})
            try:
                await self.hacs.queue.execute(can_update)
            except HacsExecutionStillInProgress:
                pass
            self.hacs.status.background_task = False
            self.hass.bus.async_fire("hacs/status", {})
