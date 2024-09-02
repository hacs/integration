"""Configuration Test Suite: can install."""
# pylint: disable=missing-docstring
from awesomeversion import AwesomeVersion

from custom_components.hacs.base import HacsBase


def test_display_status(hacs: HacsBase):
    repository = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repository.display_status == "default"

    repository.data.new = True
    assert repository.display_status == "new"
    repository.data.new = False

    repository.pending_restart = True
    assert repository.display_status == "pending-restart"
    repository.pending_restart = False

    repository.data.installed = True
    repository.data.installed_version = "1"
    repository.data.last_version = "2"
    repository.data.releases = True
    assert repository.display_status == "pending-upgrade"

    hacs.core.ha_version = AwesomeVersion("0.0.0")
    repository.repository_manifest.homeassistant = "1.0.0"
    assert repository.display_status == "pending-upgrade"

    repository.data.last_version = "1"
    assert repository.display_status == "installed"
