from custom_components.hacs.base import RemovedRepository


def test_removed():
    removed = RemovedRepository()
    assert isinstance(removed.to_json(), dict)
