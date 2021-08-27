"""Sample datasets for testing."""
# pylint: disable=invalid-name,missing-docstring

repository_data = {
    "id": 999999999,
    "full_name": "test/test",
    "fork": False,
    "description": "Sample description for repository.",
    "pushed_at": "1970-01-01T00:00:00Z",
    "stargazers_count": 999,
    "archived": False,
    "topics": ["topic1", "topic2"],
    "default_branch": "main",
    "last_commit": "12345678",
}

response_rate_limit_header = {
    "X-RateLimit-Limit": "999",
    "X-RateLimit-Remaining": "999",
    "X-RateLimit-Reset": "999",
    "Content-Type": "application/json",
}

response_rate_limit_header_with_limit = {
    "X-RateLimit-Limit": "",
    "X-RateLimit-Remaining": "0",
    "X-RateLimit-Reset": "999",
    "Content-Type": "application/json",
}

tree_files_base = {
    "tree": [
        {"path": "info.md", "type": "blob"},
        {"path": "readme.md", "type": "blob"},
        {"path": "hacs.json", "type": "blob"},
    ]
}

integration_manifest = {
    "domain": "test",
    "name": "Test",
    "documentation": "https://test.docs",
    "dependencies": [],
    "codeowners": ["developer"],
    "requirements": [],
}

release_data = [
    {
        "tag_name": "3",
        "target_commitish": "main",
        "name": "3",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "test.file",
                "download_count": 8031,
                "browser_download_url": "https://github.com/test/test/releases/download/3/test.file",
            }
        ],
    }
]


def repository_data_archived():
    data = {}
    for key in repository_data:
        data[key] = repository_data[key]
    data["archived"] = True
    return data


def tree_files_base_integration():
    integrationtree = tree_files_base
    integrationtree["tree"].append({"path": "custom_components/test/manifest.json", "type": "blob"})
    integrationtree["tree"].append({"path": "custom_components/test/__init__.py", "type": "blob"})
    integrationtree["tree"].append({"path": "custom_components/test/sensor.py", "type": "blob"})
    integrationtree["tree"].append(
        {"path": "custom_components/test/translations/en.json", "type": "blob"}
    )
    return integrationtree
