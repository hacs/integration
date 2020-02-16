"""Helpers: Filters: get_first_directory_in_directory."""
# pylint: disable=missing-docstring
from aiogithubapi.content import AIOGithubTreeContent
from custom_components.hacs.helpers.filters import get_first_directory_in_directory


def test_valid():
    tree = [
        AIOGithubTreeContent({"path": "test", "type": "tree"}, "test/test", "master"),
        AIOGithubTreeContent(
            {"path": "test/path", "type": "tree"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "test/path/sub", "type": "tree"}, "test/test", "master"
        ),
    ]
    assert get_first_directory_in_directory(tree, "test") == "path"


def test_not_valid():
    tree = [
        AIOGithubTreeContent(
            {"path": ".github/path/file.file", "type": "tree"}, "test/test", "master"
        )
    ]
    assert get_first_directory_in_directory(tree, "test") is None
