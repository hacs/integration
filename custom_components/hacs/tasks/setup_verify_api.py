""""Starting setup task: Verify API"."""
from ..enums import HacsStage
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
    """Verify the connection to the GitHub API."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        can_update = await self.hacs.async_can_update()
        self.log.debug("Can update %s repositories", can_update)
