"""Tests for the utils.url module."""
import pytest

from custom_components.hacs.utils.url import github_archive, github_release_asset


@pytest.mark.parametrize(
    "arguments,url",
    (
        (
            {"repository": "owner/repo", "version": "1.0.0", "filename": "example.zip"},
            "https://github.com/owner/repo/releases/download/1.0.0/example.zip",
        ),
    ),
)
def test_github_release_asset(arguments: dict[str, str], url: str) -> None:
    """Test github_release_asset."""
    assert github_release_asset(**arguments) == url


@pytest.mark.parametrize(
    "arguments,url",
    (
        (
            {"repository": "owner/repo", "version": "1.0.0", "variant": "heads"},
            "https://github.com/owner/repo/archive/refs/heads/1.0.0.zip",
        ),
        (
            {"repository": "owner/repo", "version": "1.0.0", "variant": "tags"},
            "https://github.com/owner/repo/archive/refs/tags/1.0.0.zip",
        ),
        (
            {
                "repository": "owner/repo",
                "version": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
                "variant": "heads",
            },
            "https://github.com/owner/repo/archive/1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b.zip",
        ),
        (
            {
                "repository": "owner/repo",
                "version": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
                "variant": "tags",
            },
            "https://github.com/owner/repo/archive/1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b.zip",
        ),
    ),
)
def test_github_archive(arguments: dict[str, str], url: str) -> None:
    """Test github_archive."""
    assert github_archive(**arguments) == url
