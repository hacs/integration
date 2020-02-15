"""Helpers: Filters: find_first_of_filetype."""
# pylint: disable=missing-docstring
from aiogithubapi.content import AIOGithubTreeContent
from custom_components.hacs.helpers.filters import find_first_of_filetype


def test_valid_objects():
    tree = [
        AIOGithubTreeContent(
            {"path": "test/path/file.file", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "test/path/sub", "type": "blob"}, "test/test", "master"
        ),
    ]
    assert find_first_of_filetype(tree, "file", "filename") == "file.file"


def test_valid_list():
    tree = ["file.file", "test/path/sub/test.file"]
    assert find_first_of_filetype(tree, "file", "filename") == "file.file"


def test_not_valid():
    tree = [
        AIOGithubTreeContent(
            {"path": ".github/path/file.yaml", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": ".github/path/file.js", "type": "blob"}, "test/test", "master"
        ),
    ]
    assert not find_first_of_filetype(tree, "file", "filename")
