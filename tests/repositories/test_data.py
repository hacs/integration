"""HACS Repository Data Test Suite."""
from custom_components.hacs.helpers.classes.repositorydata import RepositoryData

# pylint: disable=missing-docstring
from tests.sample_data import repository_data


def test_data_structure():
    data = RepositoryData.create_from_dict(repository_data)
    assert isinstance(data.to_json(), dict)


def test_data_update():
    data = RepositoryData.create_from_dict({})
    assert not data.fork
    data.update_data({"fork": True})
    assert data.fork
