""""Starting setup task: Restore"."""
from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsDisabledReason, HacsStage
from .base import HacsTask


async def async_setup(hacs: HacsBase, hass: HomeAssistant) -> None:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Restore HACS data."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        if not await self.hacs.data.restore():
            self.hacs.disable_hacs(HacsDisabledReason.RESTORE)
