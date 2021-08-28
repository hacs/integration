"""Handle critical repositories."""
import json

from aiogithubapi import GitHubException
from queueman import QueueManager

from custom_components.hacs.share import get_removed

from ..const import REPOSITORY_HACS_DEFAULT
from ..enums import HacsStage
from ..helpers.functions.store import async_load_from_store, async_save_to_store
from ..utils.decode import decode_content
from .base import HacsTask


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTask):
    """Handle critical repositories."""

    stages = [HacsStage.STARTUP]

    async def async_execute(self) -> None:
        critical_queue = QueueManager()
        was_installed = False
        stored_critical = await async_load_from_store(self.hass, "critical")
        for repo in stored_critical:
            if not repo["acknowledged"]:
                self.log.critical("URGENT!: Check the HACS panel!")
                self.hass.components.persistent_notification.create(
                    title="URGENT!", message="**Check the HACS panel!**"
                )

        try:
            response = await self.hacs.githubapi.repos.contents.get(
                REPOSITORY_HACS_DEFAULT, "critical"
            )
        except GitHubException:
            return

        remote_critical = json.loads(decode_content(response.data.content))

        for repository in remote_critical:
            removed_repo = get_removed(repository["repository"])
            removed_repo.removal_type = "critical"
            repo = self.hacs.get_by_name(repository["repository"])

            stored = {
                "repository": repository["repository"],
                "reason": repository["reason"],
                "link": repository["link"],
                "acknowledged": True,
            }
            if repo is not None and repo.installed:
                self.log.critical(
                    "Removing repository %s, it is marked as critical",
                    repository["repository"],
                )
                was_installed = True
                stored["acknowledged"] = False
                # Remove from HACS
                critical_queue.add(repository.uninstall())
                repo.remove()

            stored_critical.append(stored)
            removed_repo.update_data(stored)

        # Uninstall
        await critical_queue.execute()

        # Save to FS
        await async_save_to_store(self.hass, "critical", stored_critical)

        # Restart HASS
        if was_installed:
            self.log.critical("Resarting Home Assistant")
            self.hass.async_create_task(self.hass.async_stop(100))
