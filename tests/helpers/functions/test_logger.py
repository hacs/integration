# pylint: disable=missing-module-docstring, missing-function-docstring
from logging import Logger

from custom_components.hacs.utils.logger import get_hacs_logger


def test_logger():
    hacs_logger = get_hacs_logger()
    assert isinstance(hacs_logger, Logger)
