"""Initialize the AwesomeVersion package."""

from .awesomeversion import AwesomeVersion, AwesomeVersionDiff
from .exceptions import (
    AwesomeVersionCompareException,
    AwesomeVersionException,
    AwesomeVersionStrategyException,
)
from .strategy import COMPARABLE_STRATEGIES, AwesomeVersionStrategy

__all__ = [
    "AwesomeVersion",
    "AwesomeVersionCompareException",
    "AwesomeVersionDiff",
    "AwesomeVersionException",
    "AwesomeVersionStrategy",
    "AwesomeVersionStrategyException",
    "COMPARABLE_STRATEGIES",
]
