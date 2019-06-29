"""Test data for AIOGitHub."""
# pylint: disable=invalid-name
import pytest


@pytest.fixture()
def response_get_repo_awesome():
    return {
        "id": 99999999,
        "full_name": "awesome-dev/awesome-repo",
        "pushed_at": "1970-01-01T00:00:00Z",
        "archived": False,
        "description": "Awesome!",
        "topics": ["awesome"],
        "default_branch": "master",
    }
