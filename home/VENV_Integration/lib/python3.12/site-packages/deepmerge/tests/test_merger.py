import pytest
from deepmerge import Merger


@pytest.fixture
def custom_merger():
    def merge_sets(merger, path, base, nxt):
        base |= nxt
        return base

    def merge_list(merger, path, base, nxt):
        if len(nxt) > 0:
            base.append(nxt[-1])
            return base

    return Merger(
        [(list, merge_list), (dict, "merge"), (set, merge_sets)],
        [],
        [],
    )


def test_custom_merger_applied(custom_merger):
    result = custom_merger.merge({"foo"}, {"bar"})
    assert result == {"foo", "bar"}


def test_custom_merger_list(custom_merger):
    result = custom_merger.merge([1, 2, 3], [4, 5, 6])
    assert result == [1, 2, 3, 6]
