"""HACS Repository Data Test Suite."""
# pylint: disable=missing-docstring
from custom_components.hacs.base import RemovedRepository


def test_data_update():
    repo = RemovedRepository()
    repo.update_data({"repository": "test/test"})
    assert repo.repository == "test/test"
