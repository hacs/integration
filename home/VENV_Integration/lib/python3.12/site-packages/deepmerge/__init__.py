from __future__ import annotations

from .merger import Merger
from .strategy.core import STRATEGY_END  # noqa

# some standard mergers available

DEFAULT_TYPE_SPECIFIC_MERGE_STRATEGIES: list[tuple[type, str]] = [
    (list, "append"),
    (dict, "merge"),
    (set, "union"),
]

# this merge will never raise an exception.
# in the case of type mismatches,
# the value from the second object
# will override the previous one.
always_merger: Merger = Merger(DEFAULT_TYPE_SPECIFIC_MERGE_STRATEGIES, ["override"], ["override"])

# this merge strategies attempts
# to merge (append for list, unify for dicts)
# if possible, but raises an exception
# in the case of type conflicts.
merge_or_raise: Merger = Merger(DEFAULT_TYPE_SPECIFIC_MERGE_STRATEGIES, [], [])

# a conservative merge tactic:
# for data structures with a specific
# strategy, keep the existing value.
# similar to always_merger but instead
# keeps existing values when faced
# with a type conflict.
conservative_merger: Merger = Merger(
    DEFAULT_TYPE_SPECIFIC_MERGE_STRATEGIES, ["use_existing"], ["use_existing"]
)
