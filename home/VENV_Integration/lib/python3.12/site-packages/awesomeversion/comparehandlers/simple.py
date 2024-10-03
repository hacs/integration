"""Special handler for simple."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .sections import compare_base_sections

if TYPE_CHECKING:
    from awesomeversion import AwesomeVersion


def compare_handler_simple(
    version_a: AwesomeVersion,
    version_b: AwesomeVersion,
) -> bool | None:
    """Compare handler simple."""
    if version_a.simple and version_b.simple:
        return compare_base_sections(version_a, version_b)
    return None
