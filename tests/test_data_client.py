"""Test the data_client module."""

import asyncio
from contextlib import nullcontext as does_not_raise
from types import NoneType
from typing import ContextManager

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.exceptions import HacsException, HacsNotModifiedException

from tests.common import (
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    category_test_data_parametrized,
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
    result = await hacs.data_client.get_data(category_test_data["category"])

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
    expectation: str,
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
