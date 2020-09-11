"""Tests for repository extraction."""
from custom_components.hacs.helpers.functions.misc import extract_repository_from_url


def test_extract_repository_from_url():
    """Tests for repository extraction."""
    assert extract_repository_from_url("https://github.com/user/repo") == "user/repo"
    assert extract_repository_from_url("user/repo/") == "user/repo"
    assert extract_repository_from_url("user/repo") == "user/repo"
    assert extract_repository_from_url("USER/REPO") == "user/repo"
    assert extract_repository_from_url("user/repo.git") == "user/repo"
    assert extract_repository_from_url("user/repo.repo") == "user/repo.repo"
    assert extract_repository_from_url("git@github.com:user/repo.git") == "user/repo"
    assert not extract_repository_from_url("https://google.com/user/repo")
