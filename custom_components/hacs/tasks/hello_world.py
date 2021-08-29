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
    """ "Hacs task base."""

    schedule = timedelta(weeks=52)

    def execute(self) -> None:
        self.log.debug("Hello World!")
