"""Base HACS class."""
import logging

import attr
from aiogithubapi.github import AIOGitHubAPI
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
from homeassistant.core import HomeAssistant

from .core import HacsCore
from .frontend import HacsFrontend
from .system import HacsSystem
from .stage import HacsStage


@attr.s
class Hacs:
    """Base HACS class."""

    action: bool = False
    core = attr.ib(HacsCore)
    default_repository: AIOGitHubAPIRepository = None
    frontend = attr.ib(HacsFrontend)
    hass: HomeAssistant = None
    log: logging.Logger = logging.getLogger("custom_components.hacs")
    repository: AIOGitHubAPIRepository = None
    stage: HacsStage = HacsStage.SETUP
    system = attr.ib(HacsSystem)
    version = attr.ib(str)
    github: AIOGitHubAPI = None
