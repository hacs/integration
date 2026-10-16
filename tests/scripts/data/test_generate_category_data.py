"""Test generate category data."""

import argparse
import asyncio
import json
import os
from typing import Any

from homeassistant.core import HomeAssistant
import pytest

from scripts.data.generate_category_data import (
    OUTPUT_DIR,
    _parse_shard,
    _slice_by_shard,
    generate_category_data,
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
    stored = {"2": {"full_name": "c/d"}}

    write_shard_output("integration", 2, updated, stored)

    shard_dir = tmp_path / "integration" / "2"
    assert json.loads((shard_dir / "data.json").read_text(encoding="utf-8")) == updated
    assert json.loads((shard_dir / "stored.json").read_text(encoding="utf-8")) == stored
