"""Common helpers for data."""
from __future__ import annotations

import sys
from typing import Any

import voluptuous as vol


def expand_and_humanize_error(content: dict[str, Any], error: vol.Invalid) -> list[str] | str:
    """Expand and humanize error."""
    if isinstance(error, vol.MultipleInvalid):
        return sorted(expand_and_humanize_error(content, sub_error) for sub_error in error.errors)

    repoid = error.path[0]
    return f"[{content[repoid].get('full_name', repoid)}] {vol.humanize.humanize_error(content, error)}"


def print_error_and_exit(err: str, category: str, target_path: str | None = None):
    if target_path:
        print(f"::error::{err} for the {category} category in {target_path}")
    else:
        print(f"::error::{err} for the {category} category")
    sys.exit(1)
