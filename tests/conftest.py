"""Set up some common test helper things."""
# pytest: disable=protected-access
import asyncio
import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock

from aiogithubapi import GitHub, GitHubAPI
from aiogithubapi.const import ACCEPT_HEADERS
from awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import Integration
from homeassistant.runner import HassEventLoopPolicy
import pytest
import pytest_asyncio

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
from custom_components.hacs.utils.configuration_schema import TOKEN as CONF_TOKEN
from custom_components.hacs.utils.queue_manager import QueueManager
from custom_components.hacs.validate.manager import ValidationManager

from tests.async_mock import MagicMock
from tests.common import (
    TOKEN,
    async_test_home_assistant,
    dummy_repository_base,
    mock_storage as mock_storage,
)

# Set default logger
logging.basicConfig(level=logging.DEBUG)
if "GITHUB_ACTION" in os.environ:
    logging.basicConfig(
        format="::%(levelname)s:: %(message)s",
        level=logging.DEBUG,
    )

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

asyncio.set_event_loop_policy(HassEventLoopPolicy(False))
# Disable fixtures overriding our beautiful policy
asyncio.set_event_loop_policy = lambda policy: None

# Disable sleep in tests
_sleep = asyncio.sleep
asyncio.sleep = lambda _: _sleep(0)


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
        if exception := context.get("exception"):
            exceptions.append(exception)
        orig_exception_handler(loop, context)

    exceptions = []
    hass_obj = event_loop.run_until_complete(async_test_home_assistant(event_loop, tmpdir))
    orig_exception_handler = event_loop.get_exception_handler()
    event_loop.set_exception_handler(exc_handle)

    yield hass_obj

    event_loop.run_until_complete(hass_obj.async_stop(force=True))
    for ex in exceptions:
        if isinstance(ex, (ServiceNotFound, FileExistsError)):
            continue
        raise ex


@pytest_asyncio.fixture
async def hacs(hass: HomeAssistant):
    """Fixture to provide a HACS object."""
    hacs_obj = HacsBase()
    hacs_obj.hass = hass
    hacs_obj.validation = ValidationManager(hacs=hacs_obj, hass=hass)
    hacs_obj.session = async_get_clientsession(hass)
    hacs_obj.repositories = HacsRepositories()

    hacs_obj.integration = Integration(
        hass=hass,
        pkg_path="custom_components.hacs",
        file_path=Path(hass.config.path("custom_components/hacs")),
        manifest={"domain": DOMAIN, "version": "0.0.0", "requirements": ["hacs_frontend==1"]},
    )
    hacs_obj.common = HacsCommon()
    hacs_obj.data = AsyncMock()
    hacs_obj.queue = QueueManager(hass=hass)
    hacs_obj.core = HacsCore()
    hacs_obj.system = HacsSystem()

    hacs_obj.core.config_path = hass.config.path()
    hacs_obj.core.ha_version = AwesomeVersion(HAVERSION)
    hacs_obj.version = hacs_obj.integration.version
    hacs_obj.configuration.token = TOKEN

    ## Old GitHub client
    hacs_obj.github = GitHub(
        token=hacs_obj.configuration.token,
        session=hacs_obj.session,
        headers={
            "User-Agent": "HACS/pytest",
            "Accept": ACCEPT_HEADERS["preview"],
        },
    )

    ## New GitHub client
    hacs_obj.githubapi = GitHubAPI(
        token=hacs_obj.configuration.token,
        session=hacs_obj.session,
        **{"client_name": "HACS/pytest"},
    )

    hacs_obj.queue.clear()

    hass.data[DOMAIN] = hacs_obj

    yield hacs_obj


@pytest.fixture
def repository(hacs):
    """Fixtrue for HACS repository object"""
    yield dummy_repository_base(hacs)


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


@pytest.fixture
def config_entry() -> ConfigEntry:
    """Fixture for a config entry."""
    yield ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="",
        data={CONF_TOKEN: TOKEN},
        source="user",
        options={},
        unique_id="12345",
    )
