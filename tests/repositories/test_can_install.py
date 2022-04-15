"""Configuration Test Suite: can install."""
# pylint: disable=missing-docstring
from awesomeversion import AwesomeVersion

from custom_components.hacs.repositories.base import HacsManifest, HacsRepository


def test_hacs_can_install(hacs):
    repository = HacsRepository(hacs)
    repository.repository_manifest = HacsManifest.from_dict({"test": "test"})
    repository.data.releases = True

    hacs.core.ha_version = AwesomeVersion("1.0.0")
    repository.repository_manifest.homeassistant = "1.0.0b1"
    assert repository.can_download

    hacs.core.ha_version = AwesomeVersion("1.0.0b1")
    repository.repository_manifest.homeassistant = "1.0.0"
    assert not repository.can_download

    hacs.core.ha_version = AwesomeVersion("1.0.0b1")
    repository.repository_manifest.homeassistant = "1.0.0b2"
    assert not repository.can_download

    hacs.core.ha_version = AwesomeVersion("1.0.0")
    repository.repository_manifest.homeassistant = "1.0.0"
    assert repository.can_download
