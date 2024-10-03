from __future__ import annotations

from typing import Any

import deepmerge.merger


class DeepMergeException(Exception):
    "Base class for all `deepmerge` Exceptions"


class StrategyNotFound(DeepMergeException):
    "Exception for when a strategy cannot be located"


class InvalidMerge(DeepMergeException):
    "Exception for when unable to complete a merge operation"

    def __init__(
        self,
        strategy_list_name: str,
        config: deepmerge.merger.Merger,
        path: list,
        base: Any,
        nxt: Any,
    ) -> None:
        super().__init__(
            f"Could not merge using {strategy_list_name!r} [{config=}, {path=}, {base=}, {nxt=}]"
        )
        self.strategy_list_name = strategy_list_name
        self.config = config
        self.path = path
        self.base = base
        self.nxt = nxt
        return
