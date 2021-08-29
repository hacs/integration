""""Starting setup task: Restore"."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsDisabledReason, HacsStage
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Restore HACS data."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        if not await self.hacs.data.restore():
            self.hacs.disable_hacs(HacsDisabledReason.RESTORE)
