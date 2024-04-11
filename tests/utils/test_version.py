"""Tests for the version util functions."""
import pytest

from custom_components.hacs.utils import version


def test_version_to_download(repository):
    """Test version_to_download."""
    repository.data.selected_tag = "main"
    assert repository.version_to_download() == "main"

    repository.data.default_branch = None
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert repository.version_to_download() == "main"

    repository.data.selected_tag = "2"
    assert repository.version_to_download() == "2"

    repository.data.selected_tag = None
    repository.data.last_version = "3"
    assert repository.version_to_download() == "3"

    repository.data.selected_tag = None
    repository.data.last_version = None
    assert repository.version_to_download() == "main"

    repository.data.selected_tag = "2"
    repository.data.last_version = None
    assert repository.version_to_download() == "2"

    repository.data.selected_tag = "main"
    repository.data.last_version = None
    assert repository.version_to_download() == "main"

    repository.data.selected_tag = "3"
    repository.data.last_version = "3"
    repository.version_to_download()
    assert repository.data.selected_tag is None

    repository.data.default_branch = "dev"
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert repository.version_to_download() == "dev"

    repository.data.default_branch = "main"
    repository.data.last_version = "2"
    assert repository.version_to_download() == "2"

    repository.data.default_branch = "main"
    repository.data.selected_tag = "main"
    repository.data.last_version = None
    assert repository.version_to_download() == "main"


@pytest.mark.parametrize(
    "left, right, expected",
    [
        ("1.0.0", "0.9.9", True),
        ("1", "0.9.9", True),
        ("1.1", "0.9.9", True),
        ("0.10.0", "0.9.9", True),
        ("0.0.10", "0.9.9", False),
        ("0.9.0", "0.9.9", False),
        ("1.0.0", "1.0.0", True),
        ("1.0.0b1", "1.0.0b0", True),
        ("1.0.0b1", "1.0.0", False),
        ("1.0.0", "1.0.0b1", True),
        ("1.0.0rc1", "1.0.0b1", True),
        ("1.0.0a1", "1.0.0b1", False),
        ("1.0.0", "1.0.0a0", True),
        ("1.0.0", "1.0.0b0", True),
        ("1.0.0", "1.0.0rc0", True),
        ("0", "1.0.0rc0", False),
        ("", "1.0", None),
    ],
)
def test_version_left_higher_or_equal_then_right(left: str, right: str, expected: bool):
    """Test version_left_higher_or_equal_then_right."""
    assert version.version_left_higher_or_equal_then_right(left, right) == expected
