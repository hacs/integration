"""Create a dummy repository."""
# pylint: disable=missing-docstring
import tempfile

from homeassistant.core import HomeAssistant

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.functions.version_to_install import (
    version_to_install,
)
from custom_components.hacs.repositories import (
    HacsAppdaemon,
    HacsIntegration,
    HacsNetdaemon,
    HacsPlugin,
    HacsPythonScript,
    HacsTheme,
)
from custom_components.hacs.helpers.classes.repository import HacsRepository
from tests.sample_data import repository_data


def dummy_repository_base(hass, repository=None):
    if repository is None:
        repository = HacsRepository()
    repository.hacs.hass = hass
    repository.hacs.system.config_path = tempfile.gettempdir()
    repository.logger = getLogger("test.test")
    repository.data.full_name = "test/test"
    repository.data.full_name_lower = "test/test"
    repository.data.domain = "test"
    repository.data.last_version = "3"
    repository.data.selected_tag = "3"
    repository.ref = version_to_install(repository)
    repository.integration_manifest = {"config_flow": False, "domain": "test"}
    repository.data.published_tags = ["1", "2", "3"]
    repository.data.update_data(repository_data)
    return repository


def dummy_repository_integration(hass):
    repository = HacsIntegration("test/test")
    return dummy_repository_base(hass, repository)


def dummy_repository_theme(hass):
    repository = HacsTheme("test/test")
    return dummy_repository_base(hass, repository)


def dummy_repository_plugin(hass):
    repository = HacsPlugin("test/test")
    return dummy_repository_base(hass, repository)


def dummy_repository_python_script(hass):
    repository = HacsPythonScript("test/test")
    return dummy_repository_base(hass, repository)


def dummy_repository_appdaemon(hass):
    repository = HacsAppdaemon("test/test")
    return dummy_repository_base(hass, repository)


def dummy_repository_netdaemon(hass):
    repository = HacsNetdaemon("test/test")
    return dummy_repository_base(hass, repository)
