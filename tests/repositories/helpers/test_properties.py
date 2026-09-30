"""HACS Repository Helper properties."""
# pylint: disable=missing-docstring
from awesomeversion import AwesomeVersion
import pytest

from custom_components.hacs.repositories.base import HacsRepository


def test_repository_helpers_properties_can_be_installed(hacs):
    repository = HacsRepository(hacs)
    assert repository.can_download


def test_repository_helpers_properties_pending_update(hacs):
    repository = HacsRepository(hacs)
    repository.hacs.core.ha_version = AwesomeVersion("0.109.0")
    repository.repository_manifest.homeassistant = "0.110.0"
    repository.data.releases = True
    assert not repository.pending_update

    repository = HacsRepository(hacs)
    repository.data.installed = True
    repository.data.default_branch = "main"
    repository.data.selected_tag = "main"
    repository.data.releases = True
    repository.data.last_version = "0.2.0"
    assert not repository.pending_update

    repository.data.installed_commit = "1"
    repository.data.last_commit = "2"
    assert repository.pending_update


@pytest.mark.parametrize(
    ("installed_version", "installed_commit", "pending_update"),
    [
        (None, "3730b11", True),
        (None, "1234567", True),
        (None, "abcdef0", True),
        ("0.1.0", "3730b11", True),
        ("0.2.0", "3730b11", False),
        ("0.3.0", "3730b11", False),
    ],
)
def test_pending_update_with_releases(hacs, installed_version, installed_commit, pending_update):
    """Compare release versions without treating an installed commit as a version."""
    repository = HacsRepository(hacs)
    repository.data.installed = True
    repository.data.installed_version = installed_version
    repository.data.installed_commit = installed_commit
    repository.data.releases = True
    repository.data.last_version = "0.2.0"

    assert repository.pending_update is pending_update
