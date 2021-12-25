"""HACS Repository Helper properties."""
# pylint: disable=missing-docstring
from awesomeversion import AwesomeVersion

from custom_components.hacs.repositories.base import HacsRepository


def test_repository_helpers_properties_can_be_installed(hacs):
    repository = HacsRepository(hacs)
    assert repository.can_download


def test_repository_helpers_properties_pending_update(hacs):
    repository = HacsRepository(hacs)
    repository.hacs.core.ha_version = AwesomeVersion("0.109.0")
    repository.data.homeassistant = "0.110.0"
    repository.data.releases = True
    assert not repository.pending_update

    repository = HacsRepository(hacs)
    repository.data.installed = True
    repository.data.default_branch = "main"
    repository.data.selected_tag = "main"
    assert not repository.pending_update

    repository.data.installed_commit = "1"
    repository.data.last_commit = "2"
    assert repository.pending_update
