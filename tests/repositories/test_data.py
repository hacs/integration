"""HACS Repository Data Test Suite."""
from custom_components.hacs.repositories.base import RepositoryData

# pylint: disable=missing-docstring
from tests.sample_data import repository_data


def test_data_structure():
    RepositoryData.create_from_dict({"pushed_at": ""})
    RepositoryData.create_from_dict({"country": ""})
    RepositoryData.create_from_dict({"country": [""]})
    RepositoryData.create_from_dict({"pushed_at": "1970-01-01T00:00:00"})
    data = RepositoryData.create_from_dict(repository_data)
    assert data.stars == 999
    assert isinstance(data.to_json(), dict)


def test_data_update():
    data = RepositoryData.create_from_dict({})
    assert not data.fork
    data.update_data({"fork": True})
    data.update_data({"pushed_at": "1970-01-01T00:00:00"})
    data.update_data({"country": ""})
    data.update_data({"country": [""]})
    data.update_data({"pushed_at": ""})
    assert data.fork
