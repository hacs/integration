import pytest
from deepmerge.strategy.list import ListStrategies
from deepmerge import Merger


@pytest.fixture
def custom_merger():
    return Merger(
        [(list, ListStrategies.strategy_append_unique)],
        [],
        [],
    )


def test_strategy_append_unique(custom_merger):
    base = [1, 3, 2]
    nxt = [3, 5, 4, 1, 2]

    expected = [1, 3, 2, 5, 4]
    actual = custom_merger.merge(base, nxt)
    assert actual == expected


def test_strategy_append_unique_nested_dict(custom_merger):
    """append_unique should work even with unhashable objects
    Like dicts.
    """
    base = [{"bar": ["bob"]}]
    nxt = [{"bar": ["baz"]}]

    result = custom_merger.merge(base, nxt)

    assert result == [{"bar": ["bob"]}, {"bar": ["baz"]}]


def test_strategy_append_similar_dict(custom_merger):
    """append_unique should work for identical dicts,
    regardless of insertion order.
    """
    base = [{"bar": "bob", "foo": "baz"}]
    nxt = [{"x": "y"}, {"foo": "baz", "bar": "bob"}]

    result = custom_merger.merge(base, nxt)

    assert result == [{"bar": "bob", "foo": "baz"}, {"x": "y"}]
