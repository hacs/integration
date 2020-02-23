"""Data Test Suite."""
# pylint: disable=missing-docstring
from custom_components.hacs.repositories.repository import HacsRepository
from custom_components.hacs.hacsbase.data import restore_repository_data


def test_restore_repository_data():
    repo = HacsRepository()
    data = {"description": "test", "installed": True, "full_name": "hacs/integration"}
    restore_repository_data(repo, data)
    assert repo.data.description == "test"
