"""Test generate category data."""

import asyncio
import json
import logging
import os
from typing import Any

from homeassistant.core import HomeAssistant
import pytest

from scripts.data.generate_category_data import (
    OUTPUT_DIR,
    generate_category_data,
    get_removed_repositories,
    get_stored_data,
)

from tests.common import (
    FIXTURES_PATH,
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    category_test_data_parametrized,
    recursive_remove_key,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture

BASE_HEADERS = {"Content-Type": "application/json"}
RATE_LIMIT_HEADER = {
    **BASE_HEADERS,
    "X-RateLimit-Limit": "9999",
    "X-RateLimit-Remaining": "9999",
    "X-RateLimit-Reset": "9999",
}


def get_generated_category_data(category: str) -> dict[str, Any]:
    """Get the generated data."""
    compare = {}

    with open(f"{OUTPUT_DIR}/{category}/data.json", encoding="utf-8") as file:
        compare["data"] = recursive_remove_key(
            json.loads(file.read()), ("last_fetched",))

    with open(f"{OUTPUT_DIR}/{category}/repositories.json", encoding="utf-8") as file:
        compare["repositories"] = recursive_remove_key(
            json.loads(file.read()), ())

    with open(f"{OUTPUT_DIR}/summary.json", encoding="utf-8") as file:
        compare["summary"] = recursive_remove_key(json.loads(file.read()), ())

    return compare


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_generate_category_data_single_repository(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
):
    """Test behaviour if single repository."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(content={}),
    )
    await generate_category_data(category_test_data["category"], category_test_data["repository"])

    with open(f"{OUTPUT_DIR}/{category_test_data['category']}/data.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(
                json.loads(file.read()), ("last_fetched",))),
            f"scripts/data/generate_category_data/single/{category_test_data['category']}/{
                category_test_data['repository']}/data.json",
        )

    with open(
        f"{OUTPUT_DIR}/{category_test_data['category']}/repositories.json",
        encoding="utf-8",
    ) as file:
        snapshots.assert_match(
            safe_json_dumps(json.loads(file.read())),
            f"scripts/data/generate_category_data/single/{category_test_data['category']}/{
                category_test_data['repository']}/repositories.json",
        )

    with open(
        f"{OUTPUT_DIR}/summary.json",
        encoding="utf-8",
    ) as file:
        snapshots.assert_match(
            safe_json_dumps(json.loads(file.read())),
            f"scripts/data/generate_category_data/single/{category_test_data['category']}/{
                category_test_data['repository']}/summary.json",
        )


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_generate_category_data(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
):
    """Test behaviour if single repository."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(content={}),
    )
    await generate_category_data(category_test_data["category"])

    with open(f"{OUTPUT_DIR}/{category_test_data['category']}/data.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(
                json.loads(file.read()), ("last_fetched",))),
            f"scripts/data/generate_category_data/{
                category_test_data['category']}//data.json",
        )

    with open(
        f"{OUTPUT_DIR}/{category_test_data['category']}/repositories.json",
        encoding="utf-8",
    ) as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(json.loads(file.read()), ())),
            f"scripts/data/generate_category_data/{
                category_test_data['category']}/repositories.json",
        )

    with open(
        f"{OUTPUT_DIR}/summary.json",
        encoding="utf-8",
    ) as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(json.loads(file.read()), ())),
            f"scripts/data/generate_category_data/{
                category_test_data['category']}/summary.json",
        )


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_generate_category_data_with_prior_content(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
):
    """Test behaviour with prior content."""
    category_data = {
        "integration": {
            "domain": "example",
            "manifest": {"name": "Proxy manifest"},
            "manifest_name": "Proxy manifest",
        }
    }
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(
            content={
                category_test_data["id"]: {
                    "description": "This your first repo!",
                    "downloads": 0,
                    "etag_repository": "321",
                    "full_name": category_test_data["repository"],
                    "last_updated": "2011-01-26T19:06:43Z",
                    "last_version": category_test_data["version_base"],
                    "prerelease": "0.0.0",
                    "stargazers_count": 0,
                    "topics": ["api", "atom", "electron", "octocat"],
                    **category_data.get(category_test_data["category"], {}),
                }
            }
        ),
    )

    await generate_category_data(category_test_data["category"])

    snapshots.assert_match(
        safe_json_dumps(get_generated_category_data(
            category_test_data["category"])),
        f"scripts/data/test_generate_category_data_with_prior_content/{
            category_test_data['category']}.json",
    )


@pytest.mark.parametrize(
    "category_test_data", category_test_data_parametrized(
        categories=["integration"])
)
@pytest.mark.parametrize("error", (asyncio.CancelledError, asyncio.TimeoutError, Exception("base")))
async def test_generate_category_data_errors_release(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
    error: Exception,
    request: pytest.FixtureRequest,
):
    """Test behaviour if single repository."""
    response_mocker.add(
        f"https://api.github.com/repos/{
            category_test_data['repository']}/releases",
        MockedResponse(exception=error),
    )
    await generate_category_data(category_test_data["category"])

    snapshots.assert_match(
        safe_json_dumps(get_generated_category_data(
            category_test_data["category"])),
        f"scripts/data/test_generate_category_data_errors_release/{
            category_test_data['category']}/{request.node.callspec.id.split("-")[0]}.json",
    )


