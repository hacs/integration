"""Set up some common test helper things."""
# pytest: disable=protected-access
import asyncio
from dataclasses import asdict
from glob import iglob
import json
import logging
import os
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

from aiogithubapi import GitHub, GitHubAPI
from aiogithubapi.const import ACCEPT_HEADERS
from awesomeversion import AwesomeVersion
from homeassistant.auth.models import Credentials
from homeassistant.auth.providers.homeassistant import HassAuthProvider
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import Integration
from homeassistant.runner import HassEventLoopPolicy
import pytest
import pytest_asyncio
from pytest_snapshot.plugin import Snapshot

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
    HacsTemplateRepository,
    HacsThemeRepository,
)
from custom_components.hacs.utils.queue_manager import QueueManager
from custom_components.hacs.utils.store import async_load_from_store
from custom_components.hacs.validate.manager import ValidationManager

from tests.common import (
    REQUEST_CONTEXT,
    TOKEN,
    MockOwner,
    ResponseMocker,
    WSClient,
    async_test_home_assistant,
    client_session_proxy,
    create_config_entry,
    dummy_repository_base,
    mock_storage as mock_storage,
    recursive_remove_key,
    safe_json_dumps,
    setup_integration as common_setup_integration,
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


@pytest.fixture(autouse=True)
def set_request_context(request: pytest.FixtureRequest):
    """Set request context for every test."""
    REQUEST_CONTEXT.set(request)


@pytest.fixture()
def connection():
    """Mock fixture for connection."""
    yield MagicMock()


@pytest.fixture
def hass_storage():
    """Fixture to mock storage."""
    with mock_storage() as stored_data:
        yield stored_data


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def hass(event_loop, tmpdir):
    """Fixture to provide a test instance of Home Assistant."""

    def exc_handle(loop, context):
        """Handle exceptions by rethrowing them, which will fail the test."""
        if exception := context.get("exception"):
            exceptions.append(exception)
        orig_exception_handler(loop, context)

    exceptions: list[Exception] = []
    hass_obj = event_loop.run_until_complete(async_test_home_assistant(event_loop, tmpdir))
    orig_exception_handler = event_loop.get_exception_handler()
    event_loop.set_exception_handler(exc_handle)

    yield hass_obj

    event_loop.run_until_complete(hass_obj.async_stop(force=True))
    for ex in exceptions:
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
def repository_template(hacs):
    """Fixtrue for HACS template repository object"""
    repository_obj = HacsTemplateRepository(hacs, "test/test")
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


class SnapshotFixture(Snapshot):
    async def assert_hacs_data(
        self,
        hacs: HacsBase,
        filename: str,
        additional: dict[str, Any] | None = None,
    ):
        pass


@pytest.fixture
def snapshots(snapshot: Snapshot) -> SnapshotFixture:
    """Fixture for a snapshot."""
    snapshot.snapshot_dir = "tests/snapshots"

    async def assert_hacs_data(
        hacs: HacsBase,
        filename: str,
        additional: dict[str, Any] | None = None,
    ):
        await hacs.data.async_force_write()
        downloaded = [
            f.replace(f"{hacs.core.config_path}", "/config")
            for f in iglob(f"{hacs.core.config_path}/**", recursive=True)
            if os.path.isfile(f)
        ]
        data = {}
        stored_data = await async_load_from_store(hacs.hass, "data")
        for key, value in stored_data["repositories"].items():
            data[key] = {}
            for entry in value:
                data[key][entry["id"]] = entry
        snapshot.assert_match(
            safe_json_dumps(
                recursive_remove_key(
                    {
                        "directory": sorted(downloaded),
                        "data": data,
                        "hacs": {
                            "system": asdict(hacs.system),
                            "status": asdict(hacs.status),
                            "stage": hacs.stage,
                            "configuration": {
                                "experimental": hacs.configuration.experimental,
                                "debug": hacs.configuration.debug,
                                "dev": hacs.configuration.dev,
                            },
                        },
                        **(additional or {}),
                    },
                    ("last_fetched"),
                )
            ),
            filename,
        )

    snapshot.assert_hacs_data = assert_hacs_data
    return snapshot


@pytest_asyncio.fixture
async def proxy_session(hass: HomeAssistant) -> Generator:
    """Fixture for a proxy_session."""
    mock_session = await client_session_proxy(hass)
    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession", return_value=mock_session
    ):
        yield


@pytest_asyncio.fixture
async def ws_client(hass: HomeAssistant) -> WSClient:
    """Owner authenticated Websocket client fixture."""
    auth_provider = HassAuthProvider(hass, hass.auth._store, {"type": "homeassistant"})
    hass.auth._providers[(auth_provider.type, auth_provider.id)] = auth_provider
    owner = MockOwner.create(hass)

    credentials = Credentials(
        auth_provider_type=auth_provider.type,
        auth_provider_id=auth_provider.id,
        data={"username": "testadmin"},
    )

    await auth_provider.async_initialize()
    await hass.auth.async_link_user(owner, credentials)
    refresh_token = await hass.auth.async_create_refresh_token(
        owner, "https://hacs.xyz/testing", credential=credentials
    )

    return WSClient(hass, hass.auth.async_create_access_token(refresh_token))


@pytest.fixture()
def response_mocker(proxy_session: Generator) -> ResponseMocker:
    """Mock fixture for responses."""
    assert proxy_session is None
    yield ResponseMocker()


@pytest_asyncio.fixture
async def setup_integration(hass: HomeAssistant) -> None:
    await common_setup_integration(hass, create_config_entry(options={"experimental": True}))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
    response_mocker = ResponseMocker()
    calls = {}
    if session.config.args[0] != "tests" or exitstatus != 0:
        return

    for call in response_mocker.calls:
        if (_test_caller := call.get("_test_caller")) is None:
            continue
        if _test_caller not in calls:
            calls[_test_caller] = {}
        if (url := call.get("url")) not in calls[_test_caller]:
            calls[_test_caller][url] = 0
        calls[_test_caller][url] += 1

    if session.config.option.snapshot_update:
        with open("tests/output/proxy_calls.json", mode="w", encoding="utf-8") as file:
            file.write(safe_json_dumps(calls))

    with open("tests/output/proxy_calls.json", encoding="utf-8") as file:
        current = json.load(file)
        assert current == calls
