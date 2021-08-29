""""Store HACS data."""
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import HomeAssistant

from ..base import HacsBase
from .base import HacsTask


async def async_setup(hacs: HacsBase, hass: HomeAssistant) -> None:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """ "Hacs task base."""

    events = [EVENT_HOMEASSISTANT_FINAL_WRITE]

    async def async_execute(self) -> None:
        if self.hacs.system.disabled:
            return

        await self.hacs.data.async_write()
