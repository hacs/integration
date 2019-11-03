"""HACS Manifest Test Suite."""
# pylint: disable=missing-docstring,invalid-name
from custom_components.hacs.hacsbase.exceptions import (
    HacsMissingManifest,
    HacsBlacklistException,
)

CUSTOM = "Test"


def test_HacsMissingManifest():
    base = HacsMissingManifest()
    assert base.message == "The manifest file is missing in the repository."

    custom = HacsMissingManifest(CUSTOM)
    assert custom.message == CUSTOM


def test_HacsBlacklistException():
    base = HacsBlacklistException()
    assert base.message == "The repository is currently in the blacklist."

    custom = HacsBlacklistException(CUSTOM)
    assert custom.message == CUSTOM
