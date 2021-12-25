"""Shared HACS elements."""
import os

from .base import HacsBase
from .utils.queue_manager import QueueManager

SHARE = {
    "hacs": None,
    "factory": None,
    "queue": None,
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
        SHARE["queue"] = QueueManager()
    return SHARE["queue"]
