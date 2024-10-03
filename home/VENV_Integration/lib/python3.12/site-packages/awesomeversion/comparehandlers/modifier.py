"""Special handler for modifier."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..strategy import VERSION_STRATEGIES_DICT, AwesomeVersionStrategy
from ..utils.regex import RE_MODIFIER

SEMVER_MODIFIER_MAP = {"dev": 0, "alpha": 1, "beta": 2, "rc": 3}

if TYPE_CHECKING:
    from awesomeversion import AwesomeVersion


def compare_handler_semver_modifier(
    version_a: AwesomeVersion,
    version_b: AwesomeVersion,
) -> bool | None:
    """Compare handler sections."""
    if AwesomeVersionStrategy.SEMVER not in (
        version_a.strategy,
        version_b.strategy,
    ) or (version_a.modifier_type is None or version_b.modifier_type is None):
        return None

    if version_a.modifier_type != version_b.modifier_type:
        mod_a = SEMVER_MODIFIER_MAP.get(version_a.modifier_type)
        mod_b = SEMVER_MODIFIER_MAP.get(version_b.modifier_type)
        if mod_a is not None and mod_b is not None:
            return mod_a > mod_b

    ver_a_modifier, ver_b_modifier = None, None

    semver_pattern = VERSION_STRATEGIES_DICT[AwesomeVersionStrategy.SEMVER].pattern

    semver_match = semver_pattern.match(version_a.string)
    if semver_match and len(semver_match.groups()) >= 4:
        modifier_match = RE_MODIFIER.match(semver_match.group(4))
        if modifier_match and len(modifier_match.groups()) >= 4:
            ver_a_modifier = modifier_match.group(4)

    semver_match = semver_pattern.match(version_b.string)
    if semver_match and len(semver_match.groups()) >= 4:
        modifier_match = RE_MODIFIER.match(semver_match.group(4))
        if modifier_match and len(modifier_match.groups()) >= 4:
            ver_b_modifier = modifier_match.group(4)

    if not ver_a_modifier or not ver_b_modifier:
        return True

    return int(ver_a_modifier) > int(ver_b_modifier)