@pytest.mark.parametrize(
    "category_test_data", category_test_data_parametrized(
        categories=["integration"])
)
@pytest.mark.parametrize("status", (304, 404))
async def test_generate_category_data_error_status_release(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
    status: int,
):
    """Test behaviour with error status and existing content."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(
            content={
                category_test_data["id"]: {
                    "description": "This your first repo!",
                    "downloads": 0,
                    "etag_repository": "321",
                    "full_name": category_test_data["repository"],
                    "last_updated": "2011-01-26T19:06:43Z",
                    "last_version": category_test_data["version_base"],
                    "stargazers_count": 0,
                    "topics": ["api", "atom", "electron", "octocat"],
                    "domain": "example",
                    "manifest": {"name": "Proxy manifest"},
                    "manifest_name": "Proxy manifest",
                }
            }
        ),
    )

    response_mocker.add(
        f"https://api.github.com/repos/{
            category_test_data['repository']}/releases",
        MockedResponse(status=status, content=[]),
    )
    await generate_category_data(category_test_data["category"])

    snapshots.assert_match(
        safe_json_dumps(get_generated_category_data(
            category_test_data["category"])),
        f"scripts/data/test_generate_category_data_error_status_release/{
            category_test_data['category']}/{status}.json",
    )


@pytest.mark.parametrize(
    "category_test_data", category_test_data_parametrized(
        categories=["integration"])
)
async def test_generate_category_data_with_30plus_prereleases(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
):
    """Test behaviour with prior content."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(
            content={
                category_test_data["id"]: {
                    "description": "This your first repo!",
                    "downloads": 0,
                    "etag_repository": "321",
                    "full_name": category_test_data["repository"],
                    "last_updated": "2011-01-26T19:06:43Z",
                    "last_version": category_test_data["version_base"],
                    "stargazers_count": 0,
                    "topics": ["api", "atom", "electron", "octocat"],
                    "domain": "example",
                    "manifest": {"name": "Proxy manifest"},
                    "manifest_name": "Proxy manifest",
                }
            }
        ),
    )

    with open(
        os.path.join(
            FIXTURES_PATH,
            "proxy/api.github.com/repos/hacs-test-org/integration-basic/releases.json",
        )
    ) as file:
        release_fixture = json.loads(file.read())[0]

    response_mocker.add(
        f"https://api.github.com/repos/{
            category_test_data['repository']}/releases",
        MockedResponse(content=[release_fixture for _ in range(30)]),
    )

    await generate_category_data(category_test_data["category"])

    snapshots.assert_match(
        safe_json_dumps(get_generated_category_data(
            category_test_data["category"])),
        f"scripts/data/test_generate_category_data_with_30plus_prereleases/{
            category_test_data['category']}.json",
    )


# Shapes mirror the real data client: get_data -> {repo-id: {...}}, removed -> [full_name].
_FETCHED_STORED = {"1296269": {"full_name": "octocat/Hello-World", "category": "plugin"}}
_FETCHED_REMOVED = ["octocat/removed-repo"]


class _StubDataClient:
    """Minimal data client recording that a fetch happened."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def get_data(self, section: str, *, validate: bool) -> dict[str, dict[str, Any]]:
        self.calls.append(("get_data", section))
        return _FETCHED_STORED

    async def get_repositories(self, section: str) -> list[str]:
        self.calls.append(("get_repositories", section))
        return _FETCHED_REMOVED


class _StubHacs:
    """Minimal HACS stand-in exposing only a data client and a logger."""

    def __init__(self) -> None:
        self.data_client = _StubDataClient()
        self.log = logging.getLogger("test.generate_category_data")


_MODULE = "scripts.data.generate_category_data"


async def test_get_stored_data_reads_from_existing_dir(tmp_path, monkeypatch):
    """When the snapshot dir is set, stored data is read from it, not fetched."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", str(tmp_path))
    payload = {"1": {"full_name": "octocat/Hello-World"}}
    (tmp_path / "integration.json").write_text(json.dumps(payload))

    hacs = _StubHacs()
    assert await get_stored_data(hacs, "integration") == payload
    assert hacs.data_client.calls == []


async def test_get_removed_repositories_reads_from_existing_dir(tmp_path, monkeypatch):
    """When the snapshot dir is set, the removed list is read from it, not fetched."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", str(tmp_path))
    removed = ["octocat/Hello-World", "hacs/integration"]
    (tmp_path / "removed.json").write_text(json.dumps(removed))

    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == removed
    assert hacs.data_client.calls == []


async def test_get_stored_data_falls_back_to_fetch(monkeypatch):
    """Without the snapshot dir, stored data is fetched from the data client."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", None)
    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_removed_repositories_falls_back_to_fetch(monkeypatch):
    """Without the snapshot dir, the removed list is fetched from the data client."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", None)
    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == _FETCHED_REMOVED
    assert hacs.data_client.calls == [("get_repositories", "removed")]


async def test_get_stored_data_falls_back_when_snapshot_missing(tmp_path, monkeypatch):
    """A missing snapshot file falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", str(tmp_path))
    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_stored_data_falls_back_when_snapshot_invalid(tmp_path, monkeypatch):
    """An invalid-JSON snapshot file falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", str(tmp_path))
    (tmp_path / "plugin.json").write_text("{ not valid json")

    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_removed_repositories_falls_back_when_snapshot_missing(tmp_path, monkeypatch):
    """A missing removed snapshot falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.EXISTING_DATA_DIR", str(tmp_path))
    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == _FETCHED_REMOVED
    assert hacs.data_client.calls == [("get_repositories", "removed")]
