"""Custom logger for HACS."""
# pylint: disable=invalid-name
import logging
import os

from ..const import PACKAGE_NAME

_HACSLogger: logging.Logger = logging.getLogger(PACKAGE_NAME)

if "GITHUB_ACTION" in os.environ:
    logging.basicConfig(
        format="::%(levelname)s:: %(message)s",
        level="DEBUG",
    )


def getLogger(_name: str = None) -> logging.Logger:
    """Return a Logger instance."""
    return _HACSLogger
