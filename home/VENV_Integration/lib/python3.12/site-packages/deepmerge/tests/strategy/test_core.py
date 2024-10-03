from deepmerge.strategy.core import StrategyList
from deepmerge import STRATEGY_END


def return_true_if_foo(config, path, base, nxt):
    if base == "foo":
        return True
    return STRATEGY_END


def always_return_custom(config, path, base, nxt):
    return "custom"


def test_first_working_strategy_is_used():
    """
    In the case where the StrategyList has multiple values,
    the first strategy which returns a valid value (i.e. not STRATEGY_END)
    should be returned.
    """
    sl = StrategyList(
        [
            return_true_if_foo,
            always_return_custom,
        ]
    )
    # return_true_if_foo will take.
    assert sl({}, [], "foo", "bar") is True
    # return_true_if_foo will fail,
    # which will then activea always_return_custom
    assert sl({}, [], "bar", "baz") == "custom"
