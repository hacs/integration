"""Test merge category data."""

import json
import os
import shutil
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
import pytest

from scripts.data.generate_category_data import (
    OUTPUT_DIR,
    _slice_by_shard,
    generate_category_data,
    shard_for,
    write_shard_output,
)
from scripts.data.merge_category_data import _load_shard_data, merge_category_data

from tests.common import MockedResponse, ResponseMocker, recursive_remove_key

_MODULE = "scripts.data.merge_category_data"


@pytest.fixture
def shards_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Write and read shard output in a temporary directory."""
    monkeypatch.setattr("scripts.data.generate_category_data.SHARDS_DIR", str(tmp_path))
    monkeypatch.setattr("scripts.data.merge_category_data.SHARDS_DIR", str(tmp_path))
    return tmp_path


def _write_shards(full: dict, shards: int, skip: int | None = None) -> None:
    for index in range(shards):
        if index + 1 != skip:
            write_shard_output("integration", index + 1, _slice_by_shard(full, index, shards))


FULL = {str(i): {"full_name": f"user{i}/repo{i}"} for i in range(30)}


@pytest.mark.usefixtures("shards_dir")
@pytest.mark.parametrize("shards", [1, 2, 3])
def test_load_shard_data_reassembles_shards(shards: int):
    """Test that merging the shards gives back the full category."""
    _write_shards(FULL, shards)

    assert _load_shard_data("integration", shards) == FULL


@pytest.mark.usefixtures("shards_dir")
def test_load_shard_data_without_shards():
    """Test that merging fails when there are no shard files."""
    with pytest.raises(SystemExit):
        _load_shard_data("integration", 3)


@pytest.mark.usefixtures("shards_dir")
@pytest.mark.parametrize("missing", [1, 2, 3])
def test_load_shard_data_with_missing_shard(missing: int):
    """Test that merging fails when one expected shard is missing."""
    _write_shards(FULL, 3, skip=missing)

    with pytest.raises(SystemExit):
        _load_shard_data("integration", 3)


@pytest.mark.usefixtures("shards_dir")
@pytest.mark.parametrize("missing", [None, 3])
def test_load_shard_data_with_unexpected_shard(missing: int | None):
    """Test that an unexpected shard can't stand in for a missing one."""
    _write_shards(FULL, 3, skip=missing)
    write_shard_output("integration", 4, {})

    with pytest.raises(SystemExit):
        _load_shard_data("integration", 3)


@pytest.mark.usefixtures("shards_dir")
@pytest.mark.parametrize(
    ("old_name", "new_name"),
    [
        ("hacs-test-org/theme-basic", "hacs/integration"),
        ("hacs/integration", "hacs-test-org/theme-basic"),
    ],
)
def test_load_shard_data_keeps_refreshed_renamed_repository(old_name: str, new_name: str):
    """Test that a renamed repository found in two shards keeps the refreshed record."""
    shards = 3
    old_shard = shard_for(old_name, shards) + 1
    new_shard = shard_for(new_name, shards) + 1
    assert old_shard != new_shard

    stale = {"1": {"full_name": old_name, "last_fetched": 1.0}}
    fresh = {"1": {"full_name": new_name, "last_fetched": 2.0}}

    write_shard_output("integration", old_shard, stale)
    write_shard_output("integration", new_shard, fresh)
    (other_shard,) = {1, 2, 3} - {old_shard, new_shard}
    write_shard_output("integration", other_shard, {})

    assert _load_shard_data("integration", shards) == fresh


async def test_merge_category_data_finalizes_merged_shards(shards_dir):
    """Test that the merged shards are finalized against the stored snapshot."""
    _write_shards(FULL, 2)
    stored = {"1": {"full_name": "user1/repo1"}}
    with (
        patch(f"{_MODULE}.AdjustedHacs") as adjusted_hacs,
        patch(f"{_MODULE}.get_stored_data", AsyncMock(return_value=stored)) as get_stored,
        patch(f"{_MODULE}.finalize_category_output", AsyncMock()) as finalize,
    ):
        await merge_category_data("integration", 2)

    hacs = adjusted_hacs.return_value
    get_stored.assert_awaited_once_with(hacs, "integration")
    finalize.assert_awaited_once_with(
        hacs, "integration", stored_data=stored, current_data=stored, updated_data=FULL
    )


def _read_category_output(category: str) -> dict[str, Any]:
    output = {}
    for name in ("data.json", "repositories.json"):
        with open(os.path.join(OUTPUT_DIR, category, name), encoding="utf-8") as file:
            output[name] = recursive_remove_key(json.load(file), ("last_fetched",))
    with open(os.path.join(OUTPUT_DIR, "summary.json"), encoding="utf-8") as file:
        output["summary.json"] = json.load(file)
    return output


@pytest.mark.usefixtures("shards_dir")
@pytest.mark.parametrize("shards", [1, 2])
async def test_sharded_run_matches_unsharded_run(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    shards: int,
):
    """Test that generating every shard and merging gives the unsharded output."""
    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/data.json",
        MockedResponse(content={}, keep=True),
    )
    await generate_category_data("integration")
    expected = _read_category_output("integration")
    shutil.rmtree(os.path.join(OUTPUT_DIR, "integration"))
    os.remove(os.path.join(OUTPUT_DIR, "summary.json"))

    for shard in range(1, shards + 1):
        await generate_category_data("integration", shard=(shard, shards))
    assert not os.path.exists(os.path.join(OUTPUT_DIR, "integration", "data.json"))
    assert not os.path.exists(os.path.join(OUTPUT_DIR, "summary.json"))

    await merge_category_data("integration", shards)

    assert _read_category_output("integration") == expected
