""""Hacs base setup task."""
from .base import HacsTaskManualBase


async def async_setup() -> None:
    """Set up this task."""
    return HacsTaskHelloWorld()


class HacsTaskHelloWorld(HacsTaskManualBase):
    """"Hacs task base."""

    async def execute(self) -> None:
        self.log.debug("Hello World!")
