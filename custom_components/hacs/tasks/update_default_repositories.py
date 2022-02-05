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
    """Hacs update default task."""

    schedule = timedelta(hours=3)
    stages = [HacsStage.STARTUP]

    async def async_execute(self) -> None:
        """Execute the task."""
        self.hacs.log.info("Loading known repositories")

        for category in self.hacs.common.categories or []:
            self.hacs.queue.add(self.async_get_category_repositories(HacsCategory(category)))

        if queue_task := self.hacs.tasks.get("prosess_queue"):
            await queue_task.execute_task()

    async def async_get_category_repositories(self, category: HacsCategory) -> None:
        """Get repositories from category."""
        try:
            repositories = await self.hacs.async_github_get_hacs_default_file(category)
        except HacsException:
            return

        for repo in repositories:
            if self.hacs.common.renamed_repositories.get(repo):
                repo = self.hacs.common.renamed_repositories[repo]
            if self.hacs.repositories.is_removed(repo):
                continue
            if repo in self.hacs.common.archived_repositories:
                continue
            repository = self.hacs.repositories.get_by_full_name(repo)
            if repository is not None:
                self.hacs.repositories.mark_default(repository)
                continue
            self.hacs.queue.add(
                self.hacs.async_register_repository(
                    repository_full_name=repo,
                    category=category,
                    default=True,
                )
            )
