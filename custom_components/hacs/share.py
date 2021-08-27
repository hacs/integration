"""Shared HACS elements."""
import os

from .base import HacsBase

SHARE = {
    "hacs": None,
    "factory": None,
    "queue": None,
    "removed_repositories": [],
    "rules": {},
}


def get_hacs() -> HacsBase:
    if SHARE["hacs"] is None:
        from custom_components.hacs.hacsbase.hacs import Hacs as Legacy

        _hacs = Legacy()

        if not "PYTEST" in os.environ and "GITHUB_ACTION" in os.environ:
            _hacs.system.action = True

        SHARE["hacs"] = _hacs

    return SHARE["hacs"]


def get_factory():
    if SHARE["factory"] is None:
        from custom_components.hacs.operational.factory import HacsTaskFactory

        SHARE["factory"] = HacsTaskFactory()

    return SHARE["factory"]


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
        x for x in SHARE["removed_repositories"] if x.repository.lower() == repository.lower()
    ]

    return filter_repos.pop() or None


def list_removed_repositories():
    return SHARE["removed_repositories"]
