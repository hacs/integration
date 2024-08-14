# pylint: disable=missing-docstring,invalid-name
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterable, Mapping, Sequence
from contextlib import asynccontextmanager, contextmanager, suppress
from contextvars import ContextVar
import functools as ft
from inspect import currentframe
import json as json_func
import os
from types import NoneType
from typing import Any, TypedDict, TypeVar
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientError, ClientSession, ClientWebSocketResponse
from aiohttp.typedefs import StrOrURL
from homeassistant import auth, bootstrap, config_entries, core as ha, loader
from homeassistant.auth import auth_store, models as auth_models
from homeassistant.const import EVENT_HOMEASSISTANT_CLOSE, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    category_registry as cr,
    device_registry as dr,
    entity,
    entity_registry as er,
    floor_registry as fr,
    issue_registry as ir,
    label_registry as lr,
    restore_state as rs,
    storage,
    translation,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.json import ExtendedJSONEncoder
import homeassistant.util.dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import homeassistant.util.uuid as uuid_util
import pytest
from yarl import URL

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.repositories.base import HacsManifest, HacsRepository
from custom_components.hacs.utils.logger import LOGGER

TOKEN = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
INSTANCES = []
REQUEST_CONTEXT: ContextVar[pytest.FixtureRequest] = ContextVar("request_context", default=None)

IGNORED_BASE_FILES = {
    "/config/automations.yaml",
    "/config/configuration.yaml",
    "/config/scenes.yaml",
    "/config/scripts.yaml",
    "/config/secrets.yaml",
}

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures")


class CategoryTestData(TypedDict):
    id: str
    repository: str
    category: str
    files: list[str]
    version_base: str
    version_update: str
    prerelease: str


_CATEGORY_TEST_DATA: tuple[CategoryTestData] = (
    CategoryTestData(
        id="1296265",
        category=HacsCategory.APPDAEMON,
        repository="hacs-test-org/appdaemon-basic",
        files=["__init__.py", "example.py"],
        version_base="1.0.0",
        version_update="2.0.0",
        prerelease="3.0.0",
    ),
    CategoryTestData(
        id="1296269",
        category=HacsCategory.INTEGRATION,
        repository="hacs-test-org/integration-basic",
        files=["__init__.py", "manifest.json", "module/__init__.py"],
        version_base="1.0.0",
        version_update="2.0.0",
        prerelease="3.0.0",
    ),
    CategoryTestData(
        id="1296267",
        category=HacsCategory.PLUGIN,
        repository="hacs-test-org/plugin-basic",
        files=["example.js", "example.js.gz"],
        version_base="1.0.0",
        version_update="2.0.0",
        prerelease="3.0.0",
    ),
    CategoryTestData(
        id="1296262",
        category=HacsCategory.PYTHON_SCRIPT,
        repository="hacs-test-org/python_script-basic",
        files=["example.py"],
        version_base="1.0.0",
        version_update="2.0.0",
        prerelease="3.0.0",
    ),
    CategoryTestData(
        id="1296268",
        category=HacsCategory.TEMPLATE,
        repository="hacs-test-org/template-basic",
        files=["example.jinja"],
        version_base="1.0.0",
        version_update="2.0.0",
        prerelease="3.0.0",
    ),
    CategoryTestData(
        id="1296266",
        category=HacsCategory.THEME,
        repository="hacs-test-org/theme-basic",
        files=["example.yaml"],
        version_base="1.0.0",
        version_update="2.0.0",
        prerelease="3.0.0",
    ),
)


def category_test_data_parametrized(
    *,
    xfail_categories: list[HacsCategory] | None = None,
    categories: Iterable[HacsCategory] = [entry["category"] for entry in _CATEGORY_TEST_DATA],
    **kwargs,
):
    return (
        pytest.param(
            entry,
            marks=[pytest.mark.xfail]
            if xfail_categories and entry["category"] in xfail_categories
            else [],
            id=entry["repository"],
        )
        for entry in _CATEGORY_TEST_DATA
        if entry["category"] in categories
    )


def current_function_name():
    """Return the name of the current function."""
    return currentframe().f_back.f_code.co_name


