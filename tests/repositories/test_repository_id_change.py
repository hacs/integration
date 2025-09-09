"""Test repository ID change detection."""

import pytest

from custom_components.hacs.exceptions import HacsRepositoryIdChangedException
from custom_components.hacs.repositories.base import RepositoryData


async def test_repository_id_change_detection():
    """Test that repository ID changes are detected and handled properly."""
    # Create a repository data object with an existing ID
    repo_data = RepositoryData()
    repo_data.id = "12345"
    repo_data.full_name = "test/repository"
    
    # Try to update with a different ID - should raise exception
    github_data = {
        "id": 67890,  # Different ID
        "name": "repository",
        "full_name": "test/repository"
    }
    
    with pytest.raises(HacsRepositoryIdChangedException) as exc_info:
        repo_data.update_data(github_data)
    
    # Check the exception message contains the correct information
    assert "test/repository" in str(exc_info.value)
    assert "12345" in str(exc_info.value)
    assert "67890" in str(exc_info.value)
    
    # Ensure the ID wasn't changed
    assert repo_data.id == "12345"


async def test_repository_id_same_no_exception():
    """Test that updating with the same ID doesn't raise exception."""
    # Create a repository data object with an existing ID
    repo_data = RepositoryData()
    repo_data.id = "12345"
    repo_data.full_name = "test/repository"
    
    # Try to update with the same ID - should not raise exception
    github_data = {
        "id": 12345,  # Same ID
        "name": "repository", 
        "full_name": "test/repository"
    }
    
    # Should not raise exception
    repo_data.update_data(github_data)
    
    # ID should remain the same
    assert repo_data.id == "12345"


async def test_repository_id_new_no_exception():
    """Test that setting ID for the first time doesn't raise exception."""
    # Create a repository data object with default ID (0)
    repo_data = RepositoryData()
    assert repo_data.id == 0
    
    # Set ID for the first time - should not raise exception
    github_data = {
        "id": 12345,
        "name": "repository",
        "full_name": "test/repository"
    }
    
    # Should not raise exception
    repo_data.update_data(github_data)
    
    # ID should be set
    assert repo_data.id == "12345"