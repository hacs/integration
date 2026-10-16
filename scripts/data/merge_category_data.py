"""Merge sharded HACS data into the output for a category."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from aiohttp import ClientSession

from .common import print_error_and_exit
from .generate_category_data import (
    SHARDS_DIR,
    AdjustedHacs,
    finalize_category_output,
    get_stored_data,
)


def _load_shard_data(category: str, shards: int) -> dict[str, dict[str, Any]]:
    """Combine the generated data of shards 1 to shards of a category."""
    shard_root = Path(SHARDS_DIR, category)
    paths = [shard_root / str(number) / "data.json" for number in range(1, shards + 1)]
    found = set(shard_root.glob("*/data.json"))
    if found != set(paths):
        names = sorted(path.parent.name for path in found)
        print_error_and_exit(f"Expected shards 1 to {shards}, found {names}", category)
    merged = {}
    for path in paths:
        for key, value in json.loads(path.read_text(encoding="utf-8")).items():
            # A renamed repository can be restored from cache under its old name in one
            # shard and refreshed under its new name in another; keep the fresher record.
            existing = merged.get(key)
            if existing is None or value.get("last_fetched", 0) > existing.get("last_fetched", 0):
                merged[key] = value
    return merged


async def merge_category_data(category: str, shards: int) -> None:
    """Merge the shards of a category and write the final output."""
    updated_data = _load_shard_data(category, shards)
    async with ClientSession() as session:
        hacs = AdjustedHacs(session=session, token=os.getenv("DATA_GENERATOR_TOKEN"))
        stored_data = await get_stored_data(hacs, category)
        await finalize_category_output(
            hacs,
            category,
            stored_data=stored_data,
            current_data=stored_data,
            updated_data=updated_data,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge sharded HACS data.")
    parser.add_argument("category")
    parser.add_argument(
        "--shards",
        type=int,
        required=True,
        help="number of shards the category was generated in",
    )
    args = parser.parse_args()
    asyncio.run(merge_category_data(args.category, args.shards))