def safe_json_dumps(data: dict | list) -> str:
    return json_func.dumps(
        data,
        indent=4,
        sort_keys=True,
        cls=ExtendedJSONEncoder,
    )


def recursive_remove_key(data: dict[str, Any], to_remove: Iterable[str]) -> dict[str, Any]:
    def _sort_list(entry):
        if isinstance(entry, list):
            if len(entry) == 0:
                return entry
            if isinstance(entry[0], str):
                return sorted(entry)
            if isinstance(entry[0], list):
                return [_sort_list(item) for item in entry]
        return sorted(
            entry,
            key=lambda obj: (getattr(obj, "id", None) or getattr(obj, "name", None) or 0)
            if isinstance(obj, dict)
            else obj,
        )

    if not isinstance(data, (dict, set, list)):
        return data

    if isinstance(data, list):
        return [recursive_remove_key(item, to_remove) for item in _sort_list(data)]

    returndata = {}
    for key in sorted(data.keys()):
        value = data[key]
        if key in to_remove:
            continue
        elif isinstance(value, (str, bool, int, float, NoneType)):
            returndata[key] = value
        elif isinstance(value, dict):
            returndata[key] = recursive_remove_key(
                {k: value[k] for k in sorted(value.keys())},
                to_remove,
            )
        elif isinstance(value, (list, set)):
            returndata[key] = [recursive_remove_key(item, to_remove) for item in _sort_list(value)]
        else:
            returndata[key] = type(value)
    return returndata


def fixture(filename, asjson=True):
    """Load a fixture."""
    filename = f"{filename}.json" if "." not in filename else filename
    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        filename.lower().replace("/", "_"),
    )
    try:
        with open(path, encoding="utf-8") as fptr:
            if asjson:
                return json_func.loads(fptr.read())
            return fptr.read()
    except OSError as err:
        raise OSError(f"Missing fixture for {
                      path.split('fixtures/')[1]}") from err


def dummy_repository_base(hacs, repository=None):
    if repository is None:
        repository = HacsRepository(hacs)
        repository.data.full_name = "test/test"
        repository.data.full_name_lower = "test/test"
    repository.hacs = hacs
    repository.hacs.hass = hacs.hass
    repository.hacs.core.config_path = hacs.hass.config.path()
    repository.logger = LOGGER
    repository.data.domain = "test"
    repository.data.last_version = "3"
    repository.data.selected_tag = "3"
    repository.ref = repository.version_to_download()
    repository.integration_manifest = {"config_flow": False, "domain": "test"}
    repository.data.published_tags = ["1", "2", "3"]
    repository.data.update_data(fixture("repository_data.json", asjson=True))
    repository.hacs_manifest = HacsManifest.from_dict({})

    async def update_repository(*args, **kwargs):
        pass

    repository.update_repository = update_repository
    return repository


def get_test_config_dir(*add_path):
    """Return a path to a test config dir."""
    return os.path.join(os.path.dirname(__file__), "testing_config", *add_path)


_T = TypeVar("_T", bound=Mapping[str, Any] | Sequence[Any])


class StoreWithoutWriteLoad(storage.Store[_T]):
    """Fake store that does not write or load. Used for testing."""

    async def async_save(self, *args: Any, **kwargs: Any) -> None:
        """Save the data.

        This function is mocked out in tests.
        """

    @callback
    def async_save_delay(self, *args: Any, **kwargs: Any) -> None:
        """Save data with an optional delay.

        This function is mocked out in tests.
        """


