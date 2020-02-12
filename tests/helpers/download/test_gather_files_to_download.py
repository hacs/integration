"""Helpers: Download: reload_after_install."""
# pylint: disable=missing-docstring
from aiogithubapi.content import AIOGithubTreeContent

from custom_components.hacs.helpers.download import gather_files_to_download
from tests.dummy_repository import dummy_repository_base, dummy_repository_plugin


def test_gather_files_to_download():
    repository = dummy_repository_base()
    repository.content.path.remote = ""
    dummyfile = {"path": "test/path/file.file", "type": "blob"}
    repository.tree = [AIOGithubTreeContent(dummyfile, "test/test", "master")]
    files = [x.path for x in gather_files_to_download(repository)]
    assert "test/path/file.file" in files


def test_gather_plugin_files_from_root():
    repository = dummy_repository_plugin()
    repository.content.path.remote = ""
    repository.information.file_name = "test.js"
    dummyfile = {"path": "test.js", "type": "blob"}
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "test.js", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent({"path": "dir", "type": "tree"}, "test/test", "master"),
        AIOGithubTreeContent(
            {"path": "aaaa.js", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "dist/test.js", "type": "blob"}, "test/test", "master"
        ),
    ]
    files = [x.path for x in gather_files_to_download(repository)]
    assert "test.js" in files
    assert "dir" not in files
    assert "aaaa.js" not in files
    assert "dist/test.js" not in files


def test_gather_plugin_files_from_dist():
    repository = dummy_repository_plugin()
    repository.content.path.remote = "dist"
    repository.information.file_name = "test.js"
    dummyfile = {"path": "test.js", "type": "blob"}
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "test.js", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "dist/image.png", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "dist/test.js", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "dist/subdir", "type": "tree"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "dist/subdir/file.file", "type": "blob"}, "test/test", "master"
        ),
    ]
    files = [x.path for x in gather_files_to_download(repository)]
    assert "test.js" not in files
    assert "dist/image.png" in files
    assert "dist/subdir/file.file" in files
    assert "dist/subdir" not in files
    assert "dist/test.js" in files

