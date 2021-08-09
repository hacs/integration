""""Hacs base setup task."""
from custom_components.hacs.utils.bind_hacs import bind_hacs
from .base import HacsTaskManualBase


async def async_setup():
    """Set up this task."""
    return HacsTaskHelloWorld()


@bind_hacs
class HacsTaskHelloWorld(HacsTaskManualBase):
    """"Hacs task base."""

    async def execute(self):
        self.log.error("Hello World!")
        self.log.error(self.__hacs)