# pylint: disable=protected-access
@asynccontextmanager
async def async_test_home_assistant_min_version(
    event_loop: asyncio.AbstractEventLoop | None = None,
    load_registries: bool = True,
    config_dir: str | None = None,
) -> AsyncGenerator[HomeAssistant]:
    """Return a Home Assistant object pointing at test config dir.

    This should be copied from the minimum supported version,
    currently Home Assistant Core 2024.4.1.
    """
    hass = HomeAssistant(config_dir or get_test_config_dir())
    store = auth_store.AuthStore(hass)
    hass.auth = auth.AuthManager(hass, store, {}, {})
    ensure_auth_manager_loaded(hass.auth)
    INSTANCES.append(hass)

    orig_async_add_job = hass.async_add_job
    orig_async_add_executor_job = hass.async_add_executor_job
    orig_async_create_task = hass.async_create_task
    orig_tz = dt_util.DEFAULT_TIME_ZONE

    def async_add_job(target, *args, eager_start: bool = False):
        """Add job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock) and not isinstance(target, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_job(target, *args, eager_start=eager_start)

    def async_add_executor_job(target, *args):
        """Add executor job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_executor_job(target, *args)

    def async_create_task(coroutine, name=None, eager_start=False):
        """Create task."""
        if isinstance(coroutine, Mock) and not isinstance(coroutine, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(None)
            return fut

        return orig_async_create_task(coroutine, name, eager_start)

    hass.async_add_job = async_add_job
    hass.async_add_executor_job = async_add_executor_job
    hass.async_create_task = async_create_task

    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {}

    hass.config.location_name = "test home"
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    hass.config.set_time_zone("US/Pacific")
    hass.config.units = METRIC_SYSTEM
    hass.config.media_dirs = {"local": get_test_config_dir("media")}
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    hass.config_entries = config_entries.ConfigEntries(
        hass,
        {"_": ("Not empty or else some bad checks for hass config in discovery.py breaks")},
    )
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        hass.config_entries._async_shutdown,
        run_immediately=True,
    )

    # Load the registries
    entity.async_setup(hass)
    loader.async_setup(hass)

    # setup translation cache instead of calling translation.async_setup(hass)
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(hass)
    if load_registries:
        with (
            patch.object(StoreWithoutWriteLoad, "async_load", return_value=None),
            patch(
                "homeassistant.helpers.area_registry.AreaRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.device_registry.DeviceRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.entity_registry.EntityRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.storage.Store",  # Floor & label registry are different
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.issue_registry.IssueRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.restore_state.RestoreStateData.async_setup_dump",
                return_value=None,
            ),
            patch(
                "homeassistant.helpers.restore_state.start.async_at_start",
            ),
        ):
            await ar.async_load(hass)
            await cr.async_load(hass)
            await dr.async_load(hass)
            await er.async_load(hass)
            await fr.async_load(hass)
            await ir.async_load(hass)
            await lr.async_load(hass)
            await rs.async_load(hass)
        hass.data[bootstrap.DATA_REGISTRIES_LOADED] = None

    hass.set_state(CoreState.running)

    @callback
    def clear_instance(event):
        """Clear global instance."""
        INSTANCES.remove(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_CLOSE, clear_instance)

    yield hass

    # Restore timezone, it is set when creating the hass object
    dt_util.DEFAULT_TIME_ZONE = orig_tz


