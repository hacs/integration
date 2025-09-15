"""Validate HACS V2 data."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import voluptuous as vol

from custom_components.hacs.const import HACS_REPOSITORY_ID
from custom_components.hacs.utils.validate import VALIDATE_GENERATED_V2_REPO_DATA

from .common import expand_and_humanize_error, print_error_and_exit


async def validate_category_data(category: str, file_path: str) -> None:
    """Validate category data."""
    target_path = os.path.join(os.getcwd(), file_path)

    if not os.path.isfile(target_path):
        print_error_and_exit(f"File {target_path} does not exist", category, file_path)
    if category not in VALIDATE_GENERATED_V2_REPO_DATA:
        print_error_and_exit(f"Category {category} is not supported", category, file_path)

    with open(
        target_path,
        encoding="utf-8",
    ) as data_file:
        contents: dict[str, dict[str, Any]] = json.loads(data_file.read())
        did_raise = False

        if not contents or len(contents) == 0 or not isinstance(contents, dict):
            print_error_and_exit(f"File {target_path} is empty", category, file_path)

        try:
            VALIDATE_GENERATED_V2_REPO_DATA[category](contents)
        except vol.Invalid as error:
            did_raise = True
            errors = expand_and_humanize_error(contents, error)
            if isinstance(errors, list):
                for err in errors:
                    print(f"::error::{err}")
                sys.exit(1)

            print_error_and_exit(f"Invalid data: {errors}", category, file_path)

        if category == "integration" and HACS_REPOSITORY_ID not in contents:
            did_raise = True
            print_error_and_exit(
                "HACS is missing...", category, file_path
            )

        if did_raise:
            print_error_and_exit("Validation did raise but did not exit!", category, file_path)
            sys.exit(1)  # Fallback, should not be reached

        print(
            f"All {len(contents)} entries for the "
            f"{category} category in {target_path} are valid."
        )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 -m scripts.data.validate_category_data <category> <file>")
        sys.exit(1)
    asyncio.run(validate_category_data(sys.argv[1], sys.argv[2]))
