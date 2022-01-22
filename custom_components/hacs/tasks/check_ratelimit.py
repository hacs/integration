""""Hacs base setup task."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsDisabledReason, HacsStage
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """ "Hacs task base."""

    _can_run_disabled = True
    schedule = timedelta(hours=1)

    async def async_execute(self) -> None:
        """Execute the task."""
        if (
            not self.hacs.system.disabled
            or self.hacs.system.disabled_reason != HacsDisabledReason.RATE_LIMIT
        ):
            self.task_logger(self.hacs.log.debug, "HACS is not ratelimited")
            return

        self.task_logger(self.hacs.log.debug, "Checking if ratelimit has lifted")
        can_update = await self.hacs.async_can_update()
        self.task_logger(self.hacs.log.debug, f"Ratelimit indicate we can update {can_update}")
        if can_update > 0:
            self.hacs.enable_hacs()
