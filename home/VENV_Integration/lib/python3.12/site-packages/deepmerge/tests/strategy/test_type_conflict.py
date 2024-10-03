from typing import Dict

from deepmerge.strategy.type_conflict import TypeConflictStrategies

EMPTY_DICT: Dict = {}

CONTENT_AS_LIST = [{"key": "val"}]


def test_merge_if_not_empty():
    strategy = TypeConflictStrategies.strategy_override_if_not_empty(
        {}, [], EMPTY_DICT, CONTENT_AS_LIST
    )
    assert strategy == CONTENT_AS_LIST

    strategy = TypeConflictStrategies.strategy_override_if_not_empty(
        {}, [], CONTENT_AS_LIST, EMPTY_DICT
    )
    assert strategy == CONTENT_AS_LIST

    strategy = TypeConflictStrategies.strategy_override_if_not_empty({}, [], CONTENT_AS_LIST, None)
    assert strategy == CONTENT_AS_LIST
