"""Base HACS class."""
import logging
from typing import List, Optional

import attr
from aiogithubapi.github import AIOGitHubAPI
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from homeassistant.core import HomeAssistant

from .enums import HacsStage
from .helpers.functions.logger import getLogger
from .models.core import HacsCore
from .models.frontend import HacsFrontend
from .models.system import HacsSystem


class HacsCommon:
    """Common for HACS."""

    categories: List = []
    default: List = []
    installed: List = []
    skip: List = []


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
    _repository: Optional[AIOGitHubAPIRepository]
    _stage: HacsStage = HacsStage.SETUP
    _common: Optional[HacsCommon]

    core: HacsCore = attr.ib(HacsCore)
    common: HacsCommon = attr.ib(HacsCommon)
    status: HacsStatus = attr.ib(HacsStatus)
    frontend: HacsFrontend = attr.ib(HacsFrontend)
    log: logging.Logger = getLogger()
    system: HacsSystem = attr.ib(HacsSystem)
    repositories: List = []


@attr.s
class HacsBase(HacsBaseAttributes):
    """Base HACS class."""

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
