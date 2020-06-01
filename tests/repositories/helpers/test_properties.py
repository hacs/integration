"""HACS Repository Helper properties."""
# pylint: disable=missing-docstring
from custom_components.hacs.repositories.repository import HacsRepository


def test_repository_helpers_properties_can_be_installed():
    repository = HacsRepository()
    assert repository.can_be_installed


def test_repository_helpers_properties_custom():
    repository = HacsRepository()
    repository.data.full_name = "custom-components/test"
    assert not repository.custom

    repository.data.full_name = "test/test"
    assert repository.custom

    repository.data.id = 1337
    repository.hacs.common.default.append(repository.data.id)
    assert not repository.custom

    repository.hacs.common.default = []
    assert repository.custom

    repository.data.full_name = "hacs/integration"
    assert not repository.custom


def test_repository_helpers_properties_pending_update():
    repository = HacsRepository()
    repository.hacs.system.ha_version = "0.109.0"
    repository.data.homeassistant = "0.110.0"
    repository.data.releases = True
    assert not repository.pending_update

    repository = HacsRepository()
    repository.data.installed = True
    repository.data.default_branch = "master"
    repository.data.selected_tag = "master"
    assert not repository.pending_update

    repository.data.installed_commit = "1"
    repository.data.last_commit = "2"
    assert repository.pending_update
