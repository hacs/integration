"""Validate HACS V2 data."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import voluptuous as vol

from custom_components.hacs.utils.validate import V2_REPOS_SCHEMA


def expand_and_humanize_error(content: dict[str, Any], error: vol.Error) -> list[str] | str:
    """Expand and humanize error."""
    if isinstance(error, vol.MultipleInvalid):
        return sorted(expand_and_humanize_error(content, sub_error) for sub_error in error.errors)

    repoid = error.path[0]
    return f"[{content[repoid].get('full_name', repoid)}] {vol.humanize.humanize_error(content, error)}"


async def validate_category_data(category: str, file_path: str) -> None:
    """Validate category data."""
    target_path = os.path.join(os.getcwd(), file_path)

    def print_error_and_exit(err: str):
        print(f"::error::{err} in {target_path} for the {category} category")
        sys.exit(1)

    if not os.path.isfile(target_path):
        print_error_and_exit(f"File {target_path} does not exist")
    if category not in V2_REPOS_SCHEMA:
        print_error_and_exit(f"Category {category} is not supported")

    with open(
        target_path,
        encoding="utf-8",
    ) as data_file:
        contents: dict[str, dict[str, Any]] = json.loads(data_file.read())
        did_raise = False

        if not data_file or len(contents) == 0 or not isinstance(contents, dict):
            print_error_and_exit(f"File {target_path} is empty")

        try:
            V2_REPOS_SCHEMA[category](contents)
        except vol.Error as error:
            did_raise = True
            errors = expand_and_humanize_error(contents, error)
            if isinstance(errors, list):
                for err in errors:
                    print(f"::error::{err}")
                sys.exit(1)

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
