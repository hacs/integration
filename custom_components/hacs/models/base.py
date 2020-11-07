"""Base HACS class."""
import attr
from aiogithubapi.github import AIOGitHubAPI
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from homeassistant.core import HomeAssistant

from .core import HacsCore
from .frontend import HacsFrontend
from .system import HacsSystem
from ..enums import HacsStage

from ..helpers.functions.logger import getLogger, HACSLoggerAdapter


@attr.s
class Hacs:
    """Base HACS class."""

    default_repository: AIOGitHubAPIRepository = None
    github: AIOGitHubAPI = None
    hass: HomeAssistant = None
    repository: AIOGitHubAPIRepository = None

    log: HACSLoggerAdapter = getLogger()

    core: HacsCore = attr.ib(HacsCore)
    frontend: HacsFrontend = attr.ib(HacsFrontend)
    stage: HacsStage = HacsStage.SETUP
    system: HacsSystem = attr.ib(HacsSystem)
