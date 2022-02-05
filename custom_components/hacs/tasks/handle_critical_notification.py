""""Hacs base setup task."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsStage
from ..utils.store import async_load_from_store
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Hacs notify critical during startup task."""

    stages = [HacsStage.STARTUP]

    async def async_execute(self) -> None:
        """Execute the task."""
        alert = False
        critical = await async_load_from_store(self.hass, "critical")
        if not critical:
            return
        for repo in critical:
            if not repo["acknowledged"]:
                alert = True
        if alert:
            self.hacs.log.critical("URGENT!: Check the HACS panel!")
            self.hass.components.persistent_notification.create(
                title="URGENT!", message="**Check the HACS panel!**"
            )
