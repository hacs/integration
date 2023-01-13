"""HACS Repository Data Test Suite."""
from custom_components.hacs.repositories.base import RepositoryData

# pylint: disable=missing-docstring
from tests.sample_data import repository_data


def test_data_structure():
    RepositoryData.create_from_dict({"country": ""})
    RepositoryData.create_from_dict({"country": [""]})
    data = RepositoryData.create_from_dict(repository_data)
    assert data.stargazers_count == 999
    assert isinstance(data.to_json(), dict)
