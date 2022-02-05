""""Hacs base setup task."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsCategory, HacsStage
from ..exceptions import HacsException
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Hacs update removed task."""

    schedule = timedelta(hours=2)
    stages = [HacsStage.STARTUP]

    async def async_execute(self) -> None:
        """Execute the task."""

        need_to_save = False
        self.hacs.log.info("Loading removed repositories")

        try:
            removed_repositories = await self.hacs.async_github_get_hacs_default_file(
                HacsCategory.REMOVED
            )
        except HacsException:
            return

        for item in removed_repositories:
            removed = self.hacs.repositories.removed_repository(item["repository"])
            removed.update_data(item)

        for removed in self.hacs.repositories.list_removed:
            if (repository := self.hacs.repositories.get_by_full_name(removed.repository)) is None:
                continue
            if repository.data.installed and removed.removal_type != "critical":
                self.hacs.log.warning(
                    "You have '%s' installed with HACS "
                    "this repository has been removed from HACS, please consider removing it. "
                    "Removal reason (%s)",
                    repository.data.full_name,
                    removed.reason,
                )
            else:
                need_to_save = True
                repository.remove()

        if need_to_save:
            await self.hacs.data.async_write()
