""""Hacs base setup task."""
from __future__ import annotations

from datetime import timedelta

from aiogithubapi import GitHubNotModifiedException
from homeassistant.core import HomeAssistant

from custom_components.hacs.utils.queue_manager import QueueManager
from custom_components.hacs.utils.store import (
    async_load_from_store,
    async_save_to_store,
)

from ..base import HacsBase
from ..enums import HacsStage
from ..exceptions import HacsException
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Hacs update critical task."""

    schedule = timedelta(hours=2)
    stages = [HacsStage.RUNNING]

    async def async_execute(self) -> None:
        """Execute the task."""
        critical_queue = QueueManager(hass=self.hass)
        instored = []
        critical = []
        was_installed = False

        try:
            critical = await self.hacs.async_github_get_hacs_default_file("critical")
        except GitHubNotModifiedException:
            return
        except HacsException:
            pass

        if not critical:
            self.hacs.log.debug("No critical repositories")
            return

        stored_critical = await async_load_from_store(self.hass, "critical")

        for stored in stored_critical or []:
            instored.append(stored["repository"])

        stored_critical = []

        for repository in critical:
            removed_repo = self.hacs.repositories.removed_repository(repository["repository"])
            removed_repo.removal_type = "critical"
            repo = self.hacs.repositories.get_by_full_name(repository["repository"])

            stored = {
                "repository": repository["repository"],
                "reason": repository["reason"],
                "link": repository["link"],
                "acknowledged": True,
            }
            if repository["repository"] not in instored:
                if repo is not None and repo.data.installed:
                    self.hacs.log.critical(
                        "Removing repository %s, it is marked as critical",
                        repository["repository"],
                    )
                    was_installed = True
                    stored["acknowledged"] = False
                    # Remove from HACS
                    critical_queue.add(repo.uninstall())
                    repo.remove()

            stored_critical.append(stored)
            removed_repo.update_data(stored)

        # Uninstall
        await critical_queue.execute()

        # Save to FS
        await async_save_to_store(self.hass, "critical", stored_critical)

        # Restart HASS
        if was_installed:
            self.hacs.log.critical("Resarting Home Assistant")
            self.hass.async_create_task(self.hass.async_stop(100))
