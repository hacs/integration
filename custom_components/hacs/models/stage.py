"""Helper constants."""
# pylint: disable=missing-class-docstring
from enum import Enum


class HacsStage(str, Enum):
    SETUP = "setup"
    STARTUP = "startup"
    RUNNING = "running"
    BACKGROUND = "background"
