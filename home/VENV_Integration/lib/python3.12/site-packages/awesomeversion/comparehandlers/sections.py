"""Special handler for sections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.regex import RE_IS_SINGLE_DIGIT, RE_MODIFIER

if TYPE_CHECKING:
    from ..awesomeversion import AwesomeVersion

MODIFIERS = {"rc": 3, "beta": 2, "b": 2, "alpha": 1, "a": 1, "dev": 0, "d": 0}


def compare_handler_sections(
    version_a: AwesomeVersion,
    version_b: AwesomeVersion,
) -> bool | None:
    """Compare handler sections."""
    base = compare_base_sections(version_a, version_b)
    if base is not None:
        return base
    return compare_modifier_section(version_a, version_b)


def compare_base_sections(
    version_a: AwesomeVersion,
    version_b: AwesomeVersion,
) -> bool | None:
    """Compare base sections between two AwesomeVersion objects."""
    biggest = (
        version_a.sections
        if version_a.sections >= version_b.sections
        else version_b.sections
    )
    for section in range(0, biggest):
        ver_a_section = version_a.section(section)
        ver_b_section = version_b.section(section)
        if ver_a_section == ver_b_section:
            continue
        if ver_a_section > ver_b_section:
            return True
        if ver_a_section < ver_b_section:
            return False
    return None


def compare_modifier_section(
    version_a: AwesomeVersion,
    version_b: AwesomeVersion,
) -> bool | None:
    """Compare modifiers between two AwesomeVersion objects."""
    if version_a.modifier is None and version_b.modifier is not None:
        return True
    if version_a.modifier is not None and version_b.modifier is not None:
        version_a_modifier = RE_MODIFIER.match(version_a.string.split(".")[-1])
        version_b_modifier = RE_MODIFIER.match(version_b.string.split(".")[-1])
        if version_a_modifier and version_b_modifier:
            if version_a_modifier.group(3) == version_b_modifier.group(3):
                return int(version_a_modifier.group(4) or 0) > int(
                    version_b_modifier.group(4) or 0
                )
            mod_a = MODIFIERS.get(version_a_modifier.group(3))
            mod_b = MODIFIERS.get(version_b_modifier.group(3))
            if mod_a is not None and mod_b is not None:
                return mod_a > mod_b
            return version_a_modifier.group(3) > version_a_modifier.group(3)
        if RE_IS_SINGLE_DIGIT.match(version_a.modifier) and RE_IS_SINGLE_DIGIT.match(
            version_b.modifier
        ):
            return int(version_a.modifier) > int(version_b.modifier)
    return None
