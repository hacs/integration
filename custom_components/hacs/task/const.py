"""Constants for tasks."""
from enum import Enum


class HacsTaskType(str, Enum):
    """HacsTaskType"""

    RUNTIME = "runtime"
    EVENT = "event"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    BASE = "base"
