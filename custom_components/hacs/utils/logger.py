"""Custom logger for HACS."""
import logging

from ..const import PACKAGE_NAME

_HACSLogger: logging.Logger = logging.getLogger(PACKAGE_NAME)


def get_hacs_logger() -> logging.Logger:
    """Return a Logger instance."""
    return _HACSLogger