@asynccontextmanager
async def async_test_home_assistant_dev(
    event_loop: asyncio.AbstractEventLoop | None = None,
    load_registries: bool = True,
    config_dir: str | None = None,
) -> AsyncGenerator[HomeAssistant]:
    """Return a Home Assistant object pointing at test config dir.

    This should be copied from latest Home Assistant version,
    currently Home Assistant Core 2024.9.0dev0 (2024-08-14).
    https://github.com/home-assistant/core/blob/dev/tests/common.py
    """
    hass = HomeAssistant(config_dir or get_test_config_dir())
    store = auth_store.AuthStore(hass)
    hass.auth = auth.AuthManager(hass, store, {}, {})
    ensure_auth_manager_loaded(hass.auth)
    INSTANCES.append(hass)

    orig_async_add_job = hass.async_add_job
    orig_async_add_executor_job = hass.async_add_executor_job
    orig_async_create_task_internal = hass.async_create_task_internal
    orig_tz = dt_util.get_default_time_zone()

    def async_add_job(target, *args, eager_start: bool = False):
        """Add job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock) and not isinstance(target, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_job(target, *args, eager_start=eager_start)

    def async_add_executor_job(target, *args):
        """Add executor job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_executor_job(target, *args)

    def async_create_task_internal(coroutine, name=None, eager_start=True):
        """Create task."""
        if isinstance(coroutine, Mock) and not isinstance(coroutine, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(None)
            return fut

        return orig_async_create_task_internal(coroutine, name, eager_start)

    hass.async_add_job = async_add_job
    hass.async_add_executor_job = async_add_executor_job
    hass.async_create_task_internal = async_create_task_internal

    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {}

    hass.config.location_name = "test home"
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    await hass.config.async_set_time_zone("US/Pacific")
    hass.config.units = METRIC_SYSTEM
    hass.config.media_dirs = {"local": get_test_config_dir("media")}
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    hass.config_entries = config_entries.ConfigEntries(
        hass,
        {
            "_": (
                "Not empty or else some bad checks for hass config in discovery.py"
                " breaks"
            )
        },
    )
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        hass.config_entries._async_shutdown,
    )

    # Load the registries
    entity.async_setup(hass)
    loader.async_setup(hass)

    # setup translation cache instead of calling translation.async_setup(hass)
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(
        hass
    )
    if load_registries:
        with (
            patch.object(StoreWithoutWriteLoad,
                         "async_load", return_value=None),
            patch(
                "homeassistant.helpers.area_registry.AreaRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.device_registry.DeviceRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.entity_registry.EntityRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.storage.Store",  # Floor & label registry are different
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.issue_registry.IssueRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.restore_state.RestoreStateData.async_setup_dump",
                return_value=None,
            ),
            patch(
                "homeassistant.helpers.restore_state.start.async_at_start",
            ),
        ):
            await ar.async_load(hass)
            await cr.async_load(hass)
            await dr.async_load(hass)
            await er.async_load(hass)
            await fr.async_load(hass)
            await ir.async_load(hass)
            await lr.async_load(hass)
            await rs.async_load(hass)
        hass.data[bootstrap.DATA_REGISTRIES_LOADED] = None

    hass.set_state(CoreState.running)

    @callback
    def clear_instance(event):
        """Clear global instance."""
        # Give aiohttp one loop iteration to close
        hass.loop.call_soon(INSTANCES.remove, hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_CLOSE, clear_instance)

    try:
        yield hass
    finally:
        # Restore timezone, it is set when creating the hass object
        dt_util.set_default_time_zone(orig_tz)
        # Remove loop shutdown indicator to not interfere with additional hass objects
        with suppress(AttributeError):
            delattr(hass.loop, "_shutdown_run_callback_threadsafe")


@ha.callback
def ensure_auth_manager_loaded(auth_mgr):
    """Ensure an auth manager is considered loaded."""
    store = auth_mgr._store
    if store._users is None:
        store._set_defaults()


@contextmanager
def mock_storage(data=None):
    """Mock storage.
    Data is a dict {'key': {'version': version, 'data': data}}
    Written data will be converted to JSON to ensure JSON parsing works.
    """
    if data is None:
        data = {}

    orig_load = storage.Store._async_load

    async def mock_async_load(store):
        """Mock version of load."""
        if store._data is None:
            # No data to load
            if store.key not in data:
                return None

            mock_data = data.get(store.key)

            if "data" not in mock_data or "version" not in mock_data:
                raise ValueError('Mock data needs "version" and "data"')

            store._data = mock_data

        # Route through original load so that we trigger migration
        loaded = await orig_load(store)
        return loaded

    def mock_write_data(store, path, data_to_write):
        """Mock version of write data."""
        # To ensure that the data can be serialized
        data[store.key] = json_func.loads(json_func.dumps(data_to_write, cls=store._encoder))

    async def mock_remove(store):
        """Remove data."""
        data.pop(store.key, None)

    with (
        patch(
            "homeassistant.helpers.storage.Store._async_load",
            side_effect=mock_async_load,
            autospec=True,
        ),
        patch(
            "homeassistant.helpers.storage.Store._write_data",
            side_effect=mock_write_data,
            autospec=True,
        ),
        patch(
            "homeassistant.helpers.storage.Store.async_remove",
            side_effect=mock_remove,
            autospec=True,
        ),
    ):
        yield data


