"""Test globals."""
# pylint: disable=missing-docstring
from custom_components.hacs.share import get_removed, is_removed


def test_global_hacs(hacs):
    assert hacs.core.lovelace_mode == "storage"
    hacs.core.lovelace_mode = "yaml"


def test_is_removed():
    repo = "test/test"
    assert not is_removed(repo)


def test_get_removed():
    repo = "removed/removed"
    removed = get_removed(repo)
    assert removed.repository == repo
