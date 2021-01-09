"""Helpers: Filters: get_first_directory_in_directory."""
# pylint: disable=missing-docstring
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.helpers.functions.filters import (
    get_first_directory_in_directory,
)


def test_valid():
    tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "test", "type": "tree"}, "test/test", "main"
        ),
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "test/path", "type": "tree"}, "test/test", "main"
        ),
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "test/path/sub", "type": "tree"}, "test/test", "main"
        ),
    ]
    assert get_first_directory_in_directory(tree, "test") == "path"


def test_not_valid():
    tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": ".github/path/file.file", "type": "tree"}, "test/test", "main"
        )
    ]
    assert get_first_directory_in_directory(tree, "test") is None
