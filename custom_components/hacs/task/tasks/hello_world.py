""""Hacs base setup task."""
from .base import HacsTaskManualBase


async def async_setup():
    """Set up this task."""
    return HacsTaskHelloWorld()


class HacsTaskHelloWorld(HacsTaskManualBase):
    """"Hacs task base."""

    async def execute(self):
        self.log.error("Hello World!")
