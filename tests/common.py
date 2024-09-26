# pylint: disable=missing-docstring,invalid-name
from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from inspect import currentframe
import json as json_func
import os
from types import NoneType
from typing import Any, TypedDict
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError, ClientSession, ClientWebSocketResponse
from aiohttp.typedefs import StrOrURL
from awesomeversion import AwesomeVersion
from homeassistant import config_entries, core as ha
from homeassistant.auth import models as auth_models
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, __version__ as HA_VERSION
from homeassistant.helpers import storage
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.json import ExtendedJSONEncoder
import homeassistant.util.uuid as uuid_util
import pytest
from yarl import URL

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.repositories.base import HacsManifest, HacsRepository
from custom_components.hacs.utils.logger import LOGGER

TOKEN = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
REQUEST_CONTEXT: ContextVar[pytest.FixtureRequest] = ContextVar(
    "request_context", default=None)

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
    categories: Iterable[HacsCategory] = [entry["category"]
                                          for entry in _CATEGORY_TEST_DATA],
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
            key=lambda obj: (getattr(obj, "id", None)
                             or getattr(obj, "name", None) or 0)
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
            returndata[key] = [recursive_remove_key(
                item, to_remove) for item in _sort_list(value)]
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
        data[store.key] = json_func.loads(
            json_func.dumps(data_to_write, cls=store._encoder))

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

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, _async_close_websession)

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
        self.exception = kwargs.get("exception")
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
    config_entry_data = {
        "version": 1,
        "minor_version": 0,
        "domain": DOMAIN,
        "title": "",
        "data": {"token": TOKEN, **(data or {})},
        "source": "user",
        "options": {**(options or {})},
        "unique_id": "12345",
    }
    # legacy workaround for tests
    if AwesomeVersion(HA_VERSION).dev:
        config_entry_data["discovery_keys"] = {}
    return MockConfigEntry(**config_entry_data)


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
