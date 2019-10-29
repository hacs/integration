"""HACS Manifest Test Suite."""
# pylint: disable=missing-docstring
import pytest
from custom_components.hacs.hacsbase.exceptions import HacsRepositoryInfo
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

    assert isinstance(manifest.filename, type(None))
    assert manifest.filename is None

    assert isinstance(manifest.domains, list)
    assert not manifest.domains

    assert isinstance(manifest.country, list)
    assert not manifest.country

    assert isinstance(manifest.homeassistant, type(None))
    assert manifest.homeassistant is None

    assert isinstance(manifest.persistent_directory, type(None))
    assert manifest.persistent_directory is None

    assert isinstance(manifest.iot_class, type(None))
    assert manifest.iot_class is None

    assert isinstance(manifest.render_readme, bool)
    assert not manifest.render_readme

    assert isinstance(manifest.hacs, str)
    assert not manifest.hacs


def test_edge_pass_none():
    with pytest.raises(HacsRepositoryInfo):
        assert HacsManifest.from_dict(None)
