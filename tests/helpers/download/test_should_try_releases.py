"""Helpers: Download: should_try_releases."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.download import should_try_releases
from tests.dummy_repository import dummy_repository_base


def test_base():
    repository = dummy_repository_base()
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert should_try_releases(repository)


def test_ref_is_default():
    repository = dummy_repository_base()
    repository.ref = "master"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert not should_try_releases(repository)


def test_category_is_wrong():
    repository = dummy_repository_base()
    repository.ref = "dummy"
    repository.data.category = "integration"
    repository.data.releases = True
    assert not should_try_releases(repository)


def test_no_releases():
    repository = dummy_repository_base()
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = False
    assert not should_try_releases(repository)


def test_zip_release():
    repository = dummy_repository_base()
    repository.data.releases = False
    repository.data.zip_release = True
    repository.data.filename = "test.zip"
    assert should_try_releases(repository)

    # Select a branch
    repository.ref = "master"
    assert not should_try_releases(repository)
