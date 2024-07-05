"""Test the data_client module."""

import asyncio
from contextlib import nullcontext as does_not_raise
from typing import ContextManager

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.exceptions import HacsException, HacsNotModifiedException

from tests.common import (
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    category_test_data_parametrized,
    create_config_entry,
    get_hacs,
    recursive_remove_key,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_basic_functionality_data(
    hacs: HacsBase,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    """Test the base result."""
    result = await hacs.data_client.get_data(category_test_data["category"], validate=True)

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(result, ("last_fetched",))),
        f"data_client/base/data/{category_test_data['category']}.json",
    )


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_basic_functionality_repositories(
    hacs: HacsBase,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    """Test the base result."""
    result = await hacs.data_client.get_repositories(category_test_data["category"])

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(result, ("last_fetched",))),
        f"data_client/base/repositories/{category_test_data['category']}.json",
    )


@pytest.mark.parametrize(
    "exception,expectation",
    (
        pytest.param(
            Exception("Test"),
            pytest.raises(HacsException, match="Error fetching data from HACS: Test"),
            id="Exception-Error fetching data from HACS: Test",
        ),
        pytest.param(
            asyncio.TimeoutError,
            pytest.raises(HacsException, match="Timeout of 60s reached"),
            id="TimeoutError-Timeout of 60s reached",
        ),
    ),
)
async def test_exception_handling(
    hacs: HacsBase,
    response_mocker: ResponseMocker,
    exception: Exception,
    expectation: ContextManager,
):
    """Test the base result."""
    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/repositories.json",
        response=MockedResponse(exception=exception),
    )

    with expectation:
        await hacs.data_client.get_repositories("integration")


@pytest.mark.parametrize(
    "status,expectation",
    (
        pytest.param(1009, pytest.raises(HacsException), id="1009-HacsException"),
        pytest.param(200, does_not_raise(), id="200-does_not_raise"),
        pytest.param(201, does_not_raise(), id="201-does_not_raise"),
        pytest.param(301, pytest.raises(HacsException), id="301-HacsException"),
        pytest.param(302, pytest.raises(HacsException), id="302-HacsException"),
        pytest.param(
            304,
            pytest.raises(HacsNotModifiedException),
            id="304-HacsNotModifiedException",
        ),
        pytest.param(400, pytest.raises(HacsException), id="400-HacsException"),
        pytest.param(401, pytest.raises(HacsException), id="401-HacsException"),
        pytest.param(403, pytest.raises(HacsException), id="403-HacsException"),
        pytest.param(418, pytest.raises(HacsException), id="418-HacsException"),
        pytest.param(429, pytest.raises(HacsException), id="429-HacsException"),
        pytest.param(500, pytest.raises(HacsException), id="500-HacsException"),
        pytest.param(529, pytest.raises(HacsException), id="529-HacsException"),
    ),
)
async def test_status_handling(
    hacs: HacsBase,
    response_mocker: ResponseMocker,
    status: int,
    expectation: ContextManager,
):
    """Test the base result."""
    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/repositories.json",
        response=MockedResponse(status=status),
    )

    with expectation:
        await hacs.data_client.get_repositories("integration")


GOOD_COMMON_DATA = {
    "description": "abc",
    "etag_repository": "blah",
    "full_name": "blah",
    "last_commit": "abc",
    "last_fetched": 0,
    "last_updated": "blah",
    "manifest": {},
}

GOOD_INTEGRATION_DATA = {
    "description": "abc",
    "domain": "abc",
    "etag_repository": "blah",
    "full_name": "blah",
    "last_commit": "abc",
    "last_fetched": 0,
    "last_updated": "blah",
    "manifest": {},
    "manifest_name": "abc",
}


def without(d: dict, key: str) -> dict:
    """Return a copy of d without key."""
    d = dict(d)
    d.pop(key)
    return d


@pytest.mark.parametrize(
    ("category", "data"),
    [
        ("appdaemon", {"12345": without(GOOD_COMMON_DATA, "description")}),
        ("integration", {"12345": without(GOOD_INTEGRATION_DATA, "description")}),
        ("plugin", {"12345": without(GOOD_COMMON_DATA, "description")}),
        ("python_script", {"12345": without(GOOD_COMMON_DATA, "description")}),
        ("template", {"12345": without(GOOD_COMMON_DATA, "description")}),
        ("theme", {"12345": without(GOOD_COMMON_DATA, "description")}),
        ("critical", [{"repository": "test", "reason": "blah"}]),
        ("removed", [{"repository": "test"}]),
    ],
)
async def test_basic_functionality_data_validate(
    hacs: HacsBase,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category: str,
    data: dict | list,
):
    """Test invalid repo data is discarded when validation is enabled."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category}/data.json",
        MockedResponse(content=data),
    )
    validated = await hacs.data_client.get_data(category, validate=True)

    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category}/data.json",
        MockedResponse(content=data),
    )
    unvalidated = await hacs.data_client.get_data(category, validate=False)

    snapshots.assert_match(
        safe_json_dumps({"validated": validated, "unvalidated": unvalidated}),
        f"data_client/base/data_validate/{category}.json",
    )


@pytest.mark.parametrize(
    ("category", "data"),
    [
        ("appdaemon", without(GOOD_COMMON_DATA, "description")),
        ("integration", without(GOOD_INTEGRATION_DATA, "description")),
        ("plugin", without(GOOD_COMMON_DATA, "description")),
        ("python_script", without(GOOD_COMMON_DATA, "description")),
        ("template", without(GOOD_COMMON_DATA, "description")),
        ("theme", without(GOOD_COMMON_DATA, "description")),
    ],
)
async def test_discard_invalid_repo_data(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category: str,
    data: dict,
):
    """Test validation is enabled when updating category repositories."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category}/data.json",
        MockedResponse(content={"12345": data}),
    )

    config_entry = create_config_entry()
    hass.data.pop("custom_components", None)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hacs: HacsBase = get_hacs(hass)

    assert hacs.repositories
    assert not hacs.system.disabled
    assert hacs.stage == "running"

    repository = f"hacs-test-org/{category}-basic"
    await snapshots.assert_hacs_data(
        hacs,
        f"{repository}/test_discard_invalid_repo_data.json",
    )