class MockOwner(auth_models.User):
    """Mock a user in Home Assistant."""

    def __init__(self):
        """Initialize mock user."""
        super().__init__(
            **{
                "is_owner": True,
                "is_active": True,
                "name": "Mocked Owner User",
                "system_generated": False,
                "groups": [],
                "perm_lookup": None,
            },
        )

    @staticmethod
    def create(hass: ha.HomeAssistant):
        """Create a mock user."""
        user = MockOwner()
        ensure_auth_manager_loaded(hass.auth)
        hass.auth._store._users[user.id] = user
        return user


class MockConfigEntry(config_entries.ConfigEntry):
    entry_id = uuid_util.random_uuid_hex()

    def add_to_hass(self, hass: ha.HomeAssistant) -> None:
        """Test helper to add entry to hass."""
        hass.config_entries._entries[self.entry_id] = self


class WSClient:
    """WS Client to be used in testing."""

    client: ClientWebSocketResponse | None = None

    def __init__(self, hass: ha.HomeAssistant, token: str) -> None:
        self.hass = hass
        self.token = token
        self.id = 0

    async def _create_client(self) -> None:
        if self.client is not None:
            return

        clientsession = async_get_clientsession(self.hass)

        async def _async_close_websession(event: ha.Event) -> None:
            """Close websession."""
            await self.send_json("close", {})
            await self.client.close()

            clientsession.detach()

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_close_websession)

        self.client = await clientsession.ws_connect(
            "ws://localhost:8123/api/websocket",
            timeout=1,
            autoclose=True,
        )
        auth_response = await self.client.receive_json()
        assert auth_response["type"] == "auth_required"
        await self.client.send_json({"type": "auth", "access_token": self.token})

        auth_response = await self.client.receive_json()
        assert auth_response["type"] == "auth_ok"

    async def send_json(self, type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.id += 1
        await self._create_client()
        await self.client.send_json({"id": self.id, "type": type, **payload})

    async def receive_json(self) -> dict[str, Any]:
        return await self.client.receive_json()

    async def send_and_receive_json(self, type: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self.send_json(type=type, payload=payload)
        return await self.client.receive_json()


class MockedResponse:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.exception = kwargs.get("exception", None)
        self.keep = kwargs.get("keep", False)

    @property
    def status(self):
        return self.kwargs.get("status", 200)

    @property
    def url(self):
        return self.kwargs.get("url", "http://127.0.0.1")

    @property
    def headers(self):
        return self.kwargs.get("headers", {})

    async def read(self, **kwargs):
        if (content := self.kwargs.get("content")) is not None:
            return content
        return await self.kwargs.get("read", AsyncMock())()

    async def json(self, **kwargs):
        if (content := self.kwargs.get("content")) is not None:
            return content
        return await self.kwargs.get("json", AsyncMock())()

    async def text(self, **kwargs):
        if (content := self.kwargs.get("content")) is not None:
            return content
        return await self.kwargs.get("text", AsyncMock())()

    def raise_for_status(self) -> None:
        if self.status >= 300:
            raise ClientError(self.status)


class ResponseMocker:
    calls: list[dict[str, Any]] = []
    responses: dict[str, MockedResponse] = {}

    def add(self, url: str, response: MockedResponse) -> None:
        self.responses[url] = response

    def get(self, url: str, *args, **kwargs) -> MockedResponse:
        data = {"url": url, "args": list(args), "kwargs": kwargs}
        if (request := REQUEST_CONTEXT.get()) is not None:
            data["_test_caller"] = f"{
                request.node.location[0]}::{request.node.name}"
            data["_uses_setup_integration"] = request.node.name != "test_integration_setup" and (
                "setup_integration" in request.fixturenames or "hacs" in request.fixturenames
            )
        self.calls.append(data)
        response = self.responses.get(url, None)
        if response is not None and response.keep:
            return response
        return self.responses.pop(url, None)


class ProxyClientSession(ClientSession):
    response_mocker = ResponseMocker()

    async def _request(self, method: str, str_or_url: StrOrURL, *args, **kwargs):
        if str_or_url.startswith("ws://"):
            return await super()._request(method, str_or_url, *args, **kwargs)

        if (resp := self.response_mocker.get(str_or_url, args, kwargs)) is not None:
            LOGGER.info("Using mocked response for %s", str_or_url)
            if resp.exception:
                raise resp.exception
            return resp

        url = URL(str_or_url)
        fixture_file = f"fixtures/proxy/{url.host}{url.path}{'.json' if url.host in (
            'api.github.com', 'data-v2.hacs.xyz') and not url.path.endswith('.json') else ''}"
        fp = os.path.join(
            os.path.dirname(__file__),
            fixture_file,
        )

        LOGGER.info("Using mocked response from %s", fixture_file)

        if not os.path.exists(fp):
            raise Exception(f"Missing fixture for proxy/{url.host}{url.path}")

        async def read(**kwargs):
            if url.path.endswith(".zip"):
                with open(fp, mode="rb") as fptr:
                    return fptr.read()
            with open(fp, encoding="utf-8") as fptr:
                return fptr.read().encode("utf-8")

        async def json(**kwargs):
            with open(fp, encoding="utf-8") as fptr:
                return json_func.loads(fptr.read())

        return MockedResponse(
            url=url,
            read=read,
            json=json,
            headers={
                "X-RateLimit-Limit": "999",
                "X-RateLimit-Remaining": "999",
                "X-RateLimit-Reset": "999",
                "Content-Type": "application/json",
                "Etag": "321",
            },
        )


