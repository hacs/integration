from __future__ import annotations

import sys
from typing import Callable, Any

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import deepmerge.merger
from ..exception import StrategyNotFound, InvalidMerge

STRATEGY_END = object()

# Note: We use string annotations here to prevent circular import caused by Merger
StrategyCallable: TypeAlias = "Callable[[deepmerge.merger.Merger, list, Any, Any], Any]"
StrategyListInitable: TypeAlias = "str | StrategyCallable | list[str | StrategyCallable]"


class StrategyList:
    NAME: str

    def __init__(self, strategy_list: StrategyListInitable) -> None:
        if not isinstance(strategy_list, list):
            strategy_list = [strategy_list]
        self._strategies: list[StrategyCallable] = [self._expand_strategy(s) for s in strategy_list]

    @classmethod
    def _expand_strategy(cls, strategy: str | StrategyCallable) -> StrategyCallable:
        """
        :param strategy: string or function

        If the strategy is a string, attempt to resolve it
        among the built in strategies.

        Otherwise, return the value, implicitly assuming it's a function.
        """
        if isinstance(strategy, str):
            method_name = f"strategy_{strategy}"
            if hasattr(cls, method_name):
                return getattr(cls, method_name)
            raise StrategyNotFound(strategy)
        return strategy

    def __call__(self, config: deepmerge.merger.Merger, path: list, base: Any, nxt: Any) -> Any:
        for s in self._strategies:
            ret_val = s(config, path, base, nxt)
            if ret_val is not STRATEGY_END:
                return ret_val
        raise InvalidMerge(self.NAME, config, path, base, nxt)
