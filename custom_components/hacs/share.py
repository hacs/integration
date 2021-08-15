"""Shared HACS elements."""
from __future__ import annotations

from dataclasses import dataclass

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import HacsBase
    from .hacsbase.hacs import Hacs
    from .operational.factory import HacsTaskFactory


@dataclass
class HacsShare:
    """HacsShare"""

    hacs: Hacs | None = None
    factory: HacsTaskFactory | None = None


SHARE = {
    "hacs": None,
    "factory": None,
    "queue": None,
    "removed_repositories": [],
    "rules": {},
}


class HacsBaseclass(Hacs):
    """Hacs Baseclass"""

    _hacs: get_hacs()

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


def get_hacs() -> HacsBase:
    """Return a HACS object."""
    if (hacs := HacsShare.hacs) is not None:
        return hacs

    from .hacsbase.hacs import Hacs  # pylint: disable=import-outside-toplevel

    SHARE["hacs"] = HacsShare.hacs = hacs = Hacs()

    if not "PYTEST" in os.environ and "GITHUB_ACTION" in os.environ:
        hacs.system.action = True

    return hacs


def get_factory():
    """Return a HacsTaskFactory object."""
    if (factory := HacsShare.factory) is not None:
        return factory

    from .operational.factory import (  # pylint: disable=import-outside-toplevel
        HacsTaskFactory,
    )

    SHARE["factory"] = HacsShare.factory = factory = HacsTaskFactory()

    return factory


def get_queue():
    if SHARE["queue"] is None:
        from queueman import QueueManager

        SHARE["queue"] = QueueManager()

    return SHARE["queue"]


def is_removed(repository):
    return repository in [x.repository for x in SHARE["removed_repositories"]]


def get_removed(repository):
    if not is_removed(repository):
        from custom_components.hacs.helpers.classes.removed import RemovedRepository

        removed_repo = RemovedRepository()
        removed_repo.repository = repository
        SHARE["removed_repositories"].append(removed_repo)
    filter_repos = [
        x
        for x in SHARE["removed_repositories"]
        if x.repository.lower() == repository.lower()
    ]

    return filter_repos.pop() or None


def list_removed_repositories():
    return SHARE["removed_repositories"]


class HacsBaseClass(Hacs):
    """Hacs Baseclass"""

    _hacs: get_hacs()

    common: HacsCommon = _hacs.common
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