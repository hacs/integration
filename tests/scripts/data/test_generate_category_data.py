"""Test generate category data."""
from unittest.mock import ANY
import json
from base64 import b64encode

import pytest

from aresponses import ResponsesMockServer

from scripts.data.generate_category_data import generate_category_data, OUTPUT_DIR

from tests.sample_data import repository_data, tree_files_base, integration_manifest

BASE_HEADERS = {"Content-Type": "application/json"}
RATE_LIMIT_HEADER = {
    **BASE_HEADERS,
    "X-RateLimit-Limit": "9999",
    "X-RateLimit-Remaining": "9999",
    "X-RateLimit-Reset": "9999",
}


@pytest.mark.asyncio
async def test_generate_category_data_single_repository(
    aresponses: ResponsesMockServer,
):
    """Test behaviour if single repository."""
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(
            body=json.dumps({"resources": {"core": {"remaining": 9999}}}), headers=BASE_HEADERS
        ),
    )
    aresponses.add(
        "data-v2.hacs.xyz",
        "/integration/data.json",
        "get",
        aresponses.Response(
            body=json.dumps(
                {
                    "999999999": {
                        "manifest": {"name": "test"},
                        "description": "Sample description for repository.",
                        "domain": "test",
                        "full_name": "test/test",
                        "last_commit": "1234567",
                        "manifest_name": "Test",
                        "stargazers_count": 991,
                        "topics": [],
                    }
                }
            ),
            headers=BASE_HEADERS,
        ),
    )

    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(
            body=json.dumps(repository_data),
            headers=BASE_HEADERS,
        ),
    )

    aresponses.add(
        "api.github.com",
        "/repos/test/test/branches/main",
        "get",
        aresponses.Response(
            body=json.dumps({"commit": {"sha": "1234567890123456789012345678901234567890"}}),
            headers=BASE_HEADERS,
        ),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/main",
        "get",
        aresponses.Response(
            body=json.dumps(
                {
                    "tree": [
                        *tree_files_base["tree"],
                        {"path": "custom_components", "type": "tree"},
                        {"path": "custom_components/test", "type": "tree"},
                        {"path": "custom_components/test/manifest.json", "type": "blob"},
                        {"path": "custom_components/test/__init__.py", "type": "blob"},
                    ]
                }
            ),
            headers=BASE_HEADERS,
        ),
    )

    aresponses.add(
        "api.github.com",
        "/repos/test/test/releases",
        "get",
        aresponses.Response(
            body=json.dumps([]),
            headers=BASE_HEADERS,
        ),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/hacs.json",
        "get",
        aresponses.Response(
            body=json.dumps(
                {
                    "content": b64encode(
                        json.dumps(
                            {"name": "test", "hide_default_branch": True, "render_readme": True}
                        ).encode("utf-8")
                    ).decode("utf-8")
                }
            ),
            headers=BASE_HEADERS,
        ),
    )

    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/custom_components/test/manifest.json",
        "get",
        aresponses.Response(
            body=json.dumps(
                {
                    "content": b64encode(json.dumps(integration_manifest).encode("utf-8")).decode(
                        "utf-8"
                    )
                }
            ),
            headers=BASE_HEADERS,
        ),
    )

    await generate_category_data("integration", "test/test")

    with open(f"{OUTPUT_DIR}/integration/data.json", "r", encoding="utf-8") as file:
        data = json.loads(file.read())
        assert data == {
            "999999999": {
                "manifest": {"name": "test"},
                "description": "Sample description for repository.",
                "domain": "test",
                "full_name": "test/test",
                "last_commit": "1234567",
                "manifest_name": "Test",
                "stargazers_count": 999,
                "topics": ["topic1", "topic2"],
                "last_fetched": ANY,
            }
        }

    with open(f"{OUTPUT_DIR}/integration/repositories.json", "r", encoding="utf-8") as file:
        data = json.loads(file.read())
        assert data == ["test/test"]


