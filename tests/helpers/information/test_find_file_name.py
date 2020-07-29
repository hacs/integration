"""Helpers: Install: find_file_name."""
# pylint: disable=missing-docstring
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
from aiogithubapi.objects.repository.release import AIOGitHubAPIRepositoryRelease

from custom_components.hacs.helpers.functions.information import find_file_name
from tests.dummy_repository import (
    dummy_repository_plugin,
    dummy_repository_python_script,
    dummy_repository_theme,
)


def test_find_file_name_base():
    repository = dummy_repository_plugin()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "test.js", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == ""


def test_find_file_name_root():
    repository = dummy_repository_plugin()
    repository.data.content_in_root = True
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "test.js", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == ""


def test_find_file_name_dist():
    repository = dummy_repository_plugin()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "dist/test.js", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == "dist"


def test_find_file_name_different_name():
    repository = dummy_repository_plugin()
    repository.data.filename = "card.js"
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "card.js", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "card.js"
    assert repository.content.path.remote == ""


def test_find_file_release():
    repository = dummy_repository_plugin()
    repository.releases.objects = [
        AIOGitHubAPIRepositoryRelease(
            {"tag_name": "3", "assets": [{"name": "test.js"}]}
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == "release"


def test_find_file_release_no_asset():
    repository = dummy_repository_plugin()
    repository.releases.objects = [
        AIOGitHubAPIRepositoryRelease({"tag_name": "3", "assets": []})
    ]
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "test.js", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == ""


def test_find_file_name_base_theme():
    repository = dummy_repository_theme()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "themes/test.yaml", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.yaml"
    assert repository.data.name == "test"


def test_find_file_name_base_python_script():
    repository = dummy_repository_python_script()
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "python_scripts/test.py", "type": "blob"}, "test/test", "main"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.py"
    assert repository.data.name == "test"
