"""Initialize the HACS base."""
from datetime import timedelta

from aiogithubapi import GitHubException
from aiogithubapi.exceptions import GitHubNotModifiedException

from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store,
)

from ..base import HacsBase
from ..enums import HacsCategory, HacsStage
from ..share import get_queue
from ..utils.queue_manager import QueueManager


class Hacs(HacsBase):
    """The base class of HACS, nested throughout the project."""

    queue = get_queue()

    async def register_repository(self, full_name, category, check=True):
        """Register a repository."""
        await register_repository(full_name, category, check=check)

    async def startup_tasks(self, _event=None):
        """Tasks that are started after startup."""
        await self.async_set_stage(HacsStage.STARTUP)
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        await self.handle_critical_repositories_startup()
        await self.async_load_default_repositories()
        await self.clear_out_removed_repositories()

        self.recuring_tasks.append(
            self.hass.helpers.event.async_track_time_interval(
                self.recurring_tasks_installed, timedelta(hours=2)
            )
        )

        self.recuring_tasks.append(
            self.hass.helpers.event.async_track_time_interval(
                self.recurring_tasks_all, timedelta(hours=25)
            )
        )

        self.hass.bus.async_fire("hacs/reload", {"force": True})
        await self.recurring_tasks_installed()

        if queue_task := self.tasks.get("prosess_queue"):
            await queue_task.execute_task()

        self.status.startup = False
        self.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})
        await self.async_set_stage(HacsStage.RUNNING)

    async def handle_critical_repositories_startup(self):
        """Handled critical repositories during startup."""
        alert = False
        critical = await async_load_from_store(self.hass, "critical")
        if not critical:
            return
        for repo in critical:
            if not repo["acknowledged"]:
                alert = True
        if alert:
            self.log.critical("URGENT!: Check the HACS panel!")
            self.hass.components.persistent_notification.create(
                title="URGENT!", message="**Check the HACS panel!**"
            )

    async def handle_critical_repositories(self):
        """Handled critical repositories during runtime."""
        # Get critical repositories
        critical_queue = QueueManager()
        instored = []
        critical = []
        was_installed = False

        try:
            critical = await self.async_github_get_hacs_default_file("critical")
        except GitHubNotModifiedException:
            return
        except GitHubException:
            pass

        if not critical:
            self.log.debug("No critical repositories")
            return

        stored_critical = await async_load_from_store(self.hass, "critical")

        for stored in stored_critical or []:
            instored.append(stored["repository"])

        stored_critical = []

        for repository in critical:
            removed_repo = self.repositories.removed_repository(repository["repository"])
            removed_repo.removal_type = "critical"
            repo = self.repositories.get_by_full_name(repository["repository"])

            stored = {
                "repository": repository["repository"],
                "reason": repository["reason"],
                "link": repository["link"],
                "acknowledged": True,
            }
            if repository["repository"] not in instored:
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

    async def recurring_tasks_installed(self, _notarealarg=None):
        """Recurring tasks for installed repositories."""
        self.log.debug("Starting recurring background task for installed repositories")
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        for repository in self.repositories.list_all:
            if self.status.startup and repository.data.full_name == "hacs/integration":
                continue
            if repository.data.installed and repository.data.category in self.common.categories:
                self.queue.add(self.async_semaphore_wrapper(repository.update_repository))

        await self.handle_critical_repositories()
        self.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})
        await self.data.async_write()
        self.log.debug("Recurring background task for installed repositories done")

    async def recurring_tasks_all(self, _notarealarg=None):
        """Recurring tasks for all repositories."""
        self.log.debug("Starting recurring background task for all repositories")
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        for repository in self.repositories.list_all:
            if repository.data.category in self.common.categories:
                self.queue.add(self.async_semaphore_wrapper(repository.common_update))

        await self.async_load_default_repositories()
        await self.clear_out_removed_repositories()
        self.status.background_task = False
        await self.data.async_write()
        self.hass.bus.async_fire("hacs/status", {})
        self.hass.bus.async_fire("hacs/repository", {"action": "reload"})
        self.log.debug("Recurring background task for all repositories done")

    async def clear_out_removed_repositories(self):
        """Clear out blaclisted repositories."""
        need_to_save = False
        for removed in self.repositories.list_removed:
            repository = self.repositories.get_by_full_name(removed.repository)
            if repository is not None:
                if repository.data.installed and removed.removal_type != "critical":
                    self.log.warning(
                        f"You have {repository.data.full_name} installed with HACS "
                        + "this repository has been removed, please consider removing it. "
                        + f"Removal reason ({removed.removal_type})"
                    )
                else:
                    need_to_save = True
                    repository.remove()

        if need_to_save:
            await self.data.async_write()

    async def async_load_default_repositories(self):
        """Load known repositories."""
        self.log.info("Loading known repositories")

        for item in await self.async_github_get_hacs_default_file(HacsCategory.REMOVED):
            removed = self.repositories.removed_repository(item["repository"])
            removed.update_data(item)

        for category in self.common.categories or []:
            self.queue.add(self.async_get_category_repositories(HacsCategory(category)))

        if queue_task := self.tasks.get("prosess_queue"):
            await queue_task.execute_task()

    async def async_get_category_repositories(self, category: HacsCategory):
        """Get repositories from category."""
        repositories = await self.async_github_get_hacs_default_file(category)
        for repo in repositories:
            if self.common.renamed_repositories.get(repo):
                repo = self.common.renamed_repositories[repo]
            if self.repositories.is_removed(repo):
                continue
            if repo in self.common.archived_repositories:
                continue
            repository = self.repositories.get_by_full_name(repo)
            if repository is not None:
                self.repositories.mark_default(repository)
                continue
            self.queue.add(
                self.async_semaphore_wrapper(
                    register_repository, full_name=repo, category=category, default=True
                )
            )
