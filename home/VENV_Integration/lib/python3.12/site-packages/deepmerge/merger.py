from __future__ import annotations

from typing import Any, Sequence, TypeVar

from . import strategy as s

_T = TypeVar("_T")


class Merger:
    """
    Merges objects based on provided strategies

    :param type_strategies, List[Tuple]: a list of (Type, Strategy) pairs
           that should be used against incoming types. For example: (dict, "override").
    """

    PROVIDED_TYPE_STRATEGIES: dict[type, type[s.StrategyList]] = {
        list: s.ListStrategies,
        dict: s.DictStrategies,
        set: s.SetStrategies,
    }

    def __init__(
        self,
        type_strategies: Sequence[tuple[type, s.StrategyCallable | s.StrategyListInitable]],
        fallback_strategies: s.StrategyListInitable,
        type_conflict_strategies: s.StrategyListInitable,
    ) -> None:
        self._fallback_strategy = s.FallbackStrategies(fallback_strategies)
        self._type_conflict_strategy = s.TypeConflictStrategies(type_conflict_strategies)

        self._type_strategies: list[tuple[type, s.StrategyCallable]] = []
        for typ, strategy in type_strategies:
            if typ in self.PROVIDED_TYPE_STRATEGIES:
                # Customise a StrategyList instance for this type
                self._type_strategies.append((typ, self.PROVIDED_TYPE_STRATEGIES[typ](strategy)))
            elif callable(strategy):
                self._type_strategies.append((typ, strategy))
            else:
                raise ValueError(f"Cannot handle ({typ}, {strategy})")
        return

    def merge(self, base: _T, nxt: _T) -> _T:
        return self.value_strategy([], base, nxt)

    def type_conflict_strategy(self, path: list, base: Any, nxt: Any) -> Any:
        return self._type_conflict_strategy(self, path, base, nxt)

    def value_strategy(self, path: list, base: _T, nxt: _T) -> _T:
        # Check for strategy based on type of base, next
        for typ, strategy in self._type_strategies:
            if isinstance(base, typ) and isinstance(nxt, typ):
                # We have a strategy for this type
                return strategy(self, path, base, nxt)

        if isinstance(base, type(nxt)) or isinstance(nxt, type(base)):
            # no known strategy but base, next are similar types
            return self._fallback_strategy(self, path, base, nxt)

        # No known strategy and base, next are different types.
        return self.type_conflict_strategy(path, base, nxt)
