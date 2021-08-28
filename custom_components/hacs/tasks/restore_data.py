""""Starting setup task: Restore"."""
from ..enums import HacsDisabledReason, HacsStage
from .base import HacsTask


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTask):
    """Restore HACS data."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        if not await self.hacs.data.restore():
            self.hacs.disable_hacs(HacsDisabledReason.RESTORE)
