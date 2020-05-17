"""Helpers: Install: version_to_install."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.install import version_to_install
from tests.dummy_repository import dummy_repository_base


def test_version_to_install():
    repository = dummy_repository_base()
    repository.data.selected_tag = "master"
    assert version_to_install(repository) == "master"

    repository = dummy_repository_base()
    repository.data.default_branch = None
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert version_to_install(repository) == "master"

    repository = dummy_repository_base()
    repository.data.selected_tag = "2"
    assert version_to_install(repository) == "2"

    repository = dummy_repository_base()
    repository.data.selected_tag = None
    assert version_to_install(repository) == "3"

    repository = dummy_repository_base()
    repository.data.selected_tag = None
    repository.data.last_version = None
    assert version_to_install(repository) == "master"

    repository = dummy_repository_base()
    repository.data.selected_tag = "2"
    repository.data.last_version = None
    assert version_to_install(repository) == "2"

    repository = dummy_repository_base()
    repository.data.selected_tag = "master"
    repository.data.last_version = None
    assert version_to_install(repository) == "master"

    repository = dummy_repository_base()
    repository.data.selected_tag = "3"
    repository.data.last_version = "3"
    version_to_install(repository)
    assert repository.data.selected_tag is None

    repository = dummy_repository_base()
    repository.data.default_branch = "dev"
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert version_to_install(repository) == "dev"
