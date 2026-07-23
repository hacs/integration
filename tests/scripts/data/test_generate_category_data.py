"""Test generate category data."""

import argparse
import asyncio
import json
import os
import shutil
from typing import Any

from homeassistant.core import HomeAssistant
import pytest

from scripts.data.generate_category_data import (
    OUTPUT_DIR,
    SHARDS_DIR,
    _parse_shard,
    _slice_by_shard,
    generate_category_data,
    shard_for,
    write_shard_output,
)
from scripts.data.merge_category_data import _load_shard_files

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
        ("hacs/integration", 3, 2),
        ("hacs/integration", 2, 1),
        ("hacs-test-org/integration-basic", 3, 1),
        ("octocat/Hello-World", 3, 1),
        ("octocat/Hello-World", 2, 0),
        ("anything", 1, 0),
        ("anything", 0, 0),
    ],
)
def test_shard_for(full_name: str, shards: int, expected: int):
    """Shard assignment is stable and matches precomputed values."""
    assert shard_for(full_name, shards) == expected


def test_shard_for_is_case_insensitive():
    """Repository casing must not change the shard assignment."""
    assert shard_for("HACS/Integration", 3) == shard_for("hacs/integration", 3)


def test_shard_for_partitions_all_buckets():
    """Every shard is used and assignments stay within range."""
    names = [f"user{i}/repo{i}" for i in range(500)]
    for shards in (2, 3):
        assignments = [shard_for(name, shards) for name in names]
        assert set(assignments) == set(range(shards))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1/3", (1, 3)), ("3/3", (3, 3)), ("1/1", (1, 1))],
)
def test_parse_shard_valid(value: str, expected: tuple[int, int]):
    assert _parse_shard(value) == expected


@pytest.mark.parametrize("value", ("0/3", "4/3", "3/0", "abc", "1/2/3", "1", "-1/3"))
def test_parse_shard_invalid(value: str):
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_shard(value)


def test_slice_by_shard_is_disjoint_and_complete():
    """Slices are disjoint, cover everything, and match the shard function."""
    data = {str(i): {"full_name": f"user{i}/repo{i}"} for i in range(200)}
    shards = 3
    slices = [_slice_by_shard(data, index, shards) for index in range(shards)]

    keys = [set(entry) for entry in slices]
    assert set.union(*keys) == set(data)
    assert sum(len(entry) for entry in slices) == len(data)
    for first in range(shards):
        for second in range(first + 1, shards):
            assert keys[first].isdisjoint(keys[second])

    for index, entries in enumerate(slices):
        for value in entries.values():
            assert shard_for(value["full_name"], shards) == index


def test_slice_by_shard_single_shard_returns_all():
    data = {"1": {"full_name": "a/b"}}
    assert _slice_by_shard(data, 0, 1) == data


@pytest.mark.parametrize("shards", (1, 2, 3))
def test_write_and_merge_shard_partials_roundtrip(shards: int):
    """Writing disjoint shard partials and merging reassembles the full set.

    This mirrors the production shard -> merge data flow (``write_shard_output``
    followed by ``_load_shard_files``) without touching the network, so it needs
    no API-usage snapshots.
    """
    category = "integration"
    full = {str(i): {"full_name": f"user{i}/repo{i}"} for i in range(30)}

    shard_root = os.path.join(SHARDS_DIR, category)
    shutil.rmtree(shard_root, ignore_errors=True)

    written = 0
    for index in range(shards):
        shard_slice = _slice_by_shard(full, index, shards)
        written += len(shard_slice)
        write_shard_output(category, index + 1, shard_slice, shard_slice)

    # The shards partition the input: disjoint and complete.
    assert written == len(full)

    assert _load_shard_files(category, "data.json") == full
    assert _load_shard_files(category, "stored.json") == full

    shutil.rmtree(shard_root, ignore_errors=True)
