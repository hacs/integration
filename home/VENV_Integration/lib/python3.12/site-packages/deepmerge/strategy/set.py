from __future__ import annotations

import deepmerge.merger
from .core import StrategyList


class SetStrategies(StrategyList):
    """
    Contains the strategies provided for sets.
    """

    NAME = "set"

    @staticmethod
    def strategy_union(config: deepmerge.merger.Merger, path: list, base: set, nxt: set) -> set:
        """
        use all values in either base or nxt.
        """
        return base | nxt

    @staticmethod
    def strategy_intersect(config: deepmerge.merger.Merger, path: list, base: set, nxt: set) -> set:
        """
        use all values in both base and nxt.
        """
        return base & nxt

    @staticmethod
    def strategy_override(config: deepmerge.merger.Merger, path: list, base: set, nxt: set) -> set:
        """
        use the set nxt.
        """
        return nxt
