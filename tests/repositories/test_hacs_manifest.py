"""HACS Manifest Test Suite."""
# pylint: disable=missing-docstring
import pytest
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.repositories.manifest import HacsManifest


def test_manifest_structure():
    manifest = HacsManifest.from_dict({"name": "TEST"})

    assert isinstance(manifest.manifest, dict)

    assert isinstance(manifest.name, str)
    assert manifest.name == "TEST"

    assert isinstance(manifest.content_in_root, bool)
    assert not manifest.content_in_root

    assert isinstance(manifest.zip_release, bool)
    assert not manifest.zip_release

    assert isinstance(manifest.filename, (str, type(None)))
    assert manifest.filename is None

    assert isinstance(manifest.domains, list)
    assert not manifest.domains

    assert isinstance(manifest.country, list)
    assert not manifest.country

    assert isinstance(manifest.homeassistant, (str, type(None)))
    assert manifest.homeassistant is None

    assert isinstance(manifest.persistent_directory, (str, type(None)))
    assert manifest.persistent_directory is None

    assert isinstance(manifest.iot_class, (str, type(None)))
    assert manifest.iot_class is None

    assert isinstance(manifest.render_readme, bool)
    assert not manifest.render_readme

    assert isinstance(manifest.hacs, (str, type(None)))
    assert not manifest.hacs

    assert isinstance(manifest.hide_default_branch, bool)
    assert not manifest.hide_default_branch


def test_edge_pass_none():
    with pytest.raises(HacsException):
        assert HacsManifest.from_dict(None)
