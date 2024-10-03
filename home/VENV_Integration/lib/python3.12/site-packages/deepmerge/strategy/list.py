from __future__ import annotations

import deepmerge.merger
from .core import StrategyList
from ..extended_set import ExtendedSet


class ListStrategies(StrategyList):
    """
    Contains the strategies provided for lists.
    """

    NAME = "list"

    @staticmethod
    def strategy_override(
        config: deepmerge.merger.Merger, path: list, base: list, nxt: list
    ) -> list:
        """use the list nxt."""
        return nxt

    @staticmethod
    def strategy_prepend(
        config: deepmerge.merger.Merger, path: list, base: list, nxt: list
    ) -> list:
        """prepend nxt to base."""
        return nxt + base

    @staticmethod
    def strategy_append(config: deepmerge.merger.Merger, path: list, base: list, nxt: list) -> list:
        """append nxt to base."""
        return base + nxt

    @staticmethod
    def strategy_append_unique(
        config: deepmerge.merger.Merger, path: list, base: list, nxt: list
    ) -> list:
        """append items without duplicates in nxt to base."""
        base_as_set = ExtendedSet(base)
        return base + [n for n in nxt if n not in base_as_set]
