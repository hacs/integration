""""Store HACS data."""
from __future__ import annotations

from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import HomeAssistant

from ..base import HacsBase
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """ "Hacs task base."""

    events = [EVENT_HOMEASSISTANT_FINAL_WRITE]
    _can_run_disabled = True

    async def async_execute(self) -> None:
        """Execute the task."""
        await self.hacs.data.async_write(force=True)
