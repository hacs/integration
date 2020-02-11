"""Helpers: Download: reload_after_install."""
# pylint: disable=missing-docstring
from aiogithubapi.content import AIOGithubTreeContent

from custom_components.hacs.helpers.download import (
    gather_files_to_download,
    FileInformation,
)
from tests.dummy_repository import dummy_repository_base


def test_gather_files_to_download():
    repository = dummy_repository_base()
    repository.content.path.remote = ""
    dummyfile = {"path": "test/path/file.file", "type": "blob"}
    repository.tree = [AIOGithubTreeContent(dummyfile, "test/test", "master")]
    files = gather_files_to_download(repository)
    assert files[0].name == "file.file"

