"""Base HACS class."""
import logging

import attr
from aiogithubapi.github import AIOGitHubAPI
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from homeassistant.core import HomeAssistant

from .core import HacsCore
from .frontend import HacsFrontend
from .system import HacsSystem
from ..enums import HacsStage


@attr.s
class Hacs:
    """Base HACS class."""

    default_repository: AIOGitHubAPIRepository = None
    github: AIOGitHubAPI = None
    hass: HomeAssistant = None
    repository: AIOGitHubAPIRepository = None

    log: logging.Logger = logging.getLogger("custom_components.hacs")

    core: HacsCore = attr.ib(HacsCore)
    frontend: HacsFrontend = attr.ib(HacsFrontend)
    stage: HacsStage = HacsStage.SETUP
    system: HacsSystem = attr.ib(HacsSystem)
