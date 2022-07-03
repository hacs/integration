# pylint: disable=missing-module-docstring, missing-function-docstring
from logging import Logger

from custom_components.hacs.utils.logger import LOGGER


def test_logger():
    hacs_logger = LOGGER
    assert isinstance(hacs_logger, Logger)
