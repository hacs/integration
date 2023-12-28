# pylint: disable=missing-docstring,invalid-name
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
import functools as ft
import json as json_func
import os
from typing import Any, Iterable, Mapping
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.typedefs import StrOrURL
from awesomeversion import AwesomeVersion
from homeassistant import (
    auth,
    bootstrap,
    config as ha_config,
    config_entries,
    core as ha,
)
from homeassistant.auth import auth_store, models as auth_models
from homeassistant.const import (
    EVENT_HOMEASSISTANT_CLOSE,
    EVENT_HOMEASSISTANT_STOP,
    __version__ as HAVERSION,
)
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity,
    entity_registry as er,
    issue_registry as ir,
    restore_state as rs,
    storage,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.json import ExtendedJSONEncoder
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as date_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import homeassistant.util.uuid as uuid_util
import pytest
from yarl import URL

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.repositories.base import HacsManifest, HacsRepository
from custom_components.hacs.utils.configuration_schema import TOKEN as CONF_TOKEN
from custom_components.hacs.utils.logger import LOGGER

_LOGGER = LOGGER
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


def safe_json_dumps(data: dict | list) -> str:
    return json_func.dumps(
        data,
        indent=4,
        sort_keys=True,
        cls=ExtendedJSONEncoder,
    )


def recursive_remove_key(data: dict[str, Any], to_remove: Iterable[str]) -> dict[str, Any]:
    if not isinstance(data, (Mapping, list)):
        return data

    if isinstance(data, list):
        return [
            recursive_remove_key(val, to_remove)
            for val in sorted(data, key=lambda obj: getattr(obj, "id", 0))
        ]

    copy_data = {**data}
    for key, value in copy_data.items():
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        if key in to_remove:
            copy_data[key] = None
        elif isinstance(value, Mapping):
            copy_data[key] = recursive_remove_key(value, to_remove)
        elif isinstance(value, list):
            copy_data[key] = [
                recursive_remove_key(item, to_remove)
                for item in sorted(value, key=lambda obj: getattr(obj, "id", 0))
            ]
    return copy_data


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
            _LOGGER.debug("Loading fixture from %s", path)
            if asjson:
                return json_func.loads(fptr.read())
            return fptr.read()
    except OSError as err:
        raise OSError(f"Missing fixture for {path.split('fixtures/')[1]}") from err


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


