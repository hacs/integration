"""Helpers: Download: should_try_releases."""
# pylint: disable=missing-docstring


def test_base(repository):
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert repository.should_try_releases


def test_ref_is_default(repository):
    repository.ref = "main"
    repository.data.category = "plugin"
    repository.data.releases = True
    assert not repository.should_try_releases


def test_category_is_wrong(repository):
    repository.ref = "dummy"
    repository.data.category = "integration"
    repository.data.releases = True
    assert not repository.should_try_releases


def test_no_releases(repository):
    repository.ref = "dummy"
    repository.data.category = "plugin"
    repository.data.releases = False
    assert not repository.should_try_releases


def test_zip_release(repository):
    repository.data.releases = False
    repository.repository_manifest.zip_release = True
    repository.repository_manifest.filename = "test.zip"
    assert repository.should_try_releases

    # Select a branch
    repository.ref = "main"
    assert not repository.should_try_releases
