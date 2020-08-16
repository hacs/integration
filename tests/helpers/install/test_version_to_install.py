"""Helpers: Install: version_to_install."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.version_to_install import (
    version_to_install,
)


def test_version_to_install(repository):
    repository.data.selected_tag = "main"
    assert version_to_install(repository) == "main"

    repository.data.default_branch = None
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert version_to_install(repository) == "main"

    repository.data.selected_tag = "2"
    assert version_to_install(repository) == "2"

    repository.data.selected_tag = None
    repository.data.last_version = "3"
    assert version_to_install(repository) == "3"

    repository.data.selected_tag = None
    repository.data.last_version = None
    assert version_to_install(repository) == "main"

    repository.data.selected_tag = "2"
    repository.data.last_version = None
    assert version_to_install(repository) == "2"

    repository.data.selected_tag = "main"
    repository.data.last_version = None
    assert version_to_install(repository) == "main"

    repository.data.selected_tag = "3"
    repository.data.last_version = "3"
    version_to_install(repository)
    assert repository.data.selected_tag is None

    repository.data.default_branch = "dev"
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert version_to_install(repository) == "dev"

    repository.data.default_branch = "main"
    repository.data.last_version = "2"
    assert version_to_install(repository) == "2"
