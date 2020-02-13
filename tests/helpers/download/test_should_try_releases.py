"""Helpers: Download: should_try_releases."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.download import should_try_releases
from tests.dummy_repository import dummy_repository_base


def test_base():
    repository = dummy_repository_base()
    repository.ref = "dummy"
    repository.information.category = "plugin"
    repository.releases.releases = True
    assert should_try_releases(repository)


def test_ref_is_default():
    repository = dummy_repository_base()
    repository.ref = "master"
    repository.information.category = "plugin"
    repository.releases.releases = True
    assert not should_try_releases(repository)


def test_category_is_wrong():
    repository = dummy_repository_base()
    repository.ref = "dummy"
    repository.information.category = "integration"
    repository.releases.releases = True
    assert not should_try_releases(repository)


def test_no_releases():
    repository = dummy_repository_base()
    repository.ref = "dummy"
    repository.information.category = "plugin"
    repository.releases.releases = False
    assert not should_try_releases(repository)
