""""Store HACS data."""
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE

from .base import HacsTask


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTask):
    """ "Hacs task base."""

    events = [EVENT_HOMEASSISTANT_FINAL_WRITE]

    async def async_execute(self) -> None:
        if self.hacs.system.disabled:
            return

        await self.hacs.data.async_write()
