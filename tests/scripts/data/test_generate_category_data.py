"""Test generate category data."""

import argparse
import asyncio
import base64
from contextlib import nullcontext as does_not_raise
from datetime import UTC, datetime, timedelta
import json
import logging
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiogithubapi import GitHubNotModifiedException
from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.exceptions import HacsException
from scripts.data.generate_category_data import (
    OUTPUT_DIR,
    AdjustedHacs,
    AdjustedHacsData,
    _parse_shard,
    _slice_by_shard,
    generate_category_data,
    get_default_repositories,
    get_removed_repositories,
    get_stored_data,
    shard_for,
    write_shard_output,
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
INTEGRATION_DIRECTORY_TREE_ITEM = AIOGitHubAPIRepositoryTreeContent(
    {"path": "custom_components/example", "type": "tree"}, "test/test", "main"
)
MANIFEST_TREE_ITEM = AIOGitHubAPIRepositoryTreeContent(
    {"path": "custom_components/example/manifest.json", "type": "blob"}, "test/test", "main"
)


def common_update_with_etag(repository, etag: str, updated: bool = True):
    """Return a common_update that stores etag, like the real one does before fetching the tree."""

    async def _common_update(**_):
        repository.data.etag_repository = etag
        return updated

    return _common_update


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
    if category_test_data["category"] == "integration":
        response_mocker.add(
            f"https://raw.githubusercontent.com/{category_test_data['repository']}/"
            f"{category_test_data['version_base']}/custom_components/example/manifest.json",
            MockedResponse(content=json.dumps({"domain": "example", "name": "Proxy manifest"})),
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
    response_mocker.add(
        f"https://raw.githubusercontent.com/{category_test_data['repository']}/"
        f"{category_test_data['version_base']}/custom_components/example/manifest.json",
        MockedResponse(content=json.dumps({"domain": "example", "name": "Proxy manifest"})),
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


async def test_get_stored_data_reads_from_stored_dir(tmp_path, monkeypatch):
    """When the snapshot dir is set, stored data is read from it, not fetched."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    payload = {"1": {"full_name": "octocat/Hello-World"}}
    (tmp_path / "integration.json").write_text(json.dumps(payload))

    hacs = _StubHacs()
    assert await get_stored_data(hacs, "integration") == payload
    assert hacs.data_client.calls == []


async def test_get_removed_repositories_reads_from_stored_dir(tmp_path, monkeypatch):
    """When the snapshot dir is set, the removed list is read from it, not fetched."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    removed = ["octocat/Hello-World", "hacs/integration"]
    (tmp_path / "removed.json").write_text(json.dumps(removed))

    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == removed
    assert hacs.data_client.calls == []


async def test_get_stored_data_falls_back_to_fetch(monkeypatch):
    """Without the snapshot dir, stored data is fetched from the data client."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", None)
    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_removed_repositories_falls_back_to_fetch(monkeypatch):
    """Without the snapshot dir, the removed list is fetched from the data client."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", None)
    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == _FETCHED_REMOVED
    assert hacs.data_client.calls == [("get_repositories", "removed")]


async def test_get_default_repositories_reads_from_stored_dir(tmp_path, monkeypatch):
    """When the snapshot dir is set, the hacs/default list is read from it, not fetched."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    default = ["octocat/Hello-World"]
    (tmp_path / "default-plugin.json").write_text(json.dumps(default))

    hacs = _StubHacs()
    hacs.async_github_get_hacs_default_file = AsyncMock()
    assert await get_default_repositories(hacs, "plugin") == default
    hacs.async_github_get_hacs_default_file.assert_not_awaited()


async def test_get_default_repositories_falls_back_to_fetch(monkeypatch):
    """Without the snapshot dir, the hacs/default list is fetched from GitHub."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", None)
    hacs = _StubHacs()
    hacs.async_github_get_hacs_default_file = AsyncMock(return_value=["octocat/Hello-World"])
    assert await get_default_repositories(hacs, "plugin") == ["octocat/Hello-World"]
    hacs.async_github_get_hacs_default_file.assert_awaited_once_with("plugin")


async def test_get_stored_data_falls_back_when_snapshot_missing(tmp_path, monkeypatch):
    """A missing snapshot file falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_stored_data_falls_back_when_snapshot_invalid(tmp_path, monkeypatch):
    """An invalid-JSON snapshot file falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    (tmp_path / "plugin.json").write_text("{ not valid json")

    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_stored_data_falls_back_when_snapshot_not_utf8(tmp_path, monkeypatch):
    """A snapshot file that is not valid UTF-8 falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    (tmp_path / "plugin.json").write_bytes(b"\xff\xfe")

    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_removed_repositories_falls_back_when_snapshot_missing(tmp_path, monkeypatch):
    """A missing removed snapshot falls back to fetching instead of raising."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == _FETCHED_REMOVED
    assert hacs.data_client.calls == [("get_repositories", "removed")]


async def test_get_stored_data_falls_back_on_wrong_shape(tmp_path, monkeypatch):
    """Valid JSON of the wrong type (list, not dict) falls back to fetching."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    (tmp_path / "plugin.json").write_text(json.dumps(["not", "a", "dict"]))

    hacs = _StubHacs()
    assert await get_stored_data(hacs, "plugin") == _FETCHED_STORED
    assert hacs.data_client.calls == [("get_data", "plugin")]


async def test_get_removed_repositories_falls_back_on_wrong_shape(tmp_path, monkeypatch):
    """Valid JSON of the wrong type (dict, not list) falls back to fetching."""
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(tmp_path))
    (tmp_path / "removed.json").write_text(json.dumps({"not": "a list"}))

    hacs = _StubHacs()
    assert await get_removed_repositories(hacs) == _FETCHED_REMOVED
    assert hacs.data_client.calls == [("get_repositories", "removed")]


@pytest.mark.parametrize(
    "category_test_data", category_test_data_parametrized(categories=["integration"])
)
async def test_generate_category_data_from_stored_snapshot(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
    tmp_path,
    monkeypatch,
):
    """Generating from the stored snapshot reproduces the fetch-path output.

    Feeds the same inputs the fetch path uses (empty category data + the removed
    fixture) through STORED_DATA_DIR, and asserts the generated data.json matches
    the fetch-path snapshot -- i.e. sourcing the baseline from disk is equivalent
    to fetching it.
    """
    category = category_test_data["category"]

    stored_dir = tmp_path / "stored"
    stored_dir.mkdir()
    (stored_dir / f"{category}.json").write_text("{}")
    with open(
        os.path.join(
            FIXTURES_PATH, "proxy", "data-v2.hacs.xyz", "removed", "repositories.json"
        ),
        encoding="utf-8",
    ) as file:
        (stored_dir / "removed.json").write_text(file.read())
    monkeypatch.setattr(f"{_MODULE}.STORED_DATA_DIR", str(stored_dir))

    await generate_category_data(category)

    with open(f"{OUTPUT_DIR}/{category}/data.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(
                json.loads(file.read()), ("last_fetched",))),
            f"scripts/data/generate_category_data/{category}//data.json",
        )


async def test_summarize_data_without_updated_data():
    """Test that summarizing empty updated data doesn't divide by zero."""
    rate_limit = MagicMock()
    # The summary is printed as JSON, so the rate limit values must be serializable.
    for resource in (rate_limit.data.resources.core, rate_limit.data.resources.graphql):
        resource.used, resource.limit, resource.reset = 0, 5000, 0
    hacs = MagicMock(async_github_api_method=AsyncMock(return_value=rate_limit))

    summary = await AdjustedHacs.summarize_data(hacs, {"1": {"full_name": "a/b"}}, {})

    assert summary["changed_pct"] == 0
    assert summary["new_count"] == 0
    assert summary["diff"] == 1


async def test_summarize_data_counts_refreshes():
    """Test that refreshes that would repeat on every run unless published are counted."""
    rate_limit = MagicMock()
    for resource in (rate_limit.data.resources.core, rate_limit.data.resources.graphql):
        resource.used, resource.limit, resource.reset = 0, 5000, 0
    hacs = MagicMock(async_github_api_method=AsyncMock(return_value=rate_limit))
    now = datetime.now(UTC).timestamp()
    fresh = now - timedelta(days=1).total_seconds()
    expired = now - timedelta(days=8).total_seconds()

    summary = await AdjustedHacs.summarize_data(
        hacs,
        {
            "fresh": {"full_name": "a/fresh", "last_fetched": fresh},
            "refreshed": {"full_name": "a/refreshed", "last_fetched": expired},
            "skipped": {"full_name": "a/skipped", "last_fetched": expired},
            "untimed": {"full_name": "a/untimed"},
            "recovered": {"full_name": "a/recovered", "etag_repository": "", "last_fetched": fresh},
            "failed": {"full_name": "a/failed", "etag_repository": "old", "last_fetched": fresh},
        },
        {
            "fresh": {"full_name": "a/fresh", "last_fetched": now},
            "refreshed": {"full_name": "a/refreshed", "last_fetched": now},
            "skipped": {"full_name": "a/skipped", "last_fetched": expired},
            "untimed": {"full_name": "a/untimed", "last_fetched": now},
            "recovered": {"full_name": "a/recovered", "etag_repository": "abc", "last_fetched": now},
            "failed": {"full_name": "a/failed", "etag_repository": "", "last_fetched": now},
            "new": {"full_name": "a/new", "last_fetched": now},
        },
    )

    assert summary["changed"] == 1
    assert summary["refreshed"] == 4


@pytest.mark.parametrize(
    ("full_name", "shards", "expected"),
    [
        ("hacs/integration", 3, 0),
        ("hacs-test-org/appdaemon-basic", 3, 1),
        ("hacs-test-org/theme-basic", 3, 2),
        ("hacs-test-org/plugin-basic", 2, 0),
        ("hacs-test-org/integration-basic-custom", 2, 1),
        ("anything", 1, 0),
        ("anything", 0, 0),
    ],
)
def test_shard_for(full_name: str, shards: int, expected: int):
    """Test that shard assignment is stable."""
    assert shard_for(full_name, shards) == expected


def test_shard_for_is_case_insensitive():
    """Test that repository casing doesn't change the shard."""
    assert shard_for("HACS/Integration", 3) == shard_for("hacs/integration", 3)


@pytest.mark.parametrize("shards", [2, 3])
def test_shard_for_uses_every_shard(shards: int):
    """Test that every shard gets repositories."""
    names = [f"user{i}/repo{i}" for i in range(500)]
    assert {shard_for(name, shards) for name in names} == set(range(shards))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1/3", (1, 3)), ("3/3", (3, 3)), ("1/1", (1, 1))],
)
def test_parse_shard(value: str, expected: tuple[int, int]):
    """Test parsing valid shard arguments."""
    assert _parse_shard(value) == expected


