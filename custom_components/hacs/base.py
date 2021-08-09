"""Base HACS class."""
from __future__ import annotations
from dataclasses import dataclass, field
import logging
from typing import List, Optional, TYPE_CHECKING
import pathlib

import attr
from aiogithubapi.github import AIOGitHubAPI
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from homeassistant.core import HomeAssistant

from .enums import HacsDisabledReason, HacsStage
from .helpers.functions.logger import getLogger
from .hacsbase.configuration import Configuration
from .models.core import HacsCore
from .models.frontend import HacsFrontend
from .models.system import HacsSystem

if TYPE_CHECKING:
    from .helpers.classes.repository import HacsRepository
    from .task.manager import HacsTaskManager


@dataclass
class HacsCommon:
    """Common for HACS."""

    categories: list[str] = field(default_factory=list)
    default: list[str] = field(default_factory=list)
    installed: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)


@dataclass
class HacsStatus:
    """HacsStatus."""

    startup: bool = True
    new: bool = False
    background_task: bool = False
    reloading_data: bool = False
    upgrading_all: bool = False


@attr.s
class HacsBaseAttributes:
    """Base HACS class."""

    _default: Optional[AIOGitHubAPIRepository]
    _github: Optional[AIOGitHubAPI]
    _hass: Optional[HomeAssistant]
    _configuration: Optional[Configuration]
    _repository: Optional[AIOGitHubAPIRepository]
    _stage: HacsStage = HacsStage.SETUP
    _common: Optional[HacsCommon]

    core: HacsCore = attr.ib(HacsCore)
    common: HacsCommon = attr.ib(HacsCommon)
    status: HacsStatus = attr.ib(HacsStatus)
    frontend: HacsFrontend = attr.ib(HacsFrontend)
    log: logging.Logger = getLogger()
    system: HacsSystem = attr.ib(HacsSystem)
    repositories: list[HacsRepository] = []

    task: HacsTaskManager | None = None


class HacsBase:
    """Base HACS class."""

    def __init__(self) -> None:
        self._default: Optional[AIOGitHubAPIRepository]
        self._github: Optional[AIOGitHubAPI]
        self._hass: Optional[HomeAssistant]
        self._configuration: Optional[Configuration]
        self._repository: Optional[AIOGitHubAPIRepository]
        self._stage: HacsStage = HacsStage.SETUP
        self._common: Optional[HacsCommon]

        self.core: HacsCore = attr.ib(HacsCore)
        self.common: HacsCommon = attr.ib(HacsCommon)
        self.status: HacsStatus = attr.ib(HacsStatus)
        self.frontend: HacsFrontend = attr.ib(HacsFrontend)
        self.log: logging.Logger = getLogger()
        self.system: HacsSystem = attr.ib(HacsSystem)
        self.repositories: list[HacsRepository] = []

        self.task: HacsTaskManager | None = None

    @property
    def stage(self) -> HacsStage:
        """Returns a HacsStage object."""
        return self._stage

    @stage.setter
    def stage(self, value: HacsStage) -> None:
        """Set the value for the stage property."""
        self._stage = value

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
    def configuration(self) -> Optional[Configuration]:
        """Returns a Configuration object."""
        return self._configuration

    @configuration.setter
    def configuration(self, value: Configuration) -> None:
        """Set the value for the default property."""
        self._configuration = value

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
