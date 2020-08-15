"""Helpers: Download: should_try_releases."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.download import should_try_releases
from tests.dummy_repository import dummy_repository_base


def test_base(hass):
    repository = dummy_repository_base(hass)
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert should_try_releases(repository)


def test_ref_is_default(hass):
    repository = dummy_repository_base(hass)
    repository.ref = "main"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert not should_try_releases(repository)


def test_category_is_wrong(hass):
    repository = dummy_repository_base(hass)
    repository.ref = "dummy"
    repository.data.category = "integration"
    repository.data.releases = True
    assert not should_try_releases(repository)


def test_no_releases(hass):
    repository = dummy_repository_base(hass)
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = False
    assert not should_try_releases(repository)


def test_zip_release(hass):
    repository = dummy_repository_base(hass)
    repository.data.releases = False
    repository.data.zip_release = True
    repository.data.filename = "test.zip"
    assert should_try_releases(repository)

    # Select a branch
    repository.ref = "main"
    assert not should_try_releases(repository)
