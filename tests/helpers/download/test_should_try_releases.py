"""Helpers: Download: should_try_releases."""
# pylint: disable=missing-docstring
from custom_components.hacs.utils.download import should_try_releases


def test_base(repository):
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert should_try_releases(repository)


def test_ref_is_default(repository):
    repository.ref = "main"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert not should_try_releases(repository)


def test_category_is_wrong(repository):
    repository.ref = "dummy"
    repository.data.category = "integration"
    repository.data.releases = True
    assert not should_try_releases(repository)


def test_no_releases(repository):
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = False
    assert not should_try_releases(repository)


def test_zip_release(repository):
    repository.data.releases = False
    repository.data.zip_release = True
    repository.data.filename = "test.zip"
    assert should_try_releases(repository)

    # Select a branch
    repository.ref = "main"
    assert not should_try_releases(repository)
