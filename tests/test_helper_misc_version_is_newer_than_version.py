"""Helpers: Misc: version_is_newer_than_version."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.misc import version_is_newer_than_version


def test_basic():
    assert version_is_newer_than_version("1.0.0", "0.9.9")
    assert version_is_newer_than_version("1", "0.9.9")
    assert version_is_newer_than_version("1.1", "0.9.9")
    assert version_is_newer_than_version("0.10.0", "0.9.9")
    assert not version_is_newer_than_version("0.0.10", "0.9.9")
    assert not version_is_newer_than_version("0.9.0", "0.9.9")
    assert version_is_newer_than_version("1.0.0", "1.0.0")


def test_beta():
    assert version_is_newer_than_version("1.0.0b1", "1.0.0b0")
    assert not version_is_newer_than_version("1.0.0b1", "1.0.0")
    assert version_is_newer_than_version("1.0.0", "1.0.0b1")


def test_wierd_stuff():
    assert version_is_newer_than_version("1.0.0rc1", "1.0.0b1")
    assert not version_is_newer_than_version("1.0.0a1", "1.0.0b1")
    assert version_is_newer_than_version("1.0.0", "1.0.0a0")
    assert version_is_newer_than_version("1.0.0", "1.0.0b0")
    assert version_is_newer_than_version("1.0.0", "1.0.0rc0")
    assert not version_is_newer_than_version(None, "1.0.0rc0")
    assert not version_is_newer_than_version(1.0, "1.0.0rc0")
    assert not version_is_newer_than_version({}, "1.0.0rc0")
