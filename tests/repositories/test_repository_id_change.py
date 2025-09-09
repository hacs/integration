"""Repository Test Suite: ID change detection."""
# pylint: disable=missing-docstring
import pytest

from custom_components.hacs.exceptions import HacsRepositoryIdChangedException


def test_repository_id_change_detection_generator_mode(repository):
    """Test that repository ID changes are detected and handled properly in generator mode."""
    # Set up the repository with an existing ID and enable generator mode
    repository.data.id = "12345"
    repository.data.full_name = "test/repository"
    repository.hacs.system.generator = True

    # Try to update with a different ID - should raise exception
    github_data = {
        "id": 67890,  # Different ID
        "name": "repository",
        "full_name": "test/repository"
    }

    with pytest.raises(HacsRepositoryIdChangedException) as exc_info:
        repository.data.update_data(github_data)

    # Check the exception message contains the correct information
    assert "test/repository" in str(exc_info.value)
    assert "12345" in str(exc_info.value)
    assert "67890" in str(exc_info.value)

    # Ensure the ID wasn't changed
    assert repository.data.id == "12345"


def test_repository_id_same_no_exception_generator_mode(repository):
    """Test that updating with the same ID doesn't raise exception in generator mode."""
    # Set up the repository with an existing ID and enable generator mode
    repository.data.id = "12345"
    repository.data.full_name = "test/repository"
    repository.hacs.system.generator = True

    # Try to update with the same ID - should not raise exception
    github_data = {
        "id": 12345,  # Same ID (as integer)
        "name": "repository",
        "full_name": "test/repository"
    }

    # Should not raise exception
    repository.data.update_data(github_data)

    # ID should remain the same
    assert repository.data.id == "12345"


def test_repository_id_new_no_exception_generator_mode(repository):
    """Test that setting ID for the first time doesn't raise exception in generator mode."""
    # Set up the repository with default ID (0) and enable generator mode
    repository.data.id = "0"
    repository.hacs.system.generator = True

    # Set ID for the first time - should not raise exception
    github_data = {
        "id": 12345,
        "name": "repository",
        "full_name": "test/repository"
    }

    # Should not raise exception
    repository.data.update_data(github_data)

    # ID should be set
    assert repository.data.id == "12345"


def test_repository_id_change_no_generator_mode(repository):
    """Test that ID changes are ignored when not in generator mode."""
    # Set up the repository with an existing ID but disable generator mode
    repository.data.id = "12345"
    repository.data.full_name = "test/repository"
    repository.hacs.system.generator = False

    # Try to update with a different ID - should NOT raise exception when not in generator mode
    github_data = {
        "id": 67890,  # Different ID
        "name": "repository",
        "full_name": "test/repository"
    }

    # Should not raise exception since generator is False
    repository.data.update_data(github_data)

    # ID should be updated since generator mode is disabled
    assert repository.data.id == "67890"


def test_repository_id_change_no_id_in_data_generator_mode(repository):
    """Test that updates without ID don't raise exception in generator mode."""
    # Set up the repository with an existing ID and enable generator mode
    repository.data.id = "12345"
    repository.data.full_name = "test/repository"
    repository.hacs.system.generator = True

    # Try to update without ID in data - should not raise exception
    github_data = {
        "name": "repository",
        "full_name": "test/repository"
        # No "id" key
    }

    # Should not raise exception since no ID in data
    repository.data.update_data(github_data)

    # ID should remain unchanged
    assert repository.data.id == "12345"


def test_repository_id_string_vs_int_comparison(repository):
    """Test that string and integer IDs are compared correctly."""
    # Set up the repository with string ID and enable generator mode
    repository.data.id = "12345"
    repository.data.full_name = "test/repository"
    repository.hacs.system.generator = True

    # Try to update with same ID as integer - should not raise exception
    github_data = {
        "id": 12345,  # Same ID as integer
        "name": "repository",
        "full_name": "test/repository"
    }

    # Should not raise exception since IDs are the same when converted to string
    repository.data.update_data(github_data)

    # ID should remain as string
    assert repository.data.id == "12345"
