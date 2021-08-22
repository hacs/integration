"""Initialize the HACS base."""
import json
from datetime import timedelta

from aiogithubapi import AIOGitHubAPIException
from queueman import QueueManager
from queueman.exceptions import QueueManagerExecutionStillInProgress

from custom_components.hacs.helpers import HacsHelpers
from custom_components.hacs.helpers.functions.get_list_from_default import (
    async_get_list_from_default,
)
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.helpers.functions.remaining_github_calls import (
    get_fetch_updates_for,
)
from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store,
)
from custom_components.hacs.operational.setup_actions.categories import (
    async_setup_extra_stores,
)
from custom_components.hacs.share import (
    get_factory,
    get_queue,
    get_removed,
    is_removed,
    list_removed_repositories,
)

from ..base import HacsBase
from ..enums import HacsCategory, HacsStage


class HacsStatus:
    """HacsStatus."""

    startup = True
    new = False
    background_task = False
    reloading_data = False
    upgrading_all = False


class HacsFrontend:
    """HacsFrontend."""

    version_running = None
    version_available = None
    version_expected = None
    update_pending = False


class HacsCommon:
    """Common for HACS."""

    categories = []
    default = []
    installed = []
    renamed_repositories = {}
    archived_repositories = []
    skip = []


class System:
    """System info."""

    status = HacsStatus()
    config_path = None
    ha_version = None
    disabled = False
    running = False
    lovelace_mode = "yaml"


