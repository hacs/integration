"""HACS Repository Data Test Suite."""
# pylint: disable=missing-docstring
from custom_components.hacs.base import RemovedRepository


def test_data_update():
    repo = RemovedRepository()
    assert repo.reason is None
    repo.update_data({"reason": "test"})
    assert repo.reason == "test"
