""""Starting setup task: Restore"."""
from ..enums import HacsDisabledReason, HacsStage
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
    """Restore HACS data."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        if not await self.hacs.data.restore():
            self.hacs.disable_hacs(HacsDisabledReason.RESTORE)
