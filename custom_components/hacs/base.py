"""Base HACS class."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import gzip
import json
import logging
import math
import os
import pathlib
import shutil
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from aiogithubapi import (
    GitHub,
    GitHubAPI,
    GitHubAuthenticationException,
    GitHubException,
    GitHubNotModifiedException,
    GitHubRatelimitException,
)
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from aiohttp.client import ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.loader import Integration

from .const import REPOSITORY_HACS_DEFAULT, TV
from .enums import (
    ConfigurationType,
    HacsCategory,
    HacsDisabledReason,
    HacsStage,
    LovelaceMode,
)
from .exceptions import HacsException
from .utils.decode import decode_content
from .utils.logger import getLogger
from .utils.queue_manager import QueueManager

if TYPE_CHECKING:
    from .hacsbase.data import HacsData
    from .helpers.classes.repository import HacsRepository
    from .operational.factory import HacsTaskFactory
    from .tasks.manager import HacsTaskManager


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
    ha_version: str | None = None
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

    _default_repositories: set[HacsRepository] = field(default_factory=set)
    _repositories: list[str] = field(default_factory=list)
    _repositories_by_full_name: dict[str, str] = field(default_factory=dict)
    _repositories_by_id: dict[str, str] = field(default_factory=dict)

    @property
    def list_all(self) -> list[HacsRepository]:
        """Return a list of repositories."""
        return self._repositories

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


class HacsBase:
    """Base HACS class."""

    common = HacsCommon()
    configuration = HacsConfiguration()
    core = HacsCore()
    data: HacsData | None = None
    factory: HacsTaskFactory | None = None
    frontend_version: str | None = None
    github: GitHub | None = None
    githubapi: GitHubAPI | None = None
    hass: HomeAssistant | None = None
    integration: Integration | None = None
    log: logging.Logger = getLogger()
    queue: QueueManager | None = None
    recuring_tasks = []
    repositories: HacsRepositories = HacsRepositories()
    repository: AIOGitHubAPIRepository | None = None
    session: ClientSession | None = None
    stage: HacsStage | None = None
    status = HacsStatus()
    system = HacsSystem()
    tasks: HacsTaskManager | None = None
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
        except BaseException as error:  # pylint: disable=broad-except
            self.log.error("Could not write data to %s - %s", file_path, error)
            return False

        return os.path.exists(file_path)

    async def async_can_update(self) -> int:
        """Helper to calculate the number of repositories we can fetch data for."""
        try:
            response = await self.async_github_api_method(self.githubapi.rate_limit)
            if ((limit := response.data.resources.core.remaining or 0) - 1000) >= 15:
                return math.floor((limit - 1000) / 15)
            self.log.error(
                "GitHub API ratelimited - %s remaining", response.data.resources.core.remaining
            )
            self.disable_hacs(HacsDisabledReason.RATE_LIMIT)
        except BaseException as exception:  # pylint: disable=broad-except
            self.log.exception(exception)

        return 0

    async def async_github_get_hacs_default_file(self, filename: str) -> dict[str, Any]:
        """Get the content of a default file."""
        response = await self.async_github_api_method(
            method=self.githubapi.repos.contents.get,
            repository=REPOSITORY_HACS_DEFAULT,
            path=filename,
        )
        return json.loads(decode_content(response.data.content))

    async def async_github_api_method(
        self,
        method: Callable[[], Awaitable[TV]],
        *args,
        **kwargs,
    ) -> TV | None:
        """Call a GitHub API method"""
        try:
            return await method(*args, **kwargs)
        except GitHubAuthenticationException as exception:
            self.log.error("GitHub authentication failed - %s", exception)
            self.disable_hacs(HacsDisabledReason.INVALID_TOKEN)
        except GitHubRatelimitException as exception:
            self.log.error("GitHub API ratelimited - %s", exception)
            self.disable_hacs(HacsDisabledReason.RATE_LIMIT)
        except GitHubNotModifiedException as exception:
            raise exception
        except GitHubException as exception:
            self.log.error("GitHub API error - %s", exception)
            raise HacsException(exception) from exception
        except BaseException as exception:
            self.log.exception(exception)
            raise HacsException(exception) from exception
        return None
