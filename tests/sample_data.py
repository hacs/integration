"""Sample datasets for testing."""
# pylint: disable=invalid-name

repository_data = {
    "id": 999999999,
    "full_name": "test/test",
    "fork": False,
    "description": "Sample description for repository.",
    "pushed_at": "1970-01-01T00:00:00Z",
    "stargazers_count": 999,
    "archived": False,
    "topics": ["topic1", "topic2"],
    "default_branch": "master",
    "last_commit": "12345678",
}

response_rate_limit_header = {
    "X-RateLimit-Limit": "999",
    "X-RateLimit-Remaining": "999",
    "X-RateLimit-Reset": "999",
    "Content-Type": "application/json",
}
