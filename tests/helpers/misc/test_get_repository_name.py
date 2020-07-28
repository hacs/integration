"""Helpers: Misc: get_repository_name."""
from custom_components.hacs.const import ELEMENT_TYPES

# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.misc import get_repository_name
from custom_components.hacs.helpers.classes.manifest import HacsManifest
from tests.dummy_repository import dummy_repository_base

ELEMENT_TYPES = ELEMENT_TYPES + ["appdaemon", "python_script", "theme"]


def test_everything():
    repository = dummy_repository_base()
    repository.data.full_name = "test/TEST-REPOSITORY-NAME"
    repository.data.full_name_lower = "test/TEST-REPOSITORY-NAME".lower()
    repository.repository_manifest = HacsManifest.from_dict(
        {"name": "TEST-HACS_MANIFEST"}
    )
    repository.integration_manifest = {"name": "TEST-MANIFEST"}

    for category in ELEMENT_TYPES:
        repository.data.category = category
        name = get_repository_name(repository)
        assert name == "TEST-HACS_MANIFEST"


def test_integration_manifest():
    repository = dummy_repository_base()
    repository.data.category = "integration"
    repository.data.full_name = "test/TEST-REPOSITORY-NAME"
    repository.data.full_name_lower = "test/TEST-REPOSITORY-NAME".lower()
    repository.repository_manifest = HacsManifest.from_dict({})
    repository.integration_manifest = {"name": "TEST-MANIFEST"}

    name = get_repository_name(repository)
    assert name == "TEST-MANIFEST"


def test_repository_name():
    repository = dummy_repository_base()
    repository.data.full_name = "test/TEST-REPOSITORY-NAME"
    repository.data.full_name_lower = "test/TEST-REPOSITORY-NAME".lower()
    repository.repository_manifest = HacsManifest.from_dict({})

    name = get_repository_name(repository)
    assert name == "Test Repository Name"
