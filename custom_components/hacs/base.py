"""Base HACS class."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import logging
import math
import pathlib
from typing import TYPE_CHECKING, Any

from aiogithubapi import (
    GitHub,
    GitHubAPI,
    GitHubAuthenticationException,
    GitHubRatelimitException,
)
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from aiohttp.client import ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.loader import Integration
from queueman.manager import QueueManager

from .const import REPOSITORY_HACS_DEFAULT
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
class HacsFrontend:
    """HacsFrontend."""

    version_running: str | None = None
    version_available: str | None = None
    version_expected: str | None = None
    update_pending: bool = False


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
    default: list[str] = field(default_factory=list)
    installed: list[str] = field(default_factory=list)
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

    disabled: bool = False
    disabled_reason: str | None = None
    running: bool = False
    stage = HacsStage.SETUP
    action: bool = False


class HacsBase:
    """Base HACS class."""

    _repositories = []
    _repositories_by_full_name = {}
    _repositories_by_id = {}

    common = HacsCommon()
    configuration = HacsConfiguration()
    core = HacsCore()
    data: HacsData | None = None
    factory: HacsTaskFactory | None = None
    frontend = HacsFrontend()
    github: GitHub | None = None
    githubapi: GitHubAPI | None = None
    hass: HomeAssistant | None = None
    integration: Integration | None = None
    log: logging.Logger = getLogger()
    queue: QueueManager | None = None
    recuring_tasks = []
    repositories: list[HacsRepository] = []
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
        self.system.disabled = True
        self.system.disabled_reason = reason
        if reason != HacsDisabledReason.REMOVED:
            self.log.error("HACS is disabled - %s", reason)

    def enable_hacs(self) -> None:
        """Enable HACS."""
        self.system.disabled = False
        self.system.disabled_reason = None
        self.log.info("HACS is enabled")

    def enable_hacs_category(self, category: HacsCategory):
        """Enable HACS category."""
        if category not in self.common.categories:
            self.log.info("Enable category: %s", category)
            self.common.categories.add(category)

    def disable_hacs_category(self, category: HacsCategory):
        """Disable HACS category."""
        if category in self.common.categories:
            self.log.info("Disabling category: %s", category)
            self.common.categories.pop(category)

    async def async_can_update(self) -> int:
        """Helper to calculate the number of repositories we can fetch data for."""
        try:
            response = await self.githubapi.rate_limit()
            if ((limit := response.data.resources.core.remaining or 0) - 1000) >= 15:
                return math.floor((limit - 1000) / 15)
            self.log.error(
                "GitHub API ratelimited - %s remaining", response.data.resources.core.remaining
            )
            self.disable_hacs(HacsDisabledReason.RATE_LIMIT)
        except GitHubAuthenticationException as exception:
            self.log.error("GitHub authentication failed - %s", exception)
            self.disable_hacs(HacsDisabledReason.INVALID_TOKEN)
        except GitHubRatelimitException as exception:
            self.log.error("GitHub API ratelimited - %s", exception)
            self.disable_hacs(HacsDisabledReason.RATE_LIMIT)
        except BaseException as exception:  # pylint: disable=broad-except
            self.log.exception(exception)

        return 0

    async def async_github_get_hacs_default_file(self, filename: str) -> dict[str, Any]:
        """Get the content of a default file."""
        response = await self.githubapi.repos.contents.get(
            repository=REPOSITORY_HACS_DEFAULT, path=filename
        )
        return json.loads(decode_content(response.data.content))
