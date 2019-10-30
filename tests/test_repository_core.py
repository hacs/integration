"""Configuration Test Suite: Core repository."""
# pylint: disable=missing-docstring
import pytest
from custom_components.hacs.repositories.repository import HacsRepository
from custom_components.hacs.hacsbase.exceptions import HacsUserScrewupException

REPO = {
    "archived": False,
    "full_name": "developer/repository",
    "default_branch": "master",
    "description": "Awesome GitHub repository",
}


def test_hacs_repository_core_mostly_defaults():
    repository = HacsRepository()

    repository.information.full_name = REPO["full_name"]
    repository.information.default_branch = REPO["default_branch"]
    repository.information.name = repository.information.full_name.split("/")[1]
    repository.information.description = REPO["description"]

    assert repository.display_name == "Repository"
    assert repository.custom
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
    repository.system.ha_version = "1.0.0"
    repository.releases.releases = True

    repository.information.homeassistant_version = "1.1.0"
    assert not repository.can_install

    repository.information.homeassistant_version = "0.1.0"
    assert repository.can_install


def test_hacs_repository_core_can_install_manifest():
    repository = HacsRepository()
    repository.system.ha_version = "1.0.0"
    repository.releases.releases = True

    repository.repository_manifest.homeassistant = "1.1.0"
    assert not repository.can_install

    repository.repository_manifest.homeassistant = "0.1.0"
    assert repository.can_install
