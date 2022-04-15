from custom_components.hacs.repositories.base import RepositoryData


def test_guarded():
    data = RepositoryData.create_from_dict({"full_name": "test"})
    assert data.name == "test"

    data.update_data({"name": "new"})
    assert data.name != "new"

    test = data.to_json()
    test["name"] = "new"

    assert data.name != "new"
