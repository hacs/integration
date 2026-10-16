"""Test merge category data."""

import pytest

from scripts.data.generate_category_data import _slice_by_shard, write_shard_output
from scripts.data.merge_category_data import _load_shard_files


@pytest.fixture
def shards_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Write and read shard output in a temporary directory."""
    monkeypatch.setattr("scripts.data.generate_category_data.SHARDS_DIR", str(tmp_path))
    monkeypatch.setattr("scripts.data.merge_category_data.SHARDS_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.usefixtures("shards_dir")
@pytest.mark.parametrize("shards", [1, 2, 3])
def test_load_shard_files_reassembles_shards(shards: int):
    """Test that merging the shards gives back the full category."""
    full = {str(i): {"full_name": f"user{i}/repo{i}"} for i in range(30)}

    for index in range(shards):
        shard_slice = _slice_by_shard(full, index, shards)
        write_shard_output("integration", index + 1, shard_slice, shard_slice)

    assert _load_shard_files("integration", "data.json") == full
    assert _load_shard_files("integration", "stored.json") == full


@pytest.mark.usefixtures("shards_dir")
def test_load_shard_files_without_shards():
    """Test that merging fails when there are no shard files."""
    with pytest.raises(SystemExit):
        _load_shard_files("integration", "data.json")
