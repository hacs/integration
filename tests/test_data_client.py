"""Test the diagnostics module."""

import asyncio
from types import NoneType
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
    "exception,result",
    (
        (Exception("Test"), "Error fetching data from HACS: Test"),
        (asyncio.TimeoutError, "Timeout of 60s reached"),
    ),
)
async def test_exception_handling(
    hacs: HacsBase,
    response_mocker: ResponseMocker,
    exception: Exception,
    result: str,
):
    """Test the base result."""
    _result: str | None = None

    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/repositories.json",
        response=MockedResponse(exception=exception),
    )

    try:
        await hacs.data_client.get_repositories("integration")
    except Exception as exception:
        _result = str(exception)

    assert result == _result


@pytest.mark.parametrize(
    "status,result",
    (
        (1009, HacsException),
        (200, NoneType),
        (201, NoneType),
        (301, HacsException),
        (302, HacsException),
        (304, HacsNotModifiedException),
        (400, HacsException),
        (401, HacsException),
        (403, HacsException),
        (418, HacsException),
        (429, HacsException),
        (500, HacsException),
        (529, HacsException),
    ),
)
async def test_status_handling(
    hacs: HacsBase,
    response_mocker: ResponseMocker,
    status: int,
    result: str,
):
    """Test the base result."""
    _result: str | None = None

    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/repositories.json",
        response=MockedResponse(status=status),
    )

    try:
        await hacs.data_client.get_repositories("integration")
    except Exception as exception:
        _result = exception

    assert (result) == type(_result)
