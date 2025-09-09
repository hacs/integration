"""Test ID change handling in data generator."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hacs.exceptions import HacsRepositoryIdChangedException
from scripts.data.generate_category_data import AdjustedHacs, AdjustedHacsData


class MockRepository:
    """Mock repository for testing."""

    def __init__(self, repo_id="12345", full_name="test/repository"):
        self.data = Mock()
        self.data.id = repo_id
        self.data.full_name = full_name
        self.data.category = "integration"
        self.data.archived = False
        self.data._id_changed = False
        self.logger = Mock()
        self.string = f"<Repository {full_name}>"

    def __getattr__(self, name):
        return Mock()


@pytest.mark.asyncio
async def test_concurrent_update_repository_handles_id_change():
    """Test that concurrent_update_repository handles ID changes properly."""
    # Create mock repository
    repository = MockRepository()
    
    # Create AdjustedHacs instance
    with patch("aiohttp.ClientSession"):
        hacs = AdjustedHacs(session=Mock(), token="test_token")
    
    # Mock the common_update to raise HacsRepositoryIdChangedException
    repository.common_update = AsyncMock(
        side_effect=HacsRepositoryIdChangedException("ID changed from 12345 to 67890")
    )
    
    # Call the method
    await hacs.concurrent_update_repository(repository)
    
    # Check that the repository was marked as having ID change
    assert repository.data._id_changed is True
    
    # Check that the error was logged
    repository.logger.error.assert_called_once()
    error_call = repository.logger.error.call_args
    assert "Repository ID has changed" in error_call[0][0]


@pytest.mark.asyncio
async def test_store_repository_data_stores_id_changed():
    """Test that async_store_repository_data stores repositories with ID changes (preserving old data)."""
    # Create mock repository with ID change flag
    repository = MockRepository()
    repository.data._id_changed = True
    repository.repository_manifest = Mock()
    repository.data.last_fetched = None
    
    # Mock the required attributes
    with patch("scripts.data.generate_category_data.repository_has_missing_keys", return_value=False):
        with patch("scripts.data.generate_category_data.HACS_MANIFEST_KEYS_TO_EXPORT", []):
            with patch("scripts.data.generate_category_data.REPOSITORY_KEYS_TO_EXPORT", []):
                # Create AdjustedHacsData instance
                with patch("aiohttp.ClientSession"):
                    hacs = AdjustedHacs(session=Mock(), token="test_token")
                
                hacs_data = AdjustedHacsData(hacs=hacs)
                
                # Store repository data
                hacs_data.async_store_repository_data(repository)
                
                # Check that old data was still stored despite ID change
                assert len(hacs_data.content) == 1
                assert "12345" in hacs_data.content


@pytest.mark.asyncio  
async def test_store_repository_data_stores_normal():
    """Test that async_store_repository_data stores normal repositories."""
    # Create mock repository without ID change flag
    repository = MockRepository()
    repository.repository_manifest = Mock()
    repository.data.last_fetched = None
    
    # Mock the required attributes
    with patch("scripts.data.generate_category_data.repository_has_missing_keys", return_value=False):
        with patch("scripts.data.generate_category_data.HACS_MANIFEST_KEYS_TO_EXPORT", []):
            with patch("scripts.data.generate_category_data.REPOSITORY_KEYS_TO_EXPORT", []):
                # Create AdjustedHacsData instance
                with patch("aiohttp.ClientSession"):
                    hacs = AdjustedHacs(session=Mock(), token="test_token")
                
                hacs_data = AdjustedHacsData(hacs=hacs)
                
                # Store repository data
                hacs_data.async_store_repository_data(repository)
                
                # Check that data was stored
                assert len(hacs_data.content) == 1
                assert "12345" in hacs_data.content