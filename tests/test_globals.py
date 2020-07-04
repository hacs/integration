"""Test globals."""
# pylint: disable=missing-docstring
from custom_components.hacs.hacs import (
    get_hacs,
    get_removed,
    is_removed,
    removed_repositories,
)


def test_global_hacs():
    hacs = get_hacs()
    assert hacs.system.lovelace_mode == "storage"
    hacs.system.lovelace_mode = "yaml"
    hacs = get_hacs()
    assert hacs.system.lovelace_mode == "yaml"


def test_is_removed():
    repo = "test/test"
    assert not is_removed(repo)


def test_get_removed():
    repo = "removed/removed"
    removed = get_removed(repo)
    assert removed.repository == repo
