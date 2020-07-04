"""Data Test Suite."""
from custom_components.hacs.hacsbase.data import restore_repository_data

# pylint: disable=missing-docstring
from custom_components.hacs.helpers.classes.repository import HacsRepository


def test_restore_repository_data():
    repo = HacsRepository()
    data = {"description": "test", "installed": True, "full_name": "hacs/integration"}
    restore_repository_data(repo, data)
    assert repo.data.description == "test"
