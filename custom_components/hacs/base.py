"""Base HACS class."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import timedelta
import gzip
import json
import logging
import math
import os
import pathlib
import shutil
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from aiogithubapi import (
    AIOGitHubAPIException,
    GitHub,
    GitHubAPI,
    GitHubAuthenticationException,
    GitHubException,
    GitHubNotModifiedException,
    GitHubRatelimitException,
)
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from aiohttp.client import ClientSession, ClientTimeout
from awesomeversion import AwesomeVersion
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.loader import Integration

from .const import TV
from .enums import (
    ConfigurationType,
    HacsCategory,
    HacsDisabledReason,
    HacsGitHubRepo,
    HacsStage,
    LovelaceMode,
)
from .exceptions import (
    HacsException,
    HacsExpectedException,
    HacsRepositoryArchivedException,
    HacsRepositoryExistException,
)
from .repositories import RERPOSITORY_CLASSES
from .utils.decode import decode_content
from .utils.logger import get_hacs_logger
from .utils.queue_manager import QueueManager
from .utils.store import async_load_from_store, async_save_to_store

if TYPE_CHECKING:
    from .repositories.base import HacsRepository
    from .tasks.manager import HacsTaskManager
    from .utils.data import HacsData
    from .validate.manager import ValidationManager


@dataclass
class RemovedRepository:
    """Removed repository."""

    repository: str | None = None
    reason: str | None = None
    link: str | None = None
    removal_type: str = None  # archived, not_compliant, critical, dev, broken
    acknowledged: bool = False

    def update_data(self, data: dict):
        """Update data of the repository."""
        for key in data:
            if data[key] is None:
                continue
            if key in (
                "reason",
                "link",
                "removal_type",
                "acknowledged",
            ):
                self.__setattr__(key, data[key])

    def to_json(self):
        """Return a JSON representation of the data."""
        return {
            "repository": self.repository,
            "reason": self.reason,
            "link": self.link,
            "removal_type": self.removal_type,
            "acknowledged": self.acknowledged,
        }


@dataclass
class HacsConfiguration:
    """HacsConfiguration class."""

    appdaemon_path: str = "appdaemon/apps/"
    appdaemon: bool = False
    config: dict[str, Any] = field(default_factory=dict)
    config_entry: dict[str, str] = field(default_factory=dict)
    config_type: ConfigurationType | None = None
    country: str = "ALL"
    debug: bool = False
    dev: bool = False
    experimental: bool = False
    frontend_compact: bool = False
    frontend_mode: str = "Grid"
    frontend_repo_url: str = ""
    frontend_repo: str = ""
    netdaemon_path: str = "netdaemon/apps/"
    netdaemon: bool = False
    onboarding_done: bool = False
    plugin_path: str = "www/community/"
    python_script_path: str = "python_scripts/"
    python_script: bool = False
    release_limit: int = 5
    sidepanel_icon: str = "hacs:hacs"
    sidepanel_title: str = "HACS"
    theme_path: str = "themes/"
    theme: bool = False
    token: str = None

    def to_json(self) -> str:
        """Return a json string."""
        return asdict(self)

    def update_from_dict(self, data: dict) -> None:
        """Set attributes from dicts."""
        if not isinstance(data, dict):
            raise HacsException("Configuration is not valid.")

        for key in data:
            self.__setattr__(key, data[key])


@dataclass
class HacsCore:
    """HACS Core info."""

    config_path: pathlib.Path | None = None
    ha_version: AwesomeVersion | None = None
    lovelace_mode = LovelaceMode("yaml")


@dataclass
class HacsCommon:
    """Common for HACS."""

    categories: set[str] = field(default_factory=set)
    renamed_repositories: dict[str, str] = field(default_factory=dict)
    archived_repositories: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)


@dataclass
class HacsStatus:
    """HacsStatus."""

    startup: bool = True
    new: bool = False
    background_task: bool = False
    reloading_data: bool = False
    upgrading_all: bool = False


@dataclass
class HacsSystem:
    """HACS System info."""

    disabled_reason: HacsDisabledReason | None = None
    running: bool = False
    stage = HacsStage.SETUP
    action: bool = False

    @property
    def disabled(self) -> bool:
        """Return if HACS is disabled."""
        return self.disabled_reason is not None


@dataclass
class HacsRepositories:
    """HACS Repositories."""

    _default_repositories: set[str] = field(default_factory=set)
    _repositories: list[str] = field(default_factory=list)
    _repositories_by_full_name: dict[str, str] = field(default_factory=dict)
    _repositories_by_id: dict[str, str] = field(default_factory=dict)
    _removed_repositories: list[RemovedRepository] = field(default_factory=list)

    @property
    def list_all(self) -> list[HacsRepository]:
        """Return a list of repositories."""
        return self._repositories

    @property
    def list_removed(self) -> list[RemovedRepository]:
        """Return a list of removed repositories."""
        return self._removed_repositories

    @property
    def list_downloaded(self) -> list[HacsRepository]:
        """Return a list of downloaded repositories."""
        return [repo for repo in self._repositories if repo.data.installed]

    def register(self, repository: HacsRepository, default: bool = False) -> None:
        """Register a repository."""
        repo_id = str(repository.data.id)

        if repo_id == "0":
            return

        if self.is_registered(repository_id=repo_id):
            return

        if repository not in self._repositories:
            self._repositories.append(repository)

        self._repositories_by_id[repo_id] = repository
        self._repositories_by_full_name[repository.data.full_name_lower] = repository

        if default:
            self.mark_default(repository)

    def unregister(self, repository: HacsRepository) -> None:
        """Unregister a repository."""
        repo_id = str(repository.data.id)

        if repo_id == "0":
            return

        if not self.is_registered(repository_id=repo_id):
            return

        if self.is_default(repo_id):
            self._default_repositories.remove(repo_id)

        if repository in self._repositories:
            self._repositories.remove(repository)

        self._repositories_by_id.pop(repo_id, None)
        self._repositories_by_full_name.pop(repository.data.full_name_lower, None)

    def mark_default(self, repository: HacsRepository) -> None:
        """Mark a repository as default."""
        repo_id = str(repository.data.id)

        if repo_id == "0":
            return

        if not self.is_registered(repository_id=repo_id):
            return

        self._default_repositories.add(repo_id)

    def set_repository_id(self, repository, repo_id):
        """Update a repository id."""
        existing_repo_id = str(repository.data.id)
        if existing_repo_id == repo_id:
            return
        if existing_repo_id != "0":
            raise ValueError(
                f"The repo id for {repository.data.full_name_lower} "
                f"is already set to {existing_repo_id}"
            )
        repository.data.id = repo_id
        self.register(repository)

    def is_default(self, repository_id: str | None = None) -> bool:
        """Check if a repository is default."""
        if not repository_id:
            return False
        return repository_id in self._default_repositories

    def is_registered(
        self,
        repository_id: str | None = None,
        repository_full_name: str | None = None,
    ) -> bool:
        """Check if a repository is registered."""
        if repository_id is not None:
            return repository_id in self._repositories_by_id
        if repository_full_name is not None:
            return repository_full_name in self._repositories_by_full_name
        return False

    def get_by_id(self, repository_id: str | None) -> HacsRepository | None:
        """Get repository by id."""
        if not repository_id:
            return None
        return self._repositories_by_id.get(str(repository_id))

    def get_by_full_name(self, repository_full_name: str | None) -> HacsRepository | None:
        """Get repository by full name."""
        if not repository_full_name:
            return None
        return self._repositories_by_full_name.get(repository_full_name.lower())

    def is_removed(self, repository_full_name: str) -> bool:
        """Check if a repository is removed."""
        return repository_full_name in (
            repository.repository for repository in self._removed_repositories
        )

    def removed_repository(self, repository_full_name: str) -> RemovedRepository:
        """Get repository by full name."""
        if self.is_removed(repository_full_name):
            if removed := [
                repository
                for repository in self._removed_repositories
                if repository.repository == repository_full_name
            ]:
                return removed[0]

        removed = RemovedRepository(repository=repository_full_name)
        self._removed_repositories.append(removed)
        return removed


class HacsBase:
    """Base HACS class."""

    common = HacsCommon()
    configuration = HacsConfiguration()
    core = HacsCore()
    data: HacsData | None = None
    frontend_version: str | None = None
    github: GitHub | None = None
    githubapi: GitHubAPI | None = None
    hass: HomeAssistant | None = None
    integration: Integration | None = None
    log: logging.Logger = get_hacs_logger()
    queue: QueueManager | None = None
    recuring_tasks = []
    repositories: HacsRepositories = HacsRepositories()
    repository: AIOGitHubAPIRepository | None = None
    session: ClientSession | None = None
    stage: HacsStage | None = None
    status = HacsStatus()
    system = HacsSystem()
    tasks: HacsTaskManager | None = None
    validation: ValidationManager | None = None
    version: str | None = None

    @property
    def integration_dir(self) -> pathlib.Path:
        """Return the HACS integration dir."""
        return self.integration.file_path

    async def async_set_stage(self, stage: HacsStage | None) -> None:
        """Set HACS stage."""
        if stage and self.stage == stage:
            return

        self.stage = stage
        if stage is not None:
            self.log.info("Stage changed: %s", self.stage)
            self.hass.bus.async_fire("hacs/stage", {"stage": self.stage})
            await self.tasks.async_execute_runtume_tasks()

    def disable_hacs(self, reason: HacsDisabledReason) -> None:
        """Disable HACS."""
        if self.system.disabled_reason == reason:
            return

        self.system.disabled_reason = reason
        if reason != HacsDisabledReason.REMOVED:
            self.log.error("HACS is disabled - %s", reason)

    def enable_hacs(self) -> None:
        """Enable HACS."""
        if self.system.disabled_reason is not None:
            self.system.disabled_reason = None
            self.log.info("HACS is enabled")

    def enable_hacs_category(self, category: HacsCategory) -> None:
        """Enable HACS category."""
        if category not in self.common.categories:
            self.log.info("Enable category: %s", category)
            self.common.categories.add(category)

    def disable_hacs_category(self, category: HacsCategory) -> None:
        """Disable HACS category."""
        if category in self.common.categories:
            self.log.info("Disabling category: %s", category)
            self.common.categories.pop(category)

    async def async_save_file(self, file_path: str, content: Any) -> bool:
        """Save a file."""

        def _write_file():
            with open(
                file_path,
                mode="w" if isinstance(content, str) else "wb",
                encoding="utf-8" if isinstance(content, str) else None,
                errors="ignore" if isinstance(content, str) else None,
            ) as file_handler:
                file_handler.write(content)

            # Create gz for .js files
            if os.path.isfile(file_path):
                if file_path.endswith(".js"):
                    with open(file_path, "rb") as f_in:
                        with gzip.open(file_path + ".gz", "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)

            # LEGACY! Remove with 2.0
            if "themes" in file_path and file_path.endswith(".yaml"):
                filename = file_path.split("/")[-1]
                base = file_path.split("/themes/")[0]
                combined = f"{base}/themes/{filename}"
                if os.path.exists(combined):
                    self.log.info("Removing old theme file %s", combined)
                    os.remove(combined)

        try:
            await self.hass.async_add_executor_job(_write_file)
        except BaseException as error:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.log.error("Could not write data to %s - %s", file_path, error)
            return False

        return os.path.exists(file_path)

    async def async_can_update(self) -> int:
        """Helper to calculate the number of repositories we can fetch data for."""
        try:
            response = await self.async_github_api_method(self.githubapi.rate_limit)
            if ((limit := response.data.resources.core.remaining or 0) - 1000) >= 15:
                return math.floor((limit - 1000) / 15)
            self.log.info(
                "GitHub API ratelimited - %s remaining", response.data.resources.core.remaining
            )
            self.disable_hacs(HacsDisabledReason.RATE_LIMIT)
        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.log.exception(exception)

        return 0

    async def async_github_get_hacs_default_file(self, filename: str) -> list:
        """Get the content of a default file."""
        response = await self.async_github_api_method(
            method=self.githubapi.repos.contents.get,
            repository=HacsGitHubRepo.DEFAULT,
            path=filename,
        )
        if response is None:
            return []

        return json.loads(decode_content(response.data.content))

    async def async_github_api_method(
        self,
        method: Callable[[], Awaitable[TV]],
        *args,
        raise_exception: bool = True,
        **kwargs,
    ) -> TV | None:
        """Call a GitHub API method"""
        _exception = None

        try:
            return await method(*args, **kwargs)
        except GitHubAuthenticationException as exception:
            self.disable_hacs(HacsDisabledReason.INVALID_TOKEN)
            _exception = exception
        except GitHubRatelimitException as exception:
            self.disable_hacs(HacsDisabledReason.RATE_LIMIT)
            _exception = exception
        except GitHubNotModifiedException as exception:
            raise exception
        except GitHubException as exception:
            _exception = exception
        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.log.exception(exception)
            _exception = exception

        if raise_exception and _exception is not None:
            raise HacsException(_exception)
        return None

    async def async_register_repository(
        self,
        repository_full_name: str,
        category: HacsCategory,
        *,
        check: bool = True,
        ref: str | None = None,
        repository_id: str | None = None,
        default: bool = False,
    ) -> None:
        """Register a repository."""
        if repository_full_name in self.common.skip:
            if repository_full_name != HacsGitHubRepo.INTEGRATION:
                raise HacsExpectedException(f"Skipping {repository_full_name}")

        if repository_full_name == "home-assistant/core":
            raise HacsExpectedException(
                "You can not add homeassistant/core, to use core integrations "
                "check the Home Assistant documentation for how to add them."
            )

        if category not in RERPOSITORY_CLASSES:
            raise HacsException(f"{category} is not a valid repository category.")

        if (renamed := self.common.renamed_repositories.get(repository_full_name)) is not None:
            repository_full_name = renamed

        repository: HacsRepository = RERPOSITORY_CLASSES[category](self, repository_full_name)
        if check:
            try:
                await repository.async_registration(ref)
                if self.status.new:
                    repository.data.new = False
                if repository.validate.errors:
                    self.common.skip.append(repository.data.full_name)
                    if not self.status.startup:
                        self.log.error("Validation for %s failed.", repository_full_name)
                    if self.system.action:
                        raise HacsException(
                            f"::error:: Validation for {repository_full_name} failed."
                        )
                    return repository.validate.errors
                if self.system.action:
                    repository.logger.info("%s Validation completed", repository)
                else:
                    repository.logger.info("%s Registration completed", repository)
            except (HacsRepositoryExistException, HacsRepositoryArchivedException):
                return
            except AIOGitHubAPIException as exception:
                self.common.skip.append(repository.data.full_name)
                raise HacsException(
                    f"Validation for {repository_full_name} failed with {exception}."
                ) from exception

        if repository_id is not None:
            repository.data.id = repository_id

        if str(repository.data.id) != "0" and (
            exists := self.repositories.get_by_id(repository.data.id)
        ):
            self.repositories.unregister(exists)

        else:
            if self.hass is not None and ((check and repository.data.new) or self.status.new):
                self.hass.bus.async_fire(
                    "hacs/repository",
                    {
                        "action": "registration",
                        "repository": repository.data.full_name,
                        "repository_id": repository.data.id,
                    },
                )
        self.repositories.register(repository, default)

    async def startup_tasks(self, _event=None) -> None:
        """Tasks that are started after startup."""
        await self.async_set_stage(HacsStage.STARTUP)
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        try:
            await self.handle_critical_repositories_startup()
            await self.async_load_default_repositories()
        except HacsException as exception:
            self.log.warning(
                "Could not load default repositories: %s, retrying in 5 minuttes", exception
            )
            if not self.system.disabled:
                async_call_later(self.hass, timedelta(minutes=5), self.startup_tasks)
            return

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

        self.status.startup = False
        await self.async_set_stage(HacsStage.RUNNING)

        self.hass.bus.async_fire("hacs/reload", {"force": True})
        try:
            await self.recurring_tasks_installed()
        except HacsException as exception:
            self.log.warning(
                "Could not run initial task for downloaded repositories: %s, retrying in 5 minuttes",
                exception,
            )
            if not self.system.disabled:
                async_call_later(self.hass, timedelta(minutes=5), self.startup_tasks)
            return

        if queue_task := self.tasks.get("prosess_queue"):
            await queue_task.execute_task()

        self.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})

    async def handle_critical_repositories_startup(self) -> None:
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

    async def handle_critical_repositories(self) -> None:
        """Handled critical repositories during runtime."""
        # Get critical repositories
        critical_queue = QueueManager(hass=self.hass)
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
            self.log.critical("Resarting Home Assistant")
            self.hass.async_create_task(self.hass.async_stop(100))

    async def recurring_tasks_installed(self, _notarealarg=None) -> None:
        """Recurring tasks for installed repositories."""
        self.log.debug("Starting recurring background task for installed repositories")
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        for repository in self.repositories.list_all:
            if self.status.startup and repository.data.full_name == HacsGitHubRepo.INTEGRATION:
                continue
            if repository.data.installed and repository.data.category in self.common.categories:
                self.queue.add(repository.update_repository())

        await self.handle_critical_repositories()
        self.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})
        await self.data.async_write()
        self.log.debug("Recurring background task for installed repositories done")

    async def recurring_tasks_all(self, _notarealarg=None) -> None:
        """Recurring tasks for all repositories."""
        self.log.debug("Starting recurring background task for all repositories")
        self.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})

        for repository in self.repositories.list_all:
            if repository.data.category in self.common.categories:
                self.queue.add(repository.common_update())

        await self.async_load_default_repositories()
        self.status.background_task = False
        await self.data.async_write()
        self.hass.bus.async_fire("hacs/status", {})
        self.hass.bus.async_fire("hacs/repository", {"action": "reload"})
        self.log.debug("Recurring background task for all repositories done")

    async def async_load_default_repositories(self) -> None:
        """Load known repositories."""
        need_to_save = False
        self.log.info("Loading known repositories")

        for item in await self.async_github_get_hacs_default_file(HacsCategory.REMOVED):
            removed = self.repositories.removed_repository(item["repository"])
            removed.update_data(item)

        for category in self.common.categories or []:
            self.queue.add(self.async_get_category_repositories(HacsCategory(category)))

        if queue_task := self.tasks.get("prosess_queue"):
            await queue_task.execute_task()

        for removed in self.repositories.list_removed:
            if (repository := self.repositories.get_by_full_name(removed.repository)) is None:
                continue
            if repository.data.installed and removed.removal_type != "critical":
                self.log.warning(
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
            await self.data.async_write()

    async def async_get_category_repositories(self, category: HacsCategory) -> None:
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
                self.async_register_repository(
                    repository_full_name=repo,
                    category=category,
                    default=True,
                )
            )

    async def async_download_file(self, url: str) -> bytes | None:
        """Download files, and return the content."""
        if url is None:
            return None

        tries_left = 5

        if "tags/" in url:
            url = url.replace("tags/", "")

        self.log.debug("Downloading %s", url)

        while tries_left > 0:
            try:
                request = await self.session.get(url=url, timeout=ClientTimeout(total=60))

                # Make sure that we got a valid result
                if request.status == 200:
                    return await request.read()

                raise HacsException(
                    f"Got status code {request.status} when trying to download {url}"
                )
            except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
                self.log.debug("Download failed - %s", exception)
                tries_left -= 1
                await asyncio.sleep(1)
                continue

        return None
