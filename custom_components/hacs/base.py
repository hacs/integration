"""Base HACS class."""
from __future__ import annotations

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

    default: Optional[AIOGitHubAPIRepository]
    github: Optional[AIOGitHubAPI]

    repositories: List["HacsRepository"] = []

    task: HacsTaskManager | None = None


class Hacs:
    """Base HACS class."""

    def __init__(self) -> None:
        """Initialize."""
        self.common: HacsCommon = HacsCommon()
        self.configuration: Configuration = Configuration()
        self.core: HacsCore = HacsCore()
        self.default: AIOGitHubAPIRepository | None = None
        self.frontend: HacsFrontend = HacsFrontend()
        self.github: AIOGitHubAPI | None = None
        self.hass: HomeAssistant | None = None
        self.integration_dir = pathlib.Path(__file__).parent
        self.log: logging.Logger = getLogger()
        self.repository: AIOGitHubAPIRepository | None = None
        self.status: HacsStatus = HacsStatus()
        self.system: HacsSystem = HacsSystem()

        self._stage: HacsStage = HacsStage.SETUP

    @property
    def stage(self) -> HacsStage:
        """Returns the current stage."""
        return self._stage

    @stage.setter
    def stage(self, value: Configuration) -> None:
        """Set the current stage."""
        self._stage = value

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


class HacsBase(Hacs):
    """Hacs Baseclass"""

    __hacs: Hacs

    common: HacsCommon = __hacs.common
    configuration: Configuration = Configuration()
    core: HacsCore = HacsCore()
    default: AIOGitHubAPIRepository | None = None
    frontend: HacsFrontend = __hacs.frontend
    github: AIOGitHubAPI | None = __hacs.github
    hass: HomeAssistant | None = __hacs.hass
    integration_dir = pathlib.Path(__file__).parent
    log: logging.Logger = __hacs.log
    repository: AIOGitHubAPIRepository = __hacs.repository
    stage: HacsStage = __hacs.stage
    status: HacsStatus = HacsStatus()
    system: HacsSystem = HacsSystem()
