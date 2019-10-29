"""Helpers: Misc: get_repository_name."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.misc import get_repository_name
from custom_components.hacs.repositories.manifest import HacsManifest
from custom_components.hacs.const import ELEMENT_TYPES

ELEMENT_TYPES = ELEMENT_TYPES + ["appdaemon", "python_script", "theme"]


def test_everything():
    hacs_manifest = HacsManifest.from_dict({"name": "TEST-HACS_MANIFEST"})
    manifest = {"name": "TEST-MANIFEST"}
    repository_name = "TEST-REPOSITORY-NAME"

    for category in ELEMENT_TYPES:
        name = get_repository_name(hacs_manifest, repository_name, category, manifest)
        assert name == "TEST-HACS_MANIFEST"


def test_integration_manifest():
    hacs_manifest = HacsManifest.from_dict({})
    manifest = {"name": "TEST-MANIFEST"}
    repository_name = "TEST-REPOSITORY-NAME"

    name = get_repository_name(hacs_manifest, repository_name, "integration", manifest)
    assert name == "TEST-MANIFEST"


def test_repository_name():
    hacs_manifest = HacsManifest.from_dict({})
    repository_name = "TEST-REPOSITORY-NAME"

    name = get_repository_name(hacs_manifest, repository_name, "plugin")
    assert name == "Test Repository Name"
