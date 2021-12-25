"""Tests for repository extraction."""
from custom_components.hacs.utils import regex


def test_extract_repository_from_url():
    """Tests for repository extraction."""
    assert regex.extract_repository_from_url("https://github.com/user/repo") == "user/repo"
    assert regex.extract_repository_from_url("user/repo/") == "user/repo"
    assert regex.extract_repository_from_url("user/repo") == "user/repo"
    assert regex.extract_repository_from_url("USER/REPO") == "user/repo"
    assert regex.extract_repository_from_url("user/repo.git") == "user/repo"
    assert regex.extract_repository_from_url("user/repo.repo") == "user/repo.repo"
    assert regex.extract_repository_from_url("git@github.com:user/repo.git") == "user/repo"
    assert not regex.extract_repository_from_url("https://google.com/user/repo")