class Hacs(HacsBase, HacsHelpers):
    """The base class of HACS, nested throughout the project."""

    _repositories = []
    _repositories_by_id = {}
    _repositories_by_full_name = {}
    repo = None
    data_repo = None
    data = None
    status = HacsStatus()
    configuration = None
    version = None
    session = None
    factory = get_factory()
    queue = get_queue()
    recuring_tasks = []
    common = HacsCommon()

    @property
    def repositories(self):
        """Return the full repositories list."""
        return self._repositories

    def async_set_repositories(self, repositories):
        """Set the list of repositories."""
        self._repositories = []
        self._repositories_by_id = {}
        self._repositories_by_full_name = {}

        for repository in repositories:
            self.async_add_repository(repository)

    def async_set_repository_id(self, repository, repo_id):
        """Update a repository id."""
        existing_repo_id = str(repository.data.id)
        if existing_repo_id == repo_id:
            return
        if existing_repo_id != "0":
            raise ValueError(
                f"The repo id for {repository.data.full_name_lower} is already set to {existing_repo_id}"
            )
        repository.data.id = repo_id
        self._repositories_by_id[repo_id] = repository

    def async_add_repository(self, repository):
        """Add a repository to the list."""
        if repository.data.full_name_lower in self._repositories_by_full_name:
            raise ValueError(
                f"The repo {repository.data.full_name_lower} is already added"
            )
        self._repositories.append(repository)
        repo_id = str(repository.data.id)
        if repo_id != "0":
            self._repositories_by_id[repo_id] = repository
        self._repositories_by_full_name[repository.data.full_name_lower] = repository

    def async_remove_repository(self, repository):
        """Remove a repository from the list."""
        if repository.data.full_name_lower not in self._repositories_by_full_name:
            return
        self._repositories.remove(repository)
        repo_id = str(repository.data.id)
        if repo_id in self._repositories_by_id:
            del self._repositories_by_id[repo_id]
        del self._repositories_by_full_name[repository.data.full_name_lower]

    def get_by_id(self, repository_id):
        """Get repository by ID."""
        return self._repositories_by_id.get(str(repository_id))

    def get_by_name(self, repository_full_name):
        """Get repository by full_name."""
        if repository_full_name is None:
            return None
        return self._repositories_by_full_name.get(repository_full_name.lower())

    def is_known(self, repository_id):
        """Return a bool if the repository is known."""
        return str(repository_id) in self._repositories_by_id

    @property
    def sorted_by_name(self):
        """Return a sorted(by name) list of repository objects."""
        return sorted(self.repositories, key=lambda x: x.display_name)

    @property
    def sorted_by_repository_name(self):
        """Return a sorted(by repository_name) list of repository objects."""
        return sorted(self.repositories, key=lambda x: x.data.full_name)

    async def register_repository(self, full_name, category, check=True):
        """Register a repository."""
        await register_repository(full_name, category, check=check)

    async def startup_tasks(self, _event=None):
        """Tasks that are started after startup."""
        await self.async_set_stage(HacsStage.STARTUP)
        self.status.background_task = True
        await async_setup_extra_stores()
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
        self.recuring_tasks.append(
            self.hass.helpers.event.async_track_time_interval(
                self.prosess_queue, timedelta(minutes=10)
            )
        )

        self.hass.bus.async_fire("hacs/reload", {"force": True})
        await self.recurring_tasks_installed()

        await self.prosess_queue()

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
            critical = await self.data_repo.get_contents("critical")
            critical = json.loads(critical.content)
        except AIOGitHubAPIException:
            pass

        if not critical:
            self.log.debug("No critical repositories")
            return

        stored_critical = await async_load_from_store(self.hass, "critical")

        for stored in stored_critical or []:
            instored.append(stored["repository"])

        stored_critical = []

        for repository in critical:
            removed_repo = get_removed(repository["repository"])
            removed_repo.removal_type = "critical"
            repo = self.get_by_name(repository["repository"])

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

    async def prosess_queue(self, _notarealarg=None):
        """Recurring tasks for installed repositories."""
        if not self.queue.has_pending_tasks:
            self.log.debug("Nothing in the queue")
            return
        if self.queue.running:
            self.log.debug("Queue is already running")
            return

        can_update = await get_fetch_updates_for(self.github)
        self.log.debug(
            "Can update %s repositories, items in queue %s",
            can_update,
            self.queue.pending_tasks,
        )
        if can_update == 0:
            self.log.info("HACS is ratelimited, repository updates will resume later.")
        else:
            self.status.background_task = True
            self.hass.bus.async_fire("hacs/status", {})
            try:
                await self.queue.execute(can_update)
            except QueueManagerExecutionStillInProgress:
                pass
            self.status.background_task = False
            self.hass.bus.async_fire("hacs/status", {})

    async def recurring_tasks_installed(self, _notarealarg=None):
        """Recurring tasks for installed repositories."""
        self.log.debug("Starting recurring background task for installed repositories")
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        for repository in self.repositories:
            if self.status.startup and repository.data.full_name == "hacs/integration":
                continue
            if (
                repository.data.installed
                and repository.data.category in self.common.categories
            ):
                self.queue.add(self.factory.safe_update(repository))

        await self.handle_critical_repositories()
        self.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})
        await self.data.async_write()
        self.log.debug("Recurring background task for installed repositories done")

    async def recurring_tasks_all(self, _notarealarg=None):
        """Recurring tasks for all repositories."""
        self.log.debug("Starting recurring background task for all repositories")
        await async_setup_extra_stores()
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        for repository in self.repositories:
            if repository.data.category in self.common.categories:
                self.queue.add(self.factory.safe_common_update(repository))

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
        for removed in list_removed_repositories():
            repository = self.get_by_name(removed.repository)
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

        for item in await async_get_list_from_default(HacsCategory.REMOVED):
            removed = get_removed(item["repository"])
            removed.reason = item.get("reason")
            removed.link = item.get("link")
            removed.removal_type = item.get("removal_type")

        for category in self.common.categories or []:
            self.queue.add(self.async_get_category_repositories(HacsCategory(category)))

        await self.prosess_queue()

    async def async_get_category_repositories(self, category: HacsCategory):
        """Get repositories from category."""
        repositories = await async_get_list_from_default(category)
        for repo in repositories:
            if self.common.renamed_repositories.get(repo):
                repo = self.common.renamed_repositories[repo]
            if is_removed(repo):
                continue
            if repo in self.common.archived_repositories:
                continue
            repository = self.get_by_name(repo)
            if repository is not None:
                if str(repository.data.id) not in self.common.default:
                    self.common.default.append(str(repository.data.id))
                else:
                    continue
                continue
            self.queue.add(self.factory.safe_register(repo, category))

    async def async_set_stage(self, stage: str) -> None:
        """Set the stage of HACS."""
        self.stage = HacsStage(stage)
        self.log.info("Stage changed: %s", self.stage)
        self.hass.bus.async_fire("hacs/stage", {"stage": self.stage})
