import os
from custom_components.hacs.share import (
    SHARE,
    list_removed_repositories,
    get_hacs,
    SHARE,
)


def test_list_removed_repositories():
    list_removed_repositories()


def test_get_hacs():
    SHARE["hacs"] = None
    os.environ["GITHUB_ACTION"] = "value"
    get_hacs()
    SHARE["hacs"] = None
    del os.environ["GITHUB_ACTION"]
