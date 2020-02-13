"""Helpers: Download: reload_after_install."""
# pylint: disable=missing-docstring
from aiogithubapi.content import AIOGithubTreeContent
from aiogithubapi.release import AIOGithubRepositoryRelease

from custom_components.hacs.helpers.download import gather_files_to_download
from tests.dummy_repository import (
    dummy_repository_base,
    dummy_repository_plugin,
    dummy_repository_theme,
)


def test_gather_files_to_download():
    repository = dummy_repository_base()
    repository.content.path.remote = ""
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "test/path/file.file", "type": "blob"}, "test/test", "master"
        )
    ]
    files = [x.path for x in gather_files_to_download(repository)]
    assert "test/path/file.file" in files


def test_gather_plugin_files_from_root():
    repository = dummy_repository_plugin()
    repository.content.path.remote = ""
    repository.information.file_name = "test.js"
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


def test_gather_plugin_files_from_release():
    repository = dummy_repository_plugin()
    repository.information.file_name = "test.js"
    repository.releases.releases = True
    release = AIOGithubRepositoryRelease(
        {"tag_name": "3", "assets": [{"name": "test.js"}]}
    )
    repository.releases.objects = [release]
    files = [x.name for x in gather_files_to_download(repository)]
    assert "test.js" in files


def test_gather_zip_release():
    repository = dummy_repository_plugin()
    repository.information.file_name = "test.zip"
    repository.repository_manifest.zip_release = True
    repository.repository_manifest.filename = "test.zip"
    repository.releases.objects = [
        AIOGithubRepositoryRelease({"tag_name": "3", "assets": [{"name": "test.zip"}]})
    ]
    files = [x.name for x in gather_files_to_download(repository)]
    assert "test.zip" in files


def test_gather_content_in_root_theme():
    repository = dummy_repository_theme()
    repository.repository_manifest.content_in_root = True
    repository.tree = [
        AIOGithubTreeContent(
            {"path": "test.yaml", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent({"path": "dir", "type": "tree"}, "test/test", "master"),
        AIOGithubTreeContent(
            {"path": "test2.yaml", "type": "blob"}, "test/test", "master"
        ),
        AIOGithubTreeContent(
            {"path": "readme.md", "type": "blob"}, "test/test", "master"
        ),
    ]
    files = [x.path for x in gather_files_to_download(repository)]
    assert "readme.md" not in files
    assert "test2.yaml" not in files
    assert "test.yaml" not in files