async def client_session_proxy(hass: ha.HomeAssistant) -> ClientSession:
    """Create a mocked client session."""
    base = async_get_clientsession(hass)
    base_request = base._request
    response_mocker = ResponseMocker()

    async def _request(method: str, str_or_url: StrOrURL, *args, **kwargs):
        if str_or_url.startswith("ws://"):
            return await base_request(method, str_or_url, *args, **kwargs)

        if (resp := response_mocker.get(str_or_url, args, kwargs)) is not None:
            LOGGER.info("Using mocked response for %s", str_or_url)
            if resp.exception:
                raise resp.exception
            return resp

        url = URL(str_or_url)
        fixture_file = f"fixtures/proxy/{url.host}{url.path}{'.json' if url.host in (
            'api.github.com', 'data-v2.hacs.xyz') and not url.path.endswith('.json') else ''}"
        fp = os.path.join(
            os.path.dirname(__file__),
            fixture_file,
        )

        if not os.path.exists(fp):
            raise Exception(f"Missing fixture for proxy/{url.host}{url.path}")

        async def read(**kwargs):
            if url.path.endswith(".zip"):
                with open(fp, mode="rb") as fptr:
                    return fptr.read()
            with open(fp, encoding="utf-8") as fptr:
                return fptr.read().encode("utf-8")

        async def json(**kwargs):
            with open(fp, encoding="utf-8") as fptr:
                return json_func.loads(fptr.read())

        return MockedResponse(
            url=url,
            read=read,
            json=json,
            headers={
                "X-RateLimit-Limit": "999",
                "X-RateLimit-Remaining": "999",
                "X-RateLimit-Reset": "999",
                "Content-Type": "application/json",
            },
        )

    base._request = _request

    return base


def create_config_entry(
    data: dict[str, Any] = None,
    options: dict[str, Any] = None,
) -> MockConfigEntry:
    return MockConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="",
        data={"token": TOKEN, **(data or {})},
        source="user",
        options={**(options or {})},
        unique_id="12345",
    )


async def setup_integration(hass: ha.HomeAssistant, config_entry: MockConfigEntry) -> None:
    mock_session = await client_session_proxy(hass)
    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=mock_session,
    ):
        hass.data.pop("custom_components", None)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    hacs: HacsBase = hass.data.get(DOMAIN)
    for repository in hacs.repositories.list_all:
        if repository.data.full_name != "hacs/integration":
            repository.data.installed = False
            repository.data.installed_version = None
            repository.data.installed_commit = None
    assert not hacs.system.disabled


def get_hacs(hass: ha.HomeAssistant) -> HacsBase:
    return hass.data[DOMAIN]
