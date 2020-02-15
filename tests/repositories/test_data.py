"""HACS Repository Data Test Suite."""
# pylint: disable=missing-docstring
from tests.sample_data import repository_data
from custom_components.hacs.repositories.repositorydata import RepositoryData


def test_data_structure():
    data = RepositoryData.create_from_dict(repository_data)
    assert isinstance(data.to_json(), dict)

    assert not data.fork
    data.update_data({"fork": True})
    assert data.fork
