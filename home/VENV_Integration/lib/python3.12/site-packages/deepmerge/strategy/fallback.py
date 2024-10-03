from __future__ import annotations

from typing import Any, TypeVar

import deepmerge.merger
from .core import StrategyList


T = TypeVar("T")


class FallbackStrategies(StrategyList):
    """
    The StrategyList containing fallback strategies.
    """

    NAME = "fallback"

    @staticmethod
    def strategy_override(config: deepmerge.merger.Merger, path: list, base: Any, nxt: T) -> T:
        """use nxt, and ignore base."""
        return nxt

    @staticmethod
    def strategy_use_existing(config: deepmerge.merger.Merger, path: list, base: T, nxt: Any) -> T:
        """use base, and ignore next."""
        return base
