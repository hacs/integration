from deepmerge.strategy.set import SetStrategies


def test_union_unions():
    assert SetStrategies.strategy_union({}, [], set("abc"), set("bcd")) == set("abcd")


def test_intersect_intersects():
    assert SetStrategies.strategy_intersect({}, [], set("abc"), set("bcd")) == set("bc")


def test_override_overrides():
    assert SetStrategies.strategy_override({}, [], set("abc"), set("bcd")) == set("bcd")
