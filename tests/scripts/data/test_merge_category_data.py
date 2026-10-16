"""Test merge category data."""

import pytest

from scripts.data.generate_category_data import (
    _slice_by_shard,
    shard_for,
    write_shard_output,
)
from scripts.data.merge_category_data import _load_shard_data


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
