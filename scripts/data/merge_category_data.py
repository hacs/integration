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
from .generate_category_data import SHARDS_DIR, AdjustedHacs, finalize_category_output


def _load_shard_files(category: str, name: str) -> dict[str, dict[str, Any]]:
    """Combine one partial file from every shard of a category."""
    paths = sorted(Path(SHARDS_DIR, category).glob(f"*/{name}"))
    if not paths:
        print_error_and_exit(f"No shard {name} files found", category)
    merged = {}
    for path in paths:
        merged.update(json.loads(path.read_text(encoding="utf-8")))
    return merged


async def merge_category_data(category: str) -> None:
    """Merge the shards of a category and write the final output."""
    updated_data = _load_shard_files(category, "data.json")
    stored_data = _load_shard_files(category, "stored.json")
    async with ClientSession() as session:
        hacs = AdjustedHacs(session=session, token=os.getenv("DATA_GENERATOR_TOKEN"))
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
    args = parser.parse_args()
    asyncio.run(merge_category_data(args.category))
