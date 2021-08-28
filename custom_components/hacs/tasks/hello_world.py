""""Hacs base setup task."""
from .base import HacsTask


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTask):
    """ "Hacs task base."""

    def execute(self) -> None:
        self.log.debug("Hello World!")
