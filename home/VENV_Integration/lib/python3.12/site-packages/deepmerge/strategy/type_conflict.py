from __future__ import annotations

from typing import Any, TypeVar

import deepmerge.merger
from .core import StrategyList

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class TypeConflictStrategies(StrategyList):
    """contains the strategies provided for type conflicts."""

    NAME = "type conflict"

    @staticmethod
    def strategy_override(config: deepmerge.merger.Merger, path: list, base: Any, nxt: T1) -> T1:
        """overrides the new object over the old object"""
        return nxt

    @staticmethod
    def strategy_use_existing(
        config: deepmerge.merger.Merger, path: list, base: T1, nxt: Any
    ) -> T1:
        """uses the old object instead of the new object"""
        return base

    @staticmethod
    def strategy_override_if_not_empty(
        config: deepmerge.merger.Merger, path: list, base: T1, nxt: T2
    ) -> T1 | T2:
        """overrides the new object over the old object only if the new object is not empty or null"""
        return nxt if nxt else base
