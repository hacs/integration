"""Base HACS class."""
from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, List, Optional

import attr
from aiogithubapi.github import AIOGitHubAPI
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from aiohttp.client import ClientSession
from homeassistant.core import HomeAssistant
from queueman.manager import QueueManager

from .const import INTEGRATION_VERSION
from .enums import HacsDisabledReason, HacsStage
from .exceptions import HacsException, HacsExpectedException
from .repositories import RERPOSITORY_CLASSES

if TYPE_CHECKING:
    from .hacsbase.configuration import Configuration
    from .hacsbase.data import HacsData
    from .helpers.classes.repository import HacsRepository
    from .models.core import HacsCore
    from .models.frontend import HacsFrontend
    from .operational.factory import HacsTaskFactory


@attr.dataclass
class HacsCommon:
    """Common for HACS."""

    categories: List = []
    default: List = []
    installed: List = []
    skip: List = []


@attr.dataclass
class HacsStatus:
    """HacsStatus."""

    startup: bool = True
    new: bool = False
    background_task: bool = False
    reloading_data: bool = False
    upgrading_all: bool = False


@attr.dataclass
class HacsSystem:
    """HACS System info."""

    disabled: bool = False
    disabled_reason: str | None = None
    running: bool = False
    version: str = INTEGRATION_VERSION
    stage = HacsStage.SETUP
    action: bool = False


