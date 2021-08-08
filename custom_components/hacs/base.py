"""Base HACS class."""
from __future__ import annotations
from dataclasses import dataclass
import asyncio
import logging
from typing import Any, List, Optional, TYPE_CHECKING
import pathlib
from importlib import import_module

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
from .utils.modules import get_modules

if TYPE_CHECKING:
    from .helpers.classes.repository import HacsRepository
    from .managers.setup import HacsSetupManager


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


@dataclass
class HacsManagers:
    """HacsManagers."""

    setup: HacsSetupManager | None


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
    repositories: List["HacsRepository"] = []

    manager: HacsManagers | None = None


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


class HacsCommonManager(HacsBase):
    """Hacs common manager."""

    entries_loaction: str = ""

    def __init__(self) -> None:
        """Initialize the setup manager class."""
        self._entries: dict[str, Any] = {}

    @property
    def all_entries(self) -> list[Any]:
        """Return all list of all checks."""
        return list(self._entries.values())

    async def async_load(self):
        """Load all tasks."""
        package = f"{__package__}.{self.entries_loaction}"
        modules = get_modules(__file__, self.entries_loaction)

        async def _load_module(module: str):
            entry_module = import_module(f"{package}.{module}")
            if entry := await entry_module.async_setup():
                self._entries[entry.slug] = entry

        await asyncio.gather(*[_load_module(module) for module in modules])
        self.log.info(
            "Loaded %s setup entries (%s)", len(self.all_entries), self.all_entries
        )

    def get(self, slug: str) -> Any | None:
        """Return a element from the entries."""
        return self._entries.get(slug)

    @property
    def stages(self) -> tuple[HacsStage]:
        """Return all valid stages for the entry."""
        return ()

    async def async_execute(self) -> None:
        """Execute the the execute methods of each entry if the stage matches."""
        await asyncio.gather(
            *[
                module.execute()
                for module in self.all_entries
                if self.system.stage in module.stages or not module.stages
            ]
        )
