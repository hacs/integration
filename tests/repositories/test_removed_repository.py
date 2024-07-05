"""HACS Repository Data Test Suite."""
import pytest

from custom_components.hacs.base import RemovedRepository

BASE_DATA = {
    "repository": "remmoved/repository",
    "reason": None,
    "link": None,
    "removal_type": None,
    "acknowledged": False,
}


@pytest.mark.parametrize(
    "data",
    (
        {"removal_type": "remove"},
        {"reason": "Repository was removed from HACS"},
        {"link": "https://example.com/remmoved/repository"},
        {"acknowledged": True},
        {"acknowledged": False},
    ),
)
def test_removed_repository(data: dict[str, any]):
    """Test RemovedRepository."""
    removed = RemovedRepository(repository="remmoved/repository")
    assert removed.to_json() == BASE_DATA
    removed.update_data(data)
    assert removed.to_json() == {**BASE_DATA, **data}