@attr.s
class HacsBase:  # pylint: disable=too-many-instance-attributes
    """HACS Base class."""

    _configuration: "Configuration" | None = None
    _core: "HacsCore" | None = None
    _data: "HacsData" | None = None
    _default: AIOGitHubAPIRepository | None = None
    _factory: "HacsTaskFactory" | None = None
    _frontend: "HacsFrontend" | None = None
    _github: AIOGitHubAPI | None = None
    _hass: HomeAssistant | None = None
    _log: logging.Logger | None = None
    _queue: QueueManager | None = None
    _repository: AIOGitHubAPIRepository | None = None
    _session: ClientSession | None = None
    _stage: HacsStage = HacsStage.SETUP
    _system: "HacsSystem" | None = None

    _repositories_by_full_name: dict[str, "HacsRepository"] = {}
    _repositories_by_id: dict[str, "HacsRepository"] = {}
    _repositories: List["HacsRepository"] = []

    status = HacsStatus()
    system = HacsSystem()
    common = HacsCommon()
    recuring_tasks = []

    @property
    def repositories(self) -> List["HacsRepository"]:
        """Return the full repositories list."""
        return self._repositories

    @property
    def version(self) -> str:
        """Return the version of HACS."""
        return INTEGRATION_VERSION

    @property
    def stage(self) -> "HacsStage":
        """Returns a HacsStage object."""
        return self._stage

    @stage.setter
    def stage(self, value: "HacsStage") -> None:
        """Set the value for the stage property."""
        self._stage = value

    @property
    def factory(self) -> "HacsTaskFactory ":
        """Returns a HacsTaskFactory object."""
        return self._factory

    @factory.setter
    def factory(self, value: "HacsTaskFactory ") -> None:
        """Set the value for the factory property."""
        self._factory = value

    @property
    def queue(self) -> QueueManager:
        """Returns a QueueManager object."""
        return self._queue

    @queue.setter
    def queue(self, value: QueueManager) -> None:
        """Set the value for the queue property."""
        self._queue = value

    @property
    def core(self) -> "HacsCore":
        """Returns a HacsCore object."""
        return self._core

    @core.setter
    def core(self, value: "HacsCore") -> None:
        """Set the value for the core property."""
        self._core = value

    @property
    def configuration(self) -> "Configuration":
        """Returns a Configuration object."""
        return self._configuration

    @configuration.setter
    def configuration(self, value: "Configuration") -> None:
        """Set the value for the configuration property."""
        self._configuration = value

    @property
    def frontend(self) -> "HacsFrontend":
        """Returns a HacsFrontend object."""
        return self._frontend

    @frontend.setter
    def frontend(self, value: "HacsFrontend") -> None:
        """Set the value for the frontend property."""
        self._frontend = value

    @property
    def session(self) -> ClientSession:
        """Returns the client session used by HACS."""
        return self._session

    @session.setter
    def session(self, value: ClientSession) -> None:
        """Set the client session that HACS will use."""
        self._session = value

    @property
    def github(self) -> Optional[AIOGitHubAPI]:
        """Returns a AIOGitHubAPI object."""
        return self._github

    @github.setter
    def github(self, value: AIOGitHubAPI) -> None:
        """Set the value for the github property."""
        self._github = value

    @property
    def repository(self) -> Optional[AIOGitHubAPIRepository]:
        """Returns a AIOGitHubAPIRepository object representing hacs/integration."""
        return self._repository

    @repository.setter
    def repository(self, value: AIOGitHubAPIRepository) -> None:
        """Set the value for the repository property."""
        self._repository = value

    @property
    def default(self) -> Optional[AIOGitHubAPIRepository]:
        """Returns a AIOGitHubAPIRepository object representing hacs/default."""
        return self._default

    @default.setter
    def default(self, value: AIOGitHubAPIRepository) -> None:
        """Set the value for the default property."""
        self._default = value

    @property
    def hass(self) -> Optional[HomeAssistant]:
        """Returns a HomeAssistant object."""
        return self._hass

    @hass.setter
    def hass(self, value: HomeAssistant) -> None:
        """Set the value for the default property."""
        self._hass = value

    @property
    def data(self) -> Optional["HacsData"]:
        """Returns a HacsData object."""
        return self._data

    @data.setter
    def data(self, value: "HacsData") -> None:
        """Set the HacsData object."""
        self._data = value

    @property
    def log(self) -> Optional[logging.Logger]:
        """Returns a Logger object."""
        return self._log

    @log.setter
    def log(self, value: logging.Logger) -> None:
        """Set the Logger object."""
        self._log = value

    @property
    def integration_dir(self) -> pathlib.Path:
        """Return the HACS integration dir."""
        return pathlib.Path(__file__).parent

    def disable(self, reason: HacsDisabledReason) -> None:
        """Disable HACS."""
        self.system.disabled = True
        self.system.disabled_reason = reason
        self.log.error("HACS is disabled - %s", reason)

    def enable(self) -> None:
        """Enable HACS."""
        self.system.disabled = False
        self.system.disabled_reason = None
        self.log.info("HACS is enabled")

    def set_stage(self, stage: str) -> None:
        """Set the stage of HACS."""
        self.stage = HacsStage(stage)
        self.log.info("Stage changed: %s", self.stage)
        self.hass.bus.fire("hacs/stage", {"stage": self.stage})

    def set_repositories(self, repositories):
        """Set the list of repositories."""
        self._repositories = []
        self._repositories_by_id = {}
        self._repositories_by_full_name = {}

        for repository in repositories:
            self.add_repository(repository)

    def get_repository(
        self,
        repository_id: Optional[str | int] = None,
        repository_name: Optional[str | int] = None,
    ) -> Optional["HacsRepository"]:
        """Get a repository."""
        if repository_name is not None:
            return self._repositories_by_full_name.get(repository_name.lower())
        elif repository_id is not None:
            return self._repositories_by_id.get(str(repository_id))
        return None

    def add_repository(self, repository: "HacsRepository") -> None:
        """Add a new repository to the list."""
        if repository.data.full_name_lower not in self._repositories:
            self._repositories.append(repository)
        repo_id = str(repository.data.id)
        if repo_id != "0":
            self._repositories_by_id[repo_id] = repository
        self._repositories_by_full_name[repository.data.full_name_lower] = repository

    def remove_repository(self, repository: "HacsRepository") -> None:
        """Remove a repository from the list."""
        if repository.data.full_name_lower in self._repositories:
            self._repositories.remove(repository)
        repo_id = str(repository.data.id)
        if repo_id in self._repositories_by_id:
            del self._repositories_by_id[repo_id]
        if repository.data.full_name_lower in self._repositories_by_full_name:
            del self._repositories_by_full_name[repository.data.full_name_lower]

    async def async_register_repository(
        self,
        full_name: str,
        category: str,
        check: bool = True,
        ref: Optional[str] = None,
    ) -> Optional[List[str]]:
        """Register a repository."""
        if full_name in self.common.skip:
            if full_name != "hacs/integration":
                raise HacsExpectedException(f"Skipping {full_name}")

        if category not in RERPOSITORY_CLASSES:
            raise HacsException(f"{category} is not a valid repository category.")

        repository: "HacsRepository" = RERPOSITORY_CLASSES[category](full_name)
        if check:
            if errors := await repository.async_check_repository(ref):
                return errors

        if self.hass is not None and (
            (check and repository.data.new) or self.status.new
        ):
            self.hass.bus.async_fire(
                "hacs/repository",
                {
                    "action": "registration",
                    "repository": repository.data.full_name,
                    "repository_id": repository.data.id,
                },
            )
        self.add_repository(repository)
