"""Create a dummy repository."""
# pylint: disable=missing-docstring
from integrationhelper import Logger
from homeassistant.core import HomeAssistant
from custom_components.hacs.repositories import HacsIntegration, HacsTheme, HacsPlugin
from custom_components.hacs.repositories.repository import HacsRepository


def dummy_repository_base(repository=None):
    if repository is None:
        repository = HacsRepository()
    repository.hass = HomeAssistant()
    repository.hass.data = {"custom_components": []}
    repository.logger = Logger("hacs.test.test")
    repository.information.name = "test"
    repository.information.full_name = "test/test"
    repository.information.default_branch = "master"
    repository.versions.available = "3"
    repository.status.selected_tag = "3"
    repository.manifest = {"config_flow": False, "domain": "test"}
    repository.releases.published_tags = ["1", "2", "3"]
    return repository


def dummy_repository_integration():
    repository = HacsIntegration("test/test")
    return dummy_repository_base(repository)


def dummy_repository_theme():
    repository = HacsTheme("test/test")
    return dummy_repository_base(repository)


def dummy_repository_plugin():
    repository = HacsPlugin("test/test")
    return dummy_repository_base(repository)
