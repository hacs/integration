"""Set up some common test helper things."""
# pytest: disable=protected-access
import asyncio
import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock

from awesomeversion import AwesomeVersion
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.loader import Integration
from homeassistant.runner import HassEventLoopPolicy
import pytest

from custom_components.hacs.base import (
    HacsBase,
    HacsCommon,
    HacsCore,
    HacsRepositories,
    HacsSystem,
)
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.repositories import (
    HacsAppdaemonRepository,
    HacsIntegrationRepository,
    HacsNetdaemonRepository,
    HacsPluginRepository,
    HacsPythonScriptRepository,
    HacsThemeRepository,
)
from custom_components.hacs.repositories.base import HacsRepository
from custom_components.hacs.share import SHARE
from custom_components.hacs.tasks.manager import HacsTaskManager
from custom_components.hacs.utils.queue_manager import QueueManager
from custom_components.hacs.utils.version import version_to_download

from tests.async_mock import MagicMock
from tests.common import (
    TOKEN,
    async_test_home_assistant,
    dummy_repository_base,
    fixture,
    mock_storage as mock_storage,
)

# Set default logger
logging.basicConfig(level=logging.DEBUG)

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

asyncio.set_event_loop_policy(HassEventLoopPolicy(False))
# Disable fixtures overriding our beautiful policy
asyncio.set_event_loop_policy = lambda policy: None


@pytest.fixture()
def connection():
    """Mock fixture for connection."""
    yield MagicMock()


@pytest.fixture
def hass_storage():
    """Fixture to mock storage."""
    with mock_storage() as stored_data:
        yield stored_data


@pytest.fixture
def hass(event_loop, tmpdir):
    """Fixture to provide a test instance of Home Assistant."""

    def exc_handle(loop, context):
        """Handle exceptions by rethrowing them, which will fail the test."""
        exceptions.append(context["exception"])
        orig_exception_handler(loop, context)

    exceptions = []
    hass_obj = event_loop.run_until_complete(async_test_home_assistant(event_loop, tmpdir))
    orig_exception_handler = event_loop.get_exception_handler()
    event_loop.set_exception_handler(exc_handle)

    hass_obj.http = MagicMock()

    yield hass_obj

    event_loop.run_until_complete(hass_obj.async_stop(force=True))
    for ex in exceptions:
        if isinstance(ex, (ServiceNotFound, FileExistsError)):
            continue
        raise ex


@pytest.fixture
def hacs(hass: HomeAssistant):
    """Fixture to provide a HACS object."""
    hacs_obj = HacsBase()
    hacs_obj.hass = hass
    hacs_obj.tasks = HacsTaskManager(hacs=hacs_obj, hass=hass)
    hacs_obj.session = async_create_clientsession(hass)
    hacs_obj.repositories = HacsRepositories()

    hacs_obj.integration = Integration(
        hass=hass,
        pkg_path="custom_components.hacs",
        file_path=Path(hass.config.path("custom_components/hacs")),
        manifest={"domain": DOMAIN, "version": "0.0.0", "requirements": ["hacs_frontend==1"]},
    )
    hacs_obj.common = HacsCommon()
    hacs_obj.githubapi = AsyncMock()
    hacs_obj.data = AsyncMock()
    hacs_obj.queue = QueueManager()
    hacs_obj.core = HacsCore()
    hacs_obj.system = HacsSystem()

    hacs_obj.core.config_path = hass.config.path()
    hacs_obj.core.ha_version = AwesomeVersion(HAVERSION)
    hacs_obj.version = hacs_obj.integration.version
    hacs_obj.configuration.token = TOKEN

    if not "PYTEST" in os.environ and "GITHUB_ACTION" in os.environ:
        hacs_obj.system.action = True

    yield hacs_obj


@pytest.fixture
def repository(hacs):
    """Fixtrue for HACS repository object"""
    repository_obj = HacsRepository(hacs)
    repository_obj.hacs = hacs
    repository_obj.hass = hacs.hass
    repository_obj.hacs.core.config_path = hacs.hass.config.path()
    repository_obj.logger = logging.getLogger("test")
    repository_obj.data.full_name = "test/test"
    repository_obj.data.full_name_lower = "test/test"
    repository_obj.data.domain = "test"
    repository_obj.data.last_version = "3"
    repository_obj.data.selected_tag = "3"
    repository_obj.ref = version_to_download(repository_obj)
    repository_obj.integration_manifest = {"config_flow": False, "domain": "test"}
    repository_obj.data.published_tags = ["1", "2", "3"]
    repository_obj.data.update_data(fixture("repository_data.json"))

    async def update_repository():
        pass

    repository_obj.update_repository = update_repository
    yield repository_obj


@pytest.fixture
def repository_integration(hacs):
    """Fixtrue for HACS integration repository object"""
    repository_obj = HacsIntegrationRepository(hacs, "test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_theme(hacs):
    """Fixtrue for HACS theme repository object"""
    repository_obj = HacsThemeRepository(hacs, "test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_plugin(hacs):
    """Fixtrue for HACS plugin repository object"""
    repository_obj = HacsPluginRepository(hacs, "test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_python_script(hacs):
    """Fixtrue for HACS python_script repository object"""
    repository_obj = HacsPythonScriptRepository(hacs, "test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_appdaemon(hacs):
    """Fixtrue for HACS appdaemon repository object"""
    repository_obj = HacsAppdaemonRepository(hacs, "test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_netdaemon(hacs):
    """Fixtrue for HACS netdaemon repository object"""
    repository_obj = HacsNetdaemonRepository(hacs, "test/test")
    yield dummy_repository_base(hacs, repository_obj)
