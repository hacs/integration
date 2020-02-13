"""HACS Repository Data Test Suite."""
# pylint: disable=missing-docstring
from tests.sample_data import repository_data
from custom_components.hacs.repositories.data import RepositoryData


def test_data_structure():
    data = RepositoryData.from_dict(repository_data)
    assert isinstance(data.to_json(), dict)