# pylint: disable=protected-access
async def async_test_home_assistant(loop, tmpdir):
    """Return a Home Assistant object pointing at test config dir."""
    try:
        hass = ha.HomeAssistant()  # pylint: disable=no-value-for-parameter
    except TypeError:
        hass = ha.HomeAssistant(tmpdir)  # pylint: disable=too-many-function-args
    store = auth_store.AuthStore(hass)
    hass.auth = auth.AuthManager(hass, store, {}, {})
    ensure_auth_manager_loaded(hass.auth)
    INSTANCES.append(hass)

    orig_async_add_job = hass.async_add_job
    orig_async_add_executor_job = hass.async_add_executor_job
    orig_async_create_task = hass.async_create_task

    def async_add_job(target, *args):
        """Add job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock) and not isinstance(target, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_job(target, *args)

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

    def async_create_task(coroutine, *args, **kwargs):
        """Create task."""
        if isinstance(coroutine, Mock) and not isinstance(coroutine, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(None)
            return fut

        return orig_async_create_task(coroutine, *args, **kwargs)

    hass.async_add_job = async_add_job
    hass.async_add_executor_job = async_add_executor_job
    hass.async_create_task = async_create_task

    hass.config.location_name = "test home"
    hass.config.config_dir = str(tmpdir)
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    hass.config.time_zone = date_util.get_time_zone("US/Pacific")
    hass.config.units = METRIC_SYSTEM
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []
    hass.data = {"integrations": {}, "custom_components": {}, "components": {}}

    entity.async_setup(hass)
    await asyncio.gather(
        ar.async_load(hass),
        dr.async_load(hass),
        er.async_load(hass),
        ir.async_load(hass),
        rs.async_load(hass),
    )
    hass.data[bootstrap.DATA_REGISTRIES_LOADED] = None

    hass.config_entries = config_entries.ConfigEntries(hass, {})
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, hass.config_entries._async_shutdown)

    hass.state = ha.CoreState.running
    await async_setup_component(hass, "homeassistant", {})
    with patch("homeassistant.components.python_script.setup", return_value=True):
        assert await async_setup_component(hass, "python_script", {})

    async def clear_instance(event):
        """Clear global instance."""
        if hass.http and hass.http.runner and hass.http.runner.sites:
            await hass.http.stop()
        INSTANCES.remove(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_CLOSE, clear_instance)
    await ha_config.async_ensure_config_exists(hass)

    return hass


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
                _LOGGER.error('Mock data needs "version" and "data"')
                raise ValueError('Mock data needs "version" and "data"')

            store._data = mock_data

        # Route through original load so that we trigger migration
        loaded = await orig_load(store)
        _LOGGER.info("Loading data for %s: %s", store.key, loaded)
        return loaded

    def mock_write_data(store, path, data_to_write):
        """Mock version of write data."""
        _LOGGER.info("Writing data to %s: %s", store.key, data_to_write)
        # To ensure that the data can be serialized
        data[store.key] = json_func.loads(json_func.dumps(data_to_write, cls=store._encoder))

    async def mock_remove(store):
        """Remove data."""
        data.pop(store.key, None)

    with patch(
        "homeassistant.helpers.storage.Store._async_load",
        side_effect=mock_async_load,
        autospec=True,
    ), patch(
        "homeassistant.helpers.storage.Store._write_data",
        side_effect=mock_write_data,
        autospec=True,
    ), patch(
        "homeassistant.helpers.storage.Store.async_remove",
        side_effect=mock_remove,
        autospec=True,
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
            }
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

        if AwesomeVersion(HAVERSION) >= "2023.10.0":
            hass.config_entries._domain_index.setdefault(self.domain, []).append(self)
        else:
            hass.config_entries._domain_index.setdefault(self.domain, []).append(self.entry_id)


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
            "ws://localhost:8123/api/websocket", timeout=1, autoclose=True
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

    def raise_for_status(self):
        return self.kwargs.get("raise_for_status")


class ResponseMocker:
    calls: list[dict[str, Any]] = []
    responses: dict[str, MockedResponse] = {}

    def add(self, url: str, response: MockedResponse) -> None:
        self.responses[url] = response

    def get(self, url: str, *args, **kwargs) -> MockedResponse:
        data = {"url": url, "args": list(args), "kwargs": kwargs}
        if (request := REQUEST_CONTEXT.get()) is not None:
            data["_test_caller"] = request.node.name
            data["_uses_setup_integration"] = request.node.name != "test_integration_setup" and (
                "setup_integration" in request.fixturenames or "hacs" in request.fixturenames
            )
        self.calls.append(data)
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
        fixture_file = f"fixtures/proxy/{url.host}{url.path}{'.json' if url.host in ('api.github.com', 'data-v2.hacs.xyz') and not url.path.endswith('.json') else ''}"
        fp = os.path.join(
            os.path.dirname(__file__),
            fixture_file,
        )

        print(f"Using fixture {fp} for request to {url.host}")

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
        fixture_file = f"fixtures/proxy/{url.host}{url.path}{'.json' if url.host in ('api.github.com', 'data-v2.hacs.xyz') and not url.path.endswith('.json') else ''}"
        fp = os.path.join(
            os.path.dirname(__file__),
            fixture_file,
        )

        print(f"Using fixture {fp} for request to {url.host}")

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
    data: dict[str, Any] = None, options: dict[str, Any] = None
) -> MockConfigEntry:
    try:
        # Core 2024.1 added minor_version
        return MockConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="",
            data={CONF_TOKEN: TOKEN, **(data or {})},
            source="user",
            options={**(options or {})},
            unique_id="12345",
        )
    except TypeError:
        return MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="",
            data={CONF_TOKEN: TOKEN, **(data or {})},
            source="user",
            options={**(options or {})},
            unique_id="12345",
        )


async def setup_integration(hass: ha.HomeAssistant, config_entry: MockConfigEntry) -> None:
    mock_session = await client_session_proxy(hass)
    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession", return_value=mock_session
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
