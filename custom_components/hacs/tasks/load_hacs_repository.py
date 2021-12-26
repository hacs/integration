"""Starting setup task: load HACS repository."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..base import HacsBase
from ..enums import HacsCategory, HacsDisabledReason, HacsGitHubRepo, HacsStage
from ..exceptions import HacsException
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Load HACS repositroy."""

    stages = [HacsStage.STARTUP]

    async def async_execute(self) -> None:
        """Execute the task."""
        try:
            repository = self.hacs.repositories.get_by_full_name(HacsGitHubRepo.INTEGRATION)
            if repository is None:
                await self.hacs.async_register_repository(
                    repository_full_name=HacsGitHubRepo.INTEGRATION,
                    category=HacsCategory.INTEGRATION,
                    default=True,
                )
                repository = self.hacs.repositories.get_by_full_name(HacsGitHubRepo.INTEGRATION)
            if repository is None:
                raise HacsException("Unknown error")
            repository.data.installed = True
            repository.data.installed_version = self.hacs.integration.version
            repository.data.new = False
            self.hacs.repository = repository.repository_object
            self.hacs.repositories.mark_default(repository)
        except HacsException as exception:
            if "403" in f"{exception}":
                self.task_logger(
                    self.hacs.log.critical,
                    "GitHub API is ratelimited, or the token is wrong.",
                )
            else:
                self.task_logger(self.hacs.log.critical, f"[{exception}] - Could not load HACS!")
            self.hacs.disable_hacs(HacsDisabledReason.LOAD_HACS)
