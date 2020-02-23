"""Helpers: Install: find_file_name."""
# pylint: disable=missing-docstring
from aiogithubapi.content import AIOGithubTreeContent
from aiogithubapi.release import AIOGithubRepositoryRelease
from tests.dummy_repository import (
    dummy_repository_plugin,
    dummy_repository_theme,
    dummy_repository_python_script,
)
from custom_components.hacs.helpers.information import find_file_name


def test_find_file_name_base():
    repository = dummy_repository_plugin()
    repository.tree = [
        AIOGithubTreeContent({"path": "test.js", "type": "blob"}, "test/test", "master")
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == ""


def test_find_file_name_root():
    repository = dummy_repository_plugin()
    repository.data.content_in_root = True
    repository.tree = [
        AIOGithubTreeContent({"path": "test.js", "type": "blob"}, "test/test", "master")
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == ""


def test_find_file_name_dist():
    repository = dummy_repository_plugin()
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "dist/test.js", "type": "blob"}, "test/test", "master"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == "dist"


def test_find_file_name_different_name():
    repository = dummy_repository_plugin()
    repository.data.filename = "card.js"
    repository.tree = [
        AIOGithubTreeContent({"path": "card.js", "type": "blob"}, "test/test", "master")
    ]
    find_file_name(repository)
    assert repository.data.file_name == "card.js"
    assert repository.content.path.remote == ""


def test_find_file_release():
    repository = dummy_repository_plugin()
    repository.releases.objects = [
        AIOGithubRepositoryRelease({"tag_name": "3", "assets": [{"name": "test.js"}]})
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == "release"


def test_find_file_release_no_asset():
    repository = dummy_repository_plugin()
    repository.releases.objects = [
        AIOGithubRepositoryRelease({"tag_name": "3", "assets": []})
    ]
    repository.tree = [
        AIOGithubTreeContent({"path": "test.js", "type": "blob"}, "test/test", "master")
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.js"
    assert repository.content.path.remote == ""


def test_find_file_name_base_theme():
    repository = dummy_repository_theme()
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "themes/test.yaml", "type": "blob"}, "test/test", "master"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.yaml"
    assert repository.data.name == "test"


def test_find_file_name_base_python_script():
    repository = dummy_repository_python_script()
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "python_scripts/test.py", "type": "blob"}, "test/test", "master"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "test.py"
    assert repository.data.name == "test"


def test_find_file_name_base_theme_set():
    repository = dummy_repository_theme()
    repository.data.name = None
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "themes/file.yaml", "type": "blob"}, "test/test", "master"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "file.yaml"
    assert repository.data.name == "file"


def test_find_file_name_base_python_script_set():
    repository = dummy_repository_python_script()
    repository.data.name = None
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "python_scripts/file.py", "type": "blob"}, "test/test", "master"
        )
    ]
    find_file_name(repository)
    assert repository.data.file_name == "file.py"
    assert repository.data.name == "file"
