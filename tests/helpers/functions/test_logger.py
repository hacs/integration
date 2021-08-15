import os

from custom_components.hacs.utils.logger import getLogger


def test_logger():
    os.environ["GITHUB_ACTION"] = "value"
    getLogger()
    del os.environ["GITHUB_ACTION"]
