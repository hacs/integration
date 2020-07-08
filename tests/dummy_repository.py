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


def dummy_repository_base(repository=None):
    if repository is None:
        repository = HacsRepository()
    repository.hacs.hass = HomeAssistant()
    repository.hacs.hass.data = {"custom_components": []}
    repository.hacs.system.config_path = tempfile.gettempdir()
    repository.logger = getLogger("test.test")
    repository.data.full_name = "test/test"
    repository.data.domain = "test"
    repository.data.last_version = "3"
    repository.data.selected_tag = "3"
    repository.ref = version_to_install(repository)
    repository.integration_manifest = {"config_flow": False, "domain": "test"}
    repository.data.published_tags = ["1", "2", "3"]
    repository.data.update_data(repository_data)
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


def dummy_repository_python_script():
    repository = HacsPythonScript("test/test")
    return dummy_repository_base(repository)


def dummy_repository_appdaemon():
    repository = HacsAppdaemon("test/test")
    return dummy_repository_base(repository)


def dummy_repository_netdaemon():
    repository = HacsNetdaemon("test/test")
    return dummy_repository_base(repository)
