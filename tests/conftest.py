"""Set up some common test helper things."""
import asyncio
import logging

import pytest
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.runner import HassEventLoopPolicy

from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.hacsbase.hacs import Hacs
from custom_components.hacs.helpers.classes.repository import HacsRepository
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
from custom_components.hacs.share import SHARE
from tests.async_mock import MagicMock

from tests.common import (  # noqa: E402, isort:skip
    async_test_home_assistant,
    fixture,
    mock_storage as mock_storage,
    TOKEN,
    dummy_repository_base,
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
    hass_obj = event_loop.run_until_complete(
        async_test_home_assistant(event_loop, tmpdir)
    )
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
def hacs(hass):
    """Fixture to provide a HACS object."""
    hacs_obj = Hacs()
    hacs_obj.hass = hass
    hacs_obj.session = async_create_clientsession(hass)
    hacs_obj.configuration = Configuration()
    hacs_obj.configuration.token = TOKEN
    hacs_obj.core.config_path = hass.config.path()
    hacs_obj.system.action = False
    SHARE["hacs"] = hacs_obj
    yield hacs_obj


@pytest.fixture
def repository(hacs):
    """Fixtrue for HACS repository object"""
    repository_obj = HacsRepository()
    repository_obj.hacs = hacs
    repository_obj.hass = hacs.hass
    repository_obj.hacs.core.config_path = hacs.hass.config.path()
    repository_obj.logger = logging.getLogger("test")
    repository_obj.data.full_name = "test/test"
    repository_obj.data.full_name_lower = "test/test"
    repository_obj.data.domain = "test"
    repository_obj.data.last_version = "3"
    repository_obj.data.selected_tag = "3"
    repository_obj.ref = version_to_install(repository_obj)
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
    repository_obj = HacsIntegration("test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_theme(hacs):
    """Fixtrue for HACS theme repository object"""
    repository_obj = HacsTheme("test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_plugin(hacs):
    """Fixtrue for HACS plugin repository object"""
    repository_obj = HacsPlugin("test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_python_script(hacs):
    """Fixtrue for HACS python_script repository object"""
    repository_obj = HacsPythonScript("test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_appdaemon(hacs):
    """Fixtrue for HACS appdaemon repository object"""
    repository_obj = HacsAppdaemon("test/test")
    yield dummy_repository_base(hacs, repository_obj)


@pytest.fixture
def repository_netdaemon(hacs):
    """Fixtrue for HACS netdaemon repository object"""
    repository_obj = HacsNetdaemon("test/test")
    yield dummy_repository_base(hacs, repository_obj)
