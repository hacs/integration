"""Set up some common test helper things."""
import logging
import asyncio
import pytest
from homeassistant.exceptions import ServiceNotFound
from homeassistant.runner import HassEventLoopPolicy
from tests.common import (  # noqa: E402, isort:skip
    async_test_home_assistant,
    mock_storage as mock_storage,
    TOKEN,
    dummy_repository_base,
)
from tests.async_mock import MagicMock, Mock, patch
from custom_components.hacs.repositories import (
    HacsAppdaemon,
    HacsIntegration,
    HacsNetdaemon,
    HacsPlugin,
    HacsPythonScript,
    HacsTheme,
)

from custom_components.hacs.hacsbase.hacs import Hacs
from custom_components.hacs.hacsbase.configuration import Configuration

# Set default logger
logging.basicConfig(level=logging.DEBUG)

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

asyncio.set_event_loop_policy(HassEventLoopPolicy(False))
# Disable fixtures overriding our beautiful policy
asyncio.set_event_loop_policy = lambda policy: None


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

    yield hass_obj

    event_loop.run_until_complete(hass_obj.async_stop(force=True))
    for ex in exceptions:
        if isinstance(ex, ServiceNotFound):
            continue
        raise ex


@pytest.fixture
def hacs():
    """Fixture to provide a HACS object."""
    hacs_obj = Hacs()
    hacs_obj.hass = hass
    hacs_obj.configuration = Configuration()
    hacs_obj.configuration.token = TOKEN
    yield hacs_obj


@pytest.fixture
def repository(hass):
    """Fixtrue for HACS repository object"""
    yield dummy_repository_base(hass)


@pytest.fixture
def repository_integration(hass):
    """Fixtrue for HACS integration repository object"""
    repository_obj = HacsIntegration("test/test")
    yield dummy_repository_base(hass, repository_obj)


@pytest.fixture
def repository_theme(hass):
    """Fixtrue for HACS theme repository object"""
    repository_obj = HacsTheme("test/test")
    yield dummy_repository_base(hass, repository_obj)


@pytest.fixture
def repository_plugin(hass):
    """Fixtrue for HACS plugin repository object"""
    repository_obj = HacsPlugin("test/test")
    yield dummy_repository_base(hass, repository_obj)


@pytest.fixture
def repository_python_script(hass):
    """Fixtrue for HACS python_script repository object"""
    repository_obj = HacsPythonScript("test/test")
    yield dummy_repository_base(hass, repository_obj)


@pytest.fixture
def repository_appdaemon(hass):
    """Fixtrue for HACS appdaemon repository object"""
    repository_obj = HacsAppdaemon("test/test")
    yield dummy_repository_base(hass, repository_obj)


@pytest.fixture
def repository_netdaemon(hass):
    """Fixtrue for HACS netdaemon repository object"""
    repository_obj = HacsNetdaemon("test/test")
    yield dummy_repository_base(hass, repository_obj)
