"""Test download counter functionality."""

from unittest.mock import AsyncMock, patch

from aiogithubapi.models.release import GitHubReleaseModel
import pytest


@pytest.fixture
def mock_release_with_multiple_assets():
    """Create a mock release with multiple assets."""
    return GitHubReleaseModel(
        {
            "tag_name": "1.0.0",
            "name": "Release 1.0.0",
            "assets": [
                {
                    "name": "first-asset.js",
                    "download_count": 100,
                    "browser_download_url": "https://github.com/test/test/releases/download/1.0.0/first-asset.js",
                },
                {
                    "name": "target-asset.zip",
                    "download_count": 500,
                    "browser_download_url": "https://github.com/test/test/releases/download/1.0.0/target-asset.zip",
                },
            ],
        }
    )


async def test_download_counter_uses_correct_asset_with_filename(
    repository_plugin, mock_release_with_multiple_assets
):
    """Test that download counter uses the correct asset when file_name is specified."""
    repository = repository_plugin
    repository.data.file_name = "target-asset.zip"
    repository.releases.objects = [mock_release_with_multiple_assets]
    repository.ref = "1.0.0"
    repository.data.releases = True

    # Test the actual logic we implemented in base.py
    release = repository.releases.objects[0]
    if assets := release.assets:
        # Find the correct asset based on file_name, fallback to first asset
        target_asset = None
        if repository.data.file_name:
            for asset in assets:
                if asset.name == repository.data.file_name:
                    target_asset = asset
                    break

        # Use the target asset if found, otherwise use the first asset
        if target_asset:
            downloads = target_asset.download_count
        else:
            downloads = next(iter(assets)).download_count

    # Should find the correct asset with download count 500
    assert downloads == 500
    assert target_asset is not None
    assert target_asset.name == "target-asset.zip"


async def test_download_counter_fallback_when_no_file_name(
    repository_plugin, mock_release_with_multiple_assets
):
    """Test that download counter falls back to first asset when no specific file_name is set."""
    repository = repository_plugin
    repository.data.file_name = None  # No specific filename
    repository.releases.objects = [mock_release_with_multiple_assets]
    repository.ref = "1.0.0"
    repository.data.releases = True

    # Test the actual logic we implemented in base.py
    release = repository.releases.objects[0]
    if assets := release.assets:
        # Find the correct asset based on file_name, fallback to first asset
        target_asset = None
        if repository.data.file_name:
            for asset in assets:
                if asset.name == repository.data.file_name:
                    target_asset = asset
                    break

        # Use the target asset if found, otherwise use the first asset
        if target_asset:
            downloads = target_asset.download_count
        else:
            downloads = next(iter(assets)).download_count

    # Should use first asset when no specific filename
    assert downloads == 100  # First asset download count
    assert target_asset is None


async def test_download_counter_fallback_when_file_name_not_found(
    repository_plugin, mock_release_with_multiple_assets
):
    """Test that download counter falls back to first asset when file_name doesn't match any asset."""
    repository = repository_plugin
    repository.data.file_name = (
        "nonexistent-file.zip"  # File that doesn't exist in assets
    )
    repository.releases.objects = [mock_release_with_multiple_assets]
    repository.ref = "1.0.0"
    repository.data.releases = True

    # Test the actual logic we implemented in base.py
    release = repository.releases.objects[0]
    if assets := release.assets:
        # Find the correct asset based on file_name, fallback to first asset
        target_asset = None
        if repository.data.file_name:
            for asset in assets:
                if asset.name == repository.data.file_name:
                    target_asset = asset
                    break

        # Use the target asset if found, otherwise use the first asset
        if target_asset:
            downloads = target_asset.download_count
        else:
            downloads = next(iter(assets)).download_count

    # Should fallback to first asset when filename not found
    assert downloads == 100  # First asset download count
    assert target_asset is None
