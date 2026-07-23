"""Merge sharded HACS data into a single per-category output.

Each shard of a category produces a partial ``data.json`` (its slice of the
generated data) and a partial ``stored.json`` (its slice of the currently
published data) under ``outputdata/_shards/<category>/<shard>/``. This script
concatenates those partials back into the full dataset and runs the shared
``finalize_category_output`` step, which computes the summary and diff and
validates the complete category data.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
from typing import Any

from aiohttp import ClientSession

from .common import print_error_and_exit
from .generate_category_data import (
    SHARDS_DIR,
    AdjustedHacs,
    finalize_category_output,
)


def _load_shard_files(category: str, name: str) -> dict[str, dict[str, Any]]:
    """Merge a given partial file across all shards of a category."""
    merged: dict[str, dict[str, Any]] = {}
    paths = sorted(glob.glob(os.path.join(SHARDS_DIR, category, "*", name)))
    if not paths:
        print_error_and_exit(f"No shard '{name}' files found", category)
    for path in paths:
        with open(path, encoding="utf-8") as shard_file:
            shard_data = json.load(shard_file)
        overlap = merged.keys() & shard_data.keys()
        if overlap:
            print_error_and_exit(
                f"Duplicate keys across shards in '{name}': {sorted(overlap)[:5]}",
                category,
            )
        merged.update(shard_data)
    return merged


async def merge_category_data(category: str) -> None:
    """Merge all shards for a category and write the final output."""
    updated_data = _load_shard_files(category, "data.json")
    stored_data = _load_shard_files(category, "stored.json")

    async with ClientSession() as session:
        hacs = AdjustedHacs(
            session=session, token=os.getenv("DATA_GENERATOR_TOKEN"))
        await finalize_category_output(
            hacs,
            category,
            stored_data,
            stored_data,
            updated_data,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge sharded HACS data.")
    parser.add_argument("category")
    args = parser.parse_args()
    asyncio.run(merge_category_data(args.category))
