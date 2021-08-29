""""Hacs base setup task."""
from homeassistant.core import HomeAssistant

from ..base import HacsBase
from .base import HacsTask


async def async_setup(hacs: HacsBase, hass: HomeAssistant) -> None:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """ "Hacs task base."""

    def execute(self) -> None:
        self.log.debug("Hello World!")
