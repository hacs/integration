"""Validate HACS V2 data."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any
import voluptuous as vol

from custom_components.hacs.utils.validate import V2_REPOS_SCHEMA, V2_REPO_SCHEMA


def expand_and_humanize_error(content: dict[str, Any], error: vol.Error) -> str:
    """Expand and humanize error."""
    if isinstance(error, vol.MultipleInvalid):
        return ", ".join(
            sorted(
                expand_and_humanize_error(content, sub_error)
                for sub_error in error.errors
            )
        )
    return vol.humanize.humanize_error(content, error)

async def validate_category_data(category: str, file_path: str) -> None:
    """Validate category data."""
    target_path = os.path.join(os.getcwd(), file_path)

    def print_error_and_exit(err: str):
        print(f"::error::{err} in {target_path} for the {category} category")
        sys.exit(1)

    if not os.path.isfile(target_path):
        print_error_and_exit(f"File {target_path} does not exist")
    if category not in V2_REPO_SCHEMA:
        print_error_and_exit(f"Category {category} is not supported")

    with open(
        target_path,
        mode="r",
        encoding="utf-8",
    ) as data_file:
        contents: dict[str, dict[str, Any]] = json.loads(data_file.read())
        did_raise = False

        for repo, content in contents.items():
            try:
                V2_REPO_SCHEMA[category](content)
            except vol.Error as error:
                did_raise = True
                print(
                    f"::error::[{content.get('full_name', repo)}] "
                    f"Invalid data: {expand_and_humanize_error(content, error)}"
                )

        try:
            V2_REPOS_SCHEMA[category](contents)
        except vol.Error as error:
            did_raise = True
            print_error_and_exit(f"Invalid data: {expand_and_humanize_error(contents, error)}")

        if did_raise:
            print_error_and_exit("Validation did raise but did not exit!")
            sys.exit(1)  # Fallback, should not be reached

        print(
            f"All {len(contents)} entries for the "
            f"{category} category in {target_path} are valid."
        )


if __name__ == "__main__":
    asyncio.run(validate_category_data(sys.argv[1], sys.argv[2]))
