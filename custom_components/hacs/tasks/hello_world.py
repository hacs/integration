""""Hacs base setup task."""
from .base import HacsTaskManualBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskManualBase):
    """"Hacs task base."""

    def execute(self) -> None:
        self.log.debug("Hello World!")