@pytest.mark.parametrize("value", ["0/3", "4/3", "3/0", "abc", "1/2/3", "1", "-1/3"])
def test_parse_shard_invalid(value: str):
    """Test that invalid shard arguments are rejected."""
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_shard(value)


def test_slice_by_shard():
    """Test that shard slices are disjoint and cover all entries."""
    data = {str(i): {"full_name": f"user{i}/repo{i}"} for i in range(200)}
    slices = [_slice_by_shard(data, index, 3) for index in range(3)]

    assert sum(len(entries) for entries in slices) == len(data)
    assert set().union(*slices) == set(data)
    for index, entries in enumerate(slices):
        assert all(shard_for(value["full_name"], 3) == index for value in entries.values())


def test_slice_by_shard_single_shard():
    """Test that a single shard keeps all entries."""
    data = {"1": {"full_name": "a/b"}}
    assert _slice_by_shard(data, 0, 1) is data


def test_write_shard_output(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Test that shard output is written for a later merge step."""
    monkeypatch.setattr("scripts.data.generate_category_data.SHARDS_DIR", str(tmp_path))
    updated = {"1": {"full_name": "a/b"}}

    write_shard_output("integration", 2, updated)

    shard_dir = tmp_path / "integration" / "2"
    assert json.loads((shard_dir / "data.json").read_text(encoding="utf-8")) == updated
    assert [path.name for path in shard_dir.iterdir()] == ["data.json"]


@pytest.mark.parametrize("shards", [2, 3])
async def test_get_category_repositories_filters_by_shard(shards: int):
    """Test that each shard queues only its part of the default repository list."""
    default = [
        "hacs-test-org/integration-basic",
        "hacs-test-org/integration-basic-custom",
        "octocat/Hello-World",
    ]
    queued = []
    for index in range(shards):
        hacs = MagicMock()
        hacs.async_github_get_hacs_default_file = AsyncMock(return_value=list(default))
        hacs.repositories.get_by_full_name.return_value = None

        await AdjustedHacs.get_category_repositories(hacs, "integration", None, [], index, shards)

        names = [
            call.kwargs["repository_full_name"]
            for call in hacs.concurrent_register_repository.call_args_list
        ]
        assert all(shard_for(name, shards) == index for name in names)
        queued += names

    assert sorted(queued) == sorted([*default, "hacs/integration"])


@pytest.mark.parametrize(("shard", "index"), [((1, 1), 0), ((2, 3), 1)])
async def test_generate_category_data_shard_skips_finalization(shard: tuple[int, int], index: int):
    """Test that a shard writes its partial data instead of finalizing."""
    updated = {"1": {"full_name": "a/b"}}
    with (
        patch(f"{_MODULE}.AdjustedHacs") as adjusted_hacs,
        patch(f"{_MODULE}.get_stored_data", AsyncMock(return_value={})),
        patch(f"{_MODULE}.finalize_category_output", AsyncMock()) as finalize,
        patch(f"{_MODULE}.write_shard_output") as write_shard,
    ):
        hacs = adjusted_hacs.return_value
        hacs.generate_data_for_category = AsyncMock(return_value=updated)

        await generate_category_data("integration", shard=shard)

    kwargs = hacs.generate_data_for_category.await_args.kwargs
    assert (kwargs["index"], kwargs["shards"]) == (index, shard[1])
    write_shard.assert_called_once_with("integration", shard[0], updated)
    finalize.assert_not_awaited()


async def test_generate_category_data_without_shard_finalizes():
    """Test that an unsharded run finalizes and writes no shard output."""
    updated = {"1": {"full_name": "a/b"}}
    stored = {"2": {"full_name": "c/d"}}
    with (
        patch(f"{_MODULE}.AdjustedHacs") as adjusted_hacs,
        patch(f"{_MODULE}.get_stored_data", AsyncMock(return_value=stored)),
        patch(f"{_MODULE}.finalize_category_output", AsyncMock()) as finalize,
        patch(f"{_MODULE}.write_shard_output") as write_shard,
    ):
        hacs = adjusted_hacs.return_value
        hacs.generate_data_for_category = AsyncMock(return_value=updated)

        await generate_category_data("integration")

    kwargs = hacs.generate_data_for_category.await_args.kwargs
    assert (kwargs["index"], kwargs["shards"]) == (0, 1)
    finalize.assert_awaited_once_with(hacs, "integration", stored, stored, updated)
    write_shard.assert_not_called()


@pytest.mark.parametrize(
    ("categories", "expected"),
    [
        (["energy", "unknown", "energy", "energy.ev_charging"], ["energy", "energy.ev_charging"]),
        (["unknown"], None),
        ([], None),
        (None, None),
    ],
)
async def test_store_repository_data_categories(
    repository_integration, categories: list[str] | None, expected: list[str] | None
):
    """Test that only valid categories are exported, and the key is left out otherwise."""
    repository_integration.integration_manifest = {"categories": categories}
    data = AdjustedHacsData(hacs=repository_integration.hacs)

    data.async_store_repository_data(repository_integration)

    assert data.content[str(repository_integration.data.id)].get("categories") == expected


async def test_register_base_data_restores_categories(hacs, repository_integration):
    """Test that stored categories survive a run where the manifest is not fetched."""
    hacs.repositories.register(repository_integration)
    data = AdjustedHacsData(hacs=hacs)

    await data.register_base_data(
        "integration",
        {
            str(repository_integration.data.id): {
                "categories": ["energy"],
                "full_name": repository_integration.data.full_name,
            }
        },
        [],
    )

    assert repository_integration.integration_manifest == {"categories": ["energy"]}


async def test_register_base_data_restores_categories_for_renamed_repository(
    hacs, repository_integration
):
    """Test that stored categories are restored when the repository was renamed."""
    hacs.repositories.register(repository_integration)
    data = AdjustedHacsData(hacs=hacs)

    await data.register_base_data(
        "integration",
        {
            str(repository_integration.data.id): {
                "categories": ["energy"],
                "full_name": "old/name",
            }
        },
        [],
    )

    assert repository_integration.integration_manifest == {"categories": ["energy"]}


@pytest.mark.parametrize(
    ("stored", "fetched", "updated", "expected"),
    [
        # Gaining categories
        ({}, {"categories": ["energy"]}, True, {"categories": ["energy"]}),
        # Changing categories
        ({"categories": ["energy"]}, {"categories": ["climate"]}, True, {"categories": ["climate"]}),
        # Removing categories
        ({"categories": ["energy"]}, {"domain": "test"}, True, {"domain": "test"}),
        # Not modified keeps the stored categories
        ({"categories": ["energy"]}, {"categories": ["climate"]}, False, {"categories": ["energy"]}),
    ],
)
async def test_update_repository_reloads_integration_manifest(
    repository_integration, stored: dict, fetched: dict, updated: bool, expected: dict
):
    """Test that a modified repository gets the manifest for the current ref."""
    repository_integration.tree = [INTEGRATION_DIRECTORY_TREE_ITEM, MANIFEST_TREE_ITEM]
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = "old"
    repository_integration.integration_manifest = stored
    repository_integration.common_update = common_update_with_etag(
        repository_integration, "new" if updated else "old", updated
    )
    repository_integration.get_integration_manifest = AsyncMock(return_value=fetched)

    await AdjustedHacs.concurrent_update_repository.__wrapped__(
        AdjustedHacs.__new__(AdjustedHacs), repository_integration
    )

    assert repository_integration.integration_manifest == expected
    if updated:
        repository_integration.get_integration_manifest.assert_awaited_once_with(
            version=repository_integration.ref
        )
    else:
        repository_integration.get_integration_manifest.assert_not_awaited()



async def test_update_repository_without_integration_manifest(repository_integration):
    """Test that stored categories are dropped when the repository has no manifest."""
    repository_integration.tree = [INTEGRATION_DIRECTORY_TREE_ITEM]
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = "old"
    repository_integration.integration_manifest = {"categories": ["energy"]}
    repository_integration.common_update = common_update_with_etag(repository_integration, "new")

    await AdjustedHacs.concurrent_update_repository.__wrapped__(
        AdjustedHacs.__new__(AdjustedHacs), repository_integration
    )

    assert repository_integration.integration_manifest == {}



async def test_update_repository_keeps_categories_when_tree_fetch_fails(repository_integration):
    """Test that a forced update without a tree keeps the categories and is retried."""
    repository_integration.tree = []
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = None
    repository_integration.integration_manifest = {"categories": ["energy"]}
    repository_integration.common_update = common_update_with_etag(repository_integration, "new")
    repository_integration.get_integration_manifest = AsyncMock()

    with pytest.raises(HacsException, match="Could not update the repository"):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(
            AdjustedHacs.__new__(AdjustedHacs), repository_integration
        )

    assert repository_integration.integration_manifest == {"categories": ["energy"]}
    assert repository_integration.data.etag_repository == ""
    repository_integration.get_integration_manifest.assert_not_awaited()


async def test_update_repository_unresolved_integration_path(repository_integration):
    """Test that an unknown layout, like after hacs.json failed to download, is retried."""
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent({"path": "manifest.json", "type": "blob"}, "test/test", "main")
    ]
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = "old"
    repository_integration.integration_manifest = {"categories": ["energy"]}
    repository_integration.common_update = common_update_with_etag(repository_integration, "new")
    repository_integration.get_integration_manifest = AsyncMock()

    with pytest.raises(HacsException, match="Could not find the integration directory"):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(
            AdjustedHacs.__new__(AdjustedHacs), repository_integration
        )

    assert repository_integration.integration_manifest == {"categories": ["energy"]}
    assert repository_integration.data.etag_repository == ""
    repository_integration.get_integration_manifest.assert_not_awaited()

async def test_update_repository_retries_failed_integration_manifest(repository_integration):
    """Test that a failed manifest fetch keeps the categories and is retried on the next run."""
    repository_integration.tree = [INTEGRATION_DIRECTORY_TREE_ITEM, MANIFEST_TREE_ITEM]
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = "old"
    repository_integration.integration_manifest = {"categories": ["energy"]}
    repository_integration.get_integration_manifest = AsyncMock(return_value=None)

    async def _common_update(**_):
        # GitHub reports a modified repository unless the stored ETag matches
        modified = repository_integration.data.etag_repository != "new"
        repository_integration.data.etag_repository = "new"
        return modified

    repository_integration.common_update = _common_update
    hacs = AdjustedHacs.__new__(AdjustedHacs)

    with pytest.raises(HacsException, match=r"Could not download manifest\.json"):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(hacs, repository_integration)

    assert repository_integration.integration_manifest == {"categories": ["energy"]}
    assert repository_integration.data.etag_repository == ""

    repository_integration.get_integration_manifest = AsyncMock(
        return_value={"categories": ["climate"]}
    )
    await AdjustedHacs.concurrent_update_repository.__wrapped__(hacs, repository_integration)

    assert repository_integration.integration_manifest == {"categories": ["climate"]}
    assert repository_integration.data.etag_repository == "new"


@pytest.mark.parametrize(
    ("new_etag", "expectation", "expected_etag"),
    [
        # The update failed after common_update stored the new ETag
        ("new", pytest.raises(HacsException, match="Could not update the repository"), ""),
        # Not modified
        ("old", does_not_raise(), "old"),
    ],
)
async def test_update_repository_not_updated_integration(
    repository_integration, new_etag: str, expectation, expected_etag: str
):
    """Test that a failed update is retried on the next run, and an unmodified one isn't."""
    repository_integration.tree = [INTEGRATION_DIRECTORY_TREE_ITEM, MANIFEST_TREE_ITEM]
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = "old"
    repository_integration.integration_manifest = {"categories": ["energy"]}
    repository_integration.get_integration_manifest = AsyncMock()

    async def _common_update(**_):
        repository_integration.data.etag_repository = new_etag
        return False

    repository_integration.common_update = _common_update

    with expectation:
        await AdjustedHacs.concurrent_update_repository.__wrapped__(
            AdjustedHacs.__new__(AdjustedHacs), repository_integration
        )

    assert repository_integration.data.etag_repository == expected_etag
    assert repository_integration.integration_manifest == {"categories": ["energy"]}
    repository_integration.get_integration_manifest.assert_not_awaited()


@pytest.mark.parametrize("manifest", [[], "manifest", False])
async def test_update_repository_invalid_integration_manifest(repository_integration, manifest):
    """Test that a manifest that isn't an object has no categories."""
    repository_integration.tree = [INTEGRATION_DIRECTORY_TREE_ITEM, MANIFEST_TREE_ITEM]
    repository_integration.data.last_version = None
    repository_integration.data.etag_repository = "old"
    repository_integration.integration_manifest = {"categories": ["energy"]}
    repository_integration.common_update = common_update_with_etag(repository_integration, "new")
    repository_integration.get_integration_manifest = AsyncMock(return_value=manifest)

    await AdjustedHacs.concurrent_update_repository.__wrapped__(
        AdjustedHacs.__new__(AdjustedHacs), repository_integration
    )

    assert repository_integration.integration_manifest == {}
    assert repository_integration.data.etag_repository == "new"


@pytest.mark.parametrize(
    ("side_effect", "expected_etag"),
    [
        (Exception("Update failed"), ""),
        (None, "etag"),
    ],
)
async def test_concurrent_update_repository_clears_etag_on_failure(
    repository_integration, side_effect: Exception | None, expected_etag: str
):
    """Test that a failed update is fetched again on the next run."""
    repository_integration.data.etag_repository = "etag"
    hacs = AdjustedHacs.__new__(AdjustedHacs)
    hacs.async_update_repository = AsyncMock(side_effect=side_effect)

    if side_effect is None:
        await AdjustedHacs.concurrent_update_repository.__wrapped__(hacs, repository_integration)
    else:
        with pytest.raises(Exception, match="Update failed"):
            await AdjustedHacs.concurrent_update_repository.__wrapped__(
                hacs, repository_integration
            )

    assert repository_integration.data.etag_repository == expected_etag
    hacs.async_update_repository.assert_awaited_once_with(repository_integration)


async def test_update_repository_without_etag(repository_plugin):
    """Test that an update that couldn't fetch the repository is retried on the next run."""
    repository_plugin.data.last_version = None
    repository_plugin.data.etag_repository = None
    repository_plugin.common_update = AsyncMock(return_value=True)

    with pytest.raises(HacsException, match="Could not update the repository"):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(
            AdjustedHacs.__new__(AdjustedHacs), repository_plugin
        )

    assert repository_plugin.data.etag_repository == ""


@pytest.mark.parametrize(
    ("last_version", "tag_name", "prerelease", "etag", "fetched_ago", "force"),
    [
        # The current release is the latest one
        ("1.0.0", "1.0.0", "1.1.0b0", "old", timedelta(days=1), None),
        # New release
        ("1.0.0", "2.0.0", "1.1.0b0", "old", timedelta(days=1), True),
        # New prerelease
        ("1.0.0", "1.0.0", "1.2.0b0", "old", timedelta(days=1), True),
        # The stored data is too old
        ("1.0.0", "1.0.0", "1.1.0b0", "old", timedelta(days=8), True),
        # Never fetched
        ("1.0.0", "1.0.0", "1.1.0b0", "old", None, False),
        # The last update failed
        ("1.0.0", "1.0.0", "1.1.0b0", "", timedelta(days=1), False),
        # No stable release to compare with
        (None, "1.0.0", "1.1.0b0", "old", timedelta(days=1), False),
        # Removed prerelease
        ("1.0.0", "1.0.0", None, "old", timedelta(days=1), True),
    ],
)
async def test_update_repository_gated_on_release(
    repository_plugin,
    caplog: pytest.LogCaptureFixture,
    last_version: str | None,
    tag_name: str,
    prerelease: str | None,
    etag: str,
    fetched_ago: timedelta | None,
    force: bool | None,
):
    """Test that a repository with an unchanged release is only updated when its data needs it."""
    repository_plugin.data.releases = True
    repository_plugin.data.last_commit = "abc1234"
    repository_plugin.data.last_version = last_version
    repository_plugin.data.prerelease = "1.1.0b0"
    repository_plugin.tree = [MANIFEST_TREE_ITEM]
    repository_plugin.data.etag_repository = etag
    repository_plugin.data.last_fetched = (
        datetime.now(UTC) - fetched_ago if fetched_ago is not None else None
    )
    repository_plugin.common_update = AsyncMock(
        side_effect=common_update_with_etag(repository_plugin, "new")
    )
    hacs = AdjustedHacs.__new__(AdjustedHacs)
    hacs.githubapi = MagicMock(
        generic=AsyncMock(
            return_value=MagicMock(
                data=[
                    *(
                        [{"tag_name": prerelease, "draft": False, "prerelease": True}]
                        if prerelease
                        else []
                    ),
                    {"tag_name": tag_name, "draft": False, "prerelease": False},
                ],
                etag="releases",
            )
        )
    )

    with caplog.at_level(logging.INFO):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(hacs, repository_plugin)

    if force is None:
        repository_plugin.common_update.assert_not_awaited()
    else:
        assert repository_plugin.common_update.await_args.kwargs["force"] is force
    assert (
        "Current release 1.0.0 is the latest one, next refresh in 06:00:00:00" in caplog.text
    ) is (force is None)


async def test_update_repository_without_tree_is_retried(repository_plugin):
    """Test that a forced update that couldn't fetch the tree is retried on the next run."""
    repository_plugin.data.releases = True
    repository_plugin.data.last_version = "1.0.0"
    repository_plugin.data.etag_repository = "old"
    repository_plugin.data.last_fetched = datetime.now(UTC) - timedelta(days=8)
    repository_plugin.tree = []
    repository_plugin.common_update = common_update_with_etag(repository_plugin, "new")
    hacs = AdjustedHacs.__new__(AdjustedHacs)
    hacs.githubapi = MagicMock(
        generic=AsyncMock(
            return_value=MagicMock(
                data=[{"tag_name": "1.0.0", "draft": False, "prerelease": False}],
                etag="releases",
            )
        )
    )

    with pytest.raises(HacsException, match="Could not update the repository"):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(hacs, repository_plugin)

    assert repository_plugin.data.etag_repository == ""


async def test_update_repository_skipped_when_releases_not_modified(
    repository_plugin, caplog: pytest.LogCaptureFixture
):
    """Test that a repository is skipped when GitHub reports its releases as not modified."""
    repository_plugin.data.last_version = "1.0.0"
    repository_plugin.data.etag_repository = "old"
    repository_plugin.data.last_fetched = datetime.now(UTC) - timedelta(days=1)
    repository_plugin.common_update = AsyncMock()
    hacs = AdjustedHacs.__new__(AdjustedHacs)
    hacs.githubapi = MagicMock(generic=AsyncMock(side_effect=GitHubNotModifiedException("")))

    with caplog.at_level(logging.INFO):
        await AdjustedHacs.concurrent_update_repository.__wrapped__(hacs, repository_plugin)

    repository_plugin.common_update.assert_not_awaited()
    assert "Current release 1.0.0 is the latest one, next refresh in 06:00:00:00" in caplog.text


async def test_generate_category_data_exports_categories(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
):
    """Test that only valid categories from the manifest are exported."""
    manifest = {
        "domain": "example",
        "name": "Example",
        "categories": ["energy", "unknown", "energy", "energy.ev_charging"],
    }
    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/data.json",
        MockedResponse(content={}),
    )
    response_mocker.add(
        "https://api.github.com/repos/hacs-test-org/integration-basic/contents/custom_components/example/manifest.json",
        MockedResponse(
            content={"content": base64.b64encode(json.dumps(manifest).encode()).decode()},
            headers=BASE_HEADERS,
        ),
    )

    await generate_category_data("integration", "hacs-test-org/integration-basic")

    with open(f"{OUTPUT_DIR}/integration/data.json", encoding="utf-8") as file:
        data = json.loads(file.read())

    assert [entry.get("categories") for entry in data.values()] == [
        ["energy", "energy.ev_charging"]
    ]


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized(categories=["integration"]))
@pytest.mark.parametrize(
    ("manifest_categories", "expected"),
    [
        # Changing categories
        (["climate", "unknown", "energy.ev_charging"], ["climate", "energy.ev_charging"]),
        # Removing categories
        (None, None),
    ],
)
async def test_generate_category_data_exports_categories_for_updated_repository(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    category_test_data: CategoryTestData,
    manifest_categories: list[str] | None,
    expected: list[str] | None,
):
    """Test that a modified repository exports the categories of its current manifest."""
    manifest = {"domain": "example", "name": "Example"}
    if manifest_categories is not None:
        manifest["categories"] = manifest_categories
    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/data.json",
        MockedResponse(
            content={
                category_test_data["id"]: {
                    "categories": ["energy"],
                    "description": "This your first repo!",
                    "domain": "example",
                    "etag_repository": "old",
                    "full_name": category_test_data["repository"],
                    "last_updated": "2011-01-26T19:06:43Z",
                    "last_version": category_test_data["version_base"],
                    "manifest": {"name": "Proxy manifest"},
                    "manifest_name": "Proxy manifest",
                }
            }
        ),
    )
    response_mocker.add(
        f"https://raw.githubusercontent.com/{category_test_data['repository']}/"
        f"{category_test_data['version_base']}/custom_components/example/manifest.json",
        MockedResponse(content=json.dumps(manifest)),
    )

    await generate_category_data("integration", category_test_data["repository"])

    with open(f"{OUTPUT_DIR}/integration/data.json", encoding="utf-8") as file:
        data = json.loads(file.read())

    assert data[category_test_data["id"]].get("categories") == expected