@pytest.mark.asyncio
async def test_generate_category_data(
    aresponses: ResponsesMockServer,
):
    """Test behaviour."""
    repositories = ["test/first", "test/second"]
    current_data = {
        "999999999": {
            "manifest": {"name": "test"},
            "description": "Old contents",
            "full_name": "test/first",
            "last_commit": "123",
            "etag_repository": "231",
            "stargazers_count": 992,
            "topics": [],
        }
    }
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(
            body=json.dumps({"resources": {"core": {"remaining": 9999}}}), headers=BASE_HEADERS
        ),
    )
    aresponses.add(
        "data-v2.hacs.xyz",
        "/removed/repositories.json",
        "get",
        aresponses.Response(
            body=json.dumps([]),
            headers=BASE_HEADERS,
        ),
    )

    aresponses.add(
        "data-v2.hacs.xyz",
        "/template/data.json",
        "get",
        aresponses.Response(
            body=json.dumps(current_data),
            headers=BASE_HEADERS,
        ),
    )

    aresponses.add(
        "api.github.com",
        "/repos/hacs/default/contents/template",
        "get",
        aresponses.Response(
            body=json.dumps(
                {"content": b64encode(json.dumps(repositories).encode("utf-8")).decode("utf-8")}
            ),
            headers=BASE_HEADERS,
        ),
    )

    for repo in repositories:
        aresponses.add(
            "api.github.com",
            f"/repos/{repo}",
            "get",
            aresponses.Response(
                body=json.dumps(
                    {
                        **repository_data,
                        "id": 999999999 if repo == "test/first" else 999999998,
                        "full_name": repo,
                    }
                ),
                headers=BASE_HEADERS,
            ),
        )

        aresponses.add(
            "api.github.com",
            f"/repos/{repo}/branches/main",
            "get",
            aresponses.Response(
                body=json.dumps({"commit": {"sha": "1234567890123456789012345678901234567890"}}),
                headers=BASE_HEADERS,
            ),
        )
        aresponses.add(
            "api.github.com",
            f"/repos/{repo}/git/trees/main",
            "get",
            aresponses.Response(
                body=json.dumps(
                    {
                        "tree": [
                            *tree_files_base["tree"],
                            {"path": "test.jinja", "type": "blob"},
                        ]
                    }
                ),
                headers=BASE_HEADERS,
            ),
        )

        aresponses.add(
            "api.github.com",
            f"/repos/{repo}/branches/main",
            "get",
            aresponses.Response(
                body=json.dumps({"commit": {"sha": "1234567890123456789012345678901234567890"}}),
                headers=BASE_HEADERS,
            ),
        )
        aresponses.add(
            "api.github.com",
            f"/repos/{repo}/releases",
            "get",
            aresponses.Response(
                body=json.dumps([]),
                headers=BASE_HEADERS,
            ),
        )
        aresponses.add(
            "api.github.com",
            f"/repos/{repo}/contents/hacs.json",
            "get",
            aresponses.Response(
                body=json.dumps(
                    {
                        "content": b64encode(
                            json.dumps({"name": "test", "filename": "test.jinja"}).encode("utf-8")
                        ).decode("utf-8")
                    }
                ),
                headers=BASE_HEADERS,
            ),
        )

        aresponses.add(
            "api.github.com",
            f"/repos/{repo}/contents/readme.md",
            "get",
            aresponses.Response(
                body=json.dumps({"content": b64encode("".encode("utf-8")).decode("utf-8")}),
                headers=BASE_HEADERS,
            ),
        )
        aresponses.add(
            "api.github.com",
            "/rate_limit",
            "get",
            aresponses.Response(
                body=json.dumps({"resources": {"core": {"remaining": 9999}}}), headers=BASE_HEADERS
            ),
        )

    await generate_category_data("template")

    with open(f"{OUTPUT_DIR}/template/data.json", "r", encoding="utf-8") as file:
        data = json.loads(file.read())
        assert data == {
            "999999998": {
                "manifest": {"name": "test"},
                "description": "Sample description for repository.",
                "full_name": "test/second",
                "last_commit": "1234567",
                "stargazers_count": 999,
                "topics": ["topic1", "topic2"],
                "last_fetched": ANY,
            },
            "999999999": {
                "manifest": {"name": "test"},
                "description": "Sample description for repository.",
                "full_name": "test/first",
                "last_commit": "1234567",
                "stargazers_count": 999,
                "topics": ["topic1", "topic2"],
                "last_fetched": ANY,
            },
        }

    with open(f"{OUTPUT_DIR}/template/repositories.json", "r", encoding="utf-8") as file:
        data = json.loads(file.read())
        assert "test/first" in data
        assert "test/second" in data
        assert len(data) == 2
