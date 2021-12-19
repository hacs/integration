"""Configuration Test Suite: Core repository."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.classes.repository import HacsRepository


def test_hacs_repository_core_mostly_defaults():
    repository = HacsRepository()

    repository.data.full_name = "developer/repository"
    repository.data.full_name_lower = "developer/repository"
    repository.data.default_branch = "main"
    repository.data.description = "Awesome GitHub repository"

    assert repository.display_name == "Repository"
    assert repository.display_status == "new"
    assert repository.display_status_description == "This is a newly added repository."
    assert repository.main_action == "INSTALL"
    assert repository.display_version_or_commit == "commit"
    assert repository.display_available_version == ""
    assert repository.display_installed_version == ""
    assert repository.can_install
    assert not repository.pending_upgrade


def test_hacs_repository_core_can_install_legacy():
    repository = HacsRepository()
    repository.hacs.core.ha_version = "1.0.0"
    repository.data.releases = True

    repository.data.homeassistant = "1.1.0"
    assert not repository.can_install

    repository.data.homeassistant = "1.0.0"
    assert repository.can_install

    repository.data.homeassistant = "0.1.0"
    assert repository.can_install


def test_hacs_repository_core_can_install_manifest():
    repository = HacsRepository()
    repository.hacs.core.ha_version = "1.0.0"
    repository.data.releases = True

    repository.data.homeassistant = "1.1.0"
    assert not repository.can_install

    repository.data.homeassistant = "1.0.0"
    assert repository.can_install

    repository.data.homeassistant = "0.1.0"
    assert repository.can_install
