"""Configuration Test Suite: Core repository."""
# pylint: disable=missing-docstring
from awesomeversion import AwesomeVersion

from custom_components.hacs.repositories.base import HacsRepository


def test_hacs_repository_core_mostly_defaults(hacs):
    repository = HacsRepository(hacs)

    repository.data.full_name = "developer/repository"
    repository.data.full_name_lower = "developer/repository"
    repository.data.default_branch = "main"
    repository.data.description = "Awesome GitHub repository"

    assert repository.display_name == "Repository"
    assert repository.display_status == "new"
    assert repository.display_version_or_commit == "commit"
    assert repository.display_available_version == ""
    assert repository.display_installed_version == ""
    assert repository.can_download
    assert not repository.pending_update


def test_hacs_repository_core_can_install_legacy(hacs):
    repository = HacsRepository(hacs)
    repository.hacs.core.ha_version = AwesomeVersion("1.0.0")
    repository.data.releases = True

    repository.repository_manifest.homeassistant = "1.1.0"
    assert not repository.can_download

    repository.repository_manifest.homeassistant = "1.0.0"
    assert repository.can_download

    repository.repository_manifest.homeassistant = "0.1.0"
    assert repository.can_download


def test_hacs_repository_core_can_install_manifest(hacs):
    repository = HacsRepository(hacs)
    repository.hacs.core.ha_version = AwesomeVersion("1.0.0")
    repository.data.releases = True

    repository.repository_manifest.homeassistant = "1.1.0"
    assert not repository.can_download

    repository.repository_manifest.homeassistant = "1.0.0"
    assert repository.can_download

    repository.repository_manifest.homeassistant = "0.1.0"
    assert repository.can_download
