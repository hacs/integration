"""Helpers: Install: find_file_name."""
# pylint: disable=missing-docstring
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
from aiogithubapi.objects.repository.release import AIOGitHubAPIRepositoryRelease


def test_find_file_name_base(repository_plugin):
    repository_plugin.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "test.js", "type": "blob"}, "test/test", "main")
    ]
    repository_plugin.update_filenames()
    assert repository_plugin.data.file_name == "test.js"
    assert repository_plugin.content.path.remote == ""


def test_find_file_name_root(repository_plugin):
    repository_plugin.data.content_in_root = True
    repository_plugin.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "test.js", "type": "blob"}, "test/test", "main")
    ]
    repository_plugin.update_filenames()
    assert repository_plugin.data.file_name == "test.js"
    assert repository_plugin.content.path.remote == ""


def test_find_file_name_dist(repository_plugin):
    repository_plugin.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "dist/test.js", "type": "blob"}, "test/test", "main"
        )
    ]
    repository_plugin.update_filenames()
    assert repository_plugin.data.file_name == "test.js"
    assert repository_plugin.content.path.remote == "dist"


def test_find_file_name_different_name(repository_plugin):
    repository_plugin.data.filename = "card.js"
    repository_plugin.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "card.js", "type": "blob"}, "test/test", "main")
    ]
    repository_plugin.update_filenames()
    assert repository_plugin.data.file_name == "card.js"
    assert repository_plugin.content.path.remote == ""


def test_find_file_release(repository_plugin):
    repository_plugin.releases.objects = [
        AIOGitHubAPIRepositoryRelease({"tag_name": "3", "assets": [{"name": "test.js"}]})
    ]
    repository_plugin.update_filenames()
    assert repository_plugin.data.file_name == "test.js"
    assert repository_plugin.content.path.remote == "release"


def test_find_file_release_no_asset(repository_plugin):
    repository_plugin.releases.objects = [
        AIOGitHubAPIRepositoryRelease({"tag_name": "3", "assets": []})
    ]
    repository_plugin.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "test.js", "type": "blob"}, "test/test", "main")
    ]
    repository_plugin.update_filenames()
    assert repository_plugin.data.file_name == "test.js"
    assert repository_plugin.content.path.remote == ""


def test_find_file_name_base_theme(repository_theme):
    repository_theme.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "themes/test.yaml", "type": "blob"}, "test/test", "main"
        )
    ]
    repository_theme.update_filenames()
    assert repository_theme.data.file_name == "test.yaml"
    assert repository_theme.data.name == "test"


def test_find_file_name_base_python_script(repository_python_script):
    repository_python_script.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "python_scripts/test.py", "type": "blob"}, "test/test", "main"
        )
    ]
    repository_python_script.update_filenames()
    assert repository_python_script.data.file_name == "test.py"
    assert repository_python_script.data.name == "test"
