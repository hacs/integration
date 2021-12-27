import os

from custom_components.hacs.utils.logger import get_hacs_logger


def test_logger():
    os.environ["GITHUB_ACTION"] = "value"
    get_hacs_logger()
    del os.environ["GITHUB_ACTION"]